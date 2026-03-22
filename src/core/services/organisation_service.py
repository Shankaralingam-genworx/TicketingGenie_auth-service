import secrets
import string

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.auth_constants import RoleName
from src.core.exceptions.base_exception import AppException, NotFoundException
from src.core.security import hash_password
from src.core.celery.workers.email_tasks import (
    send_customer_welcome_email,
    send_org_admin_welcome_email,
)
from src.data.repositories.customer_repository import CustomerRepository
from src.data.repositories.organisation_repository import OrganisationRepository
from src.data.repositories.refresh_token_repository import RefreshTokenRepository
from src.data.repositories.role_repository import RoleRepository
from src.data.repositories.user_repository import UserRepository
from src.schemas.customer_tier_schema import CustomerTierResponse
from src.schemas.organisation_schema import (
    OrgCustomerCreate,
    OrgCustomerResponse,
    OrganisationCreate,
    OrganisationCreatedResponse,
    OrganisationResponse,
    OrganisationUpdate,
)
from src.observability.logging.logger import get_logger

logger = get_logger(__name__).bind(service="auth-service")

ORG_ADMIN_ROLE = "org_admin"


def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    pwd = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%"),
    ]
    pwd += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(pwd)
    return "".join(pwd)


def _map_org(org) -> OrganisationResponse:
    return OrganisationResponse(
        id=org.id,
        name=org.name,
        domain=org.domain,
        customer_tier_id=org.customer_tier_id,
        tier=CustomerTierResponse.model_validate(org.tier) if org.tier else None,
        is_active=org.is_active,
        created_at=org.created_at,
    )


def _map_customer_user(user) -> OrgCustomerResponse:
    c = user.customer
    return OrgCustomerResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        org_id=user.org_id,
        created_at=user.created_at,
        phone=c.phone if c else None,
        preferred_contact=(
            c.preferred_contact.value if c and c.preferred_contact else None
        ),
        customer_tier_id=c.customer_tier_id if c else None,
        tier_name=c.tier.name if c and c.tier else None,
    )


class OrganisationService:

    def __init__(self, db: AsyncSession):
        self.org_repo   = OrganisationRepository(db)
        self.user_repo  = UserRepository(db)
        self.role_repo  = RoleRepository(db)
        self.cust_repo  = CustomerRepository(db)
        self.token_repo = RefreshTokenRepository(db)
        self.db         = db

    # ── System admin: Organisation CRUD ───────────────────────────────────────

    async def list_organisations(self) -> list[OrganisationResponse]:
        logger.info("list_organisations_started")
        orgs = await self.org_repo.get_all()
        logger.info("list_organisations_success", count=len(orgs))
        return [_map_org(o) for o in orgs]

    async def get_organisation(self, org_id: int) -> OrganisationResponse:
        logger.info("get_organisation_started")
        org = await self._get_or_404(org_id)
        logger.info("get_organisation_success")
        return _map_org(org)

    async def create_organisation(
        self, data: OrganisationCreate
    ) -> OrganisationCreatedResponse:
        """Create org + org_admin user; email temp credentials via Celery."""
        logger.info("create_organisation_started", org_name=data.name)

        if await self.org_repo.get_by_name(data.name):
            logger.warning("create_organisation_name_conflict", org_name=data.name)
            raise AppException(
                f"Organisation '{data.name}' already exists.", status_code=409
            )

        if data.domain and await self.org_repo.get_by_domain(data.domain):
            logger.warning("create_organisation_domain_conflict", domain=data.domain)
            raise AppException(
                f"Domain '{data.domain}' is already used by another organisation.",
                status_code=409,
            )

        self._validate_email_domain(str(data.admin_email), data.domain)

        org_admin_role = await self.role_repo.get_by_name(ORG_ADMIN_ROLE)
        if not org_admin_role:
            logger.error("create_organisation_role_not_seeded", role=ORG_ADMIN_ROLE)
            raise AppException("Role 'org_admin' not seeded.", status_code=500)

        admin_email = str(data.admin_email).lower().strip()

        if await self.user_repo.get_by_email(admin_email):
            logger.warning("create_organisation_admin_email_exists", email=admin_email)
            raise AppException(
                f"Email '{admin_email}' is already registered.", status_code=409
            )

        org = await self.org_repo.create(
            name=data.name,
            customer_tier_id=data.customer_tier_id,
            domain=data.domain,
        )

        temp_password = _generate_temp_password()
        admin_user = await self.user_repo.create_org_user(
            name=data.admin_name,
            email=admin_email,
            password_hash=hash_password(temp_password),
            role_id=org_admin_role.id,
            org_id=org.id,
        )

        logger.info("sending_org_admin_email", email=admin_email)
        send_org_admin_welcome_email.delay(
            to_email=admin_email,
            name=data.admin_name,
            org_name=data.name,
            temp_password=temp_password,
        )

        logger.info(
            "create_organisation_success",
            org_id=org.id,
            admin_user_id=admin_user.id,
            admin_email=admin_email,
        )

        org = await self.org_repo.get_by_id(org.id)
        return OrganisationCreatedResponse(
            organisation=_map_org(org),
            org_admin_email=admin_email,
            message=(
                f"Organisation '{org.name}' created. "
                f"Temporary credentials sent to {admin_email}."
            ),
        )

    async def update_organisation(
        self, org_id: int, payload: OrganisationUpdate
    ) -> OrganisationResponse:
        logger.info("update_organisation_started", org_id=org_id)

        org = await self._get_or_404(org_id)

        if payload.name and payload.name != org.name:
            if await self.org_repo.get_by_name(payload.name):
                logger.warning(
                    "update_organisation_name_conflict",
                    org_id=org_id,
                    new_name=payload.name,
                )
                raise AppException(
                    f"Organisation '{payload.name}' already exists.", status_code=409
                )

        if payload.domain and payload.domain != org.domain:
            if await self.org_repo.get_by_domain(payload.domain):
                logger.warning(
                    "update_organisation_domain_conflict",
                    org_id=org_id,
                    domain=payload.domain,
                )
                raise AppException(
                    f"Domain '{payload.domain}' is already used by another organisation.",
                    status_code=409,
                )

        updated = await self.org_repo.update(
            org,
            name=payload.name,
            customer_tier_id=payload.customer_tier_id,
            domain=payload.domain,
            is_active=payload.is_active,
        )

        logger.info("update_organisation_success", org_id=org_id)
        return _map_org(updated)

    # ── org_admin: manage own organisation ────────────────────────────────────

    async def get_my_organisation(self, org_id: int) -> OrganisationResponse:
        logger.info("get_my_organisation_started", org_id=org_id)
        org = await self._get_or_404(org_id)
        logger.info("get_my_organisation_success", org_id=org_id)
        return _map_org(org)

    async def list_org_customers(self, org_id: int) -> list[OrgCustomerResponse]:
        logger.info("list_org_customers_started", org_id=org_id)
        await self._get_or_404(org_id)
        users = await self.org_repo.get_customers(org_id)
        logger.info("list_org_customers_success", org_id=org_id, count=len(users))
        return [_map_customer_user(u) for u in users]

    async def add_customer(
        self, org_id: int, payload: OrgCustomerCreate
    ) -> OrgCustomerResponse:
        """Create a customer user + profile under this org; tier inherited from org."""
        logger.info("add_customer_started", org_id=org_id)

        org = await self._get_or_404(org_id)

        if not org.is_active:
            logger.warning("add_customer_org_inactive", org_id=org_id)
            raise AppException("Organisation is inactive.", status_code=403)

        customer_email = str(payload.email).lower().strip()
        self._validate_email_domain(customer_email, org.domain)

        customer_role = await self.role_repo.get_by_name(RoleName.CUSTOMER.value)
        if not customer_role:
            logger.error("add_customer_role_not_seeded", role=RoleName.CUSTOMER.value)
            raise AppException("Role 'customer' not seeded.", status_code=500)

        if await self.user_repo.get_by_email(customer_email):
            logger.warning("add_customer_email_exists", email=customer_email)
            raise AppException(
                f"Email '{customer_email}' is already registered.", status_code=409
            )

        temp_password = _generate_temp_password()
        user = await self.user_repo.create_org_user(
            name=payload.name,
            email=customer_email,
            password_hash=hash_password(temp_password),
            role_id=customer_role.id,
            org_id=org_id,
        )

        await self.cust_repo.create_org_customer(
            user_id=user.id,
            org_id=org_id,
            customer_tier_id=org.customer_tier_id,
            phone=payload.phone,
            preferred_contact=payload.preferred_contact,
        )
        
        logger.info("sending_customer_welcome_email", email=customer_email)
        send_customer_welcome_email.delay(
            to_email=customer_email,
            name=payload.name,
            org_name=org.name,
            temp_password=temp_password,
        )

        logger.info(
            "add_customer_success",
            user_id=user.id,
            org_id=org_id,
            tier_id=org.customer_tier_id,
        )

        fresh_user = await self.user_repo.get_by_id(user.id)
        return _map_customer_user(fresh_user)

    async def deactivate_customer(
        self, org_id: int, customer_user_id: int
    ) -> OrgCustomerResponse:
        """Deactivate a customer and revoke all their active sessions."""
        logger.info(
            "deactivate_customer_started",
            org_id=org_id,
            customer_user_id=customer_user_id,
        )

        user = await self.user_repo.get_by_id(customer_user_id)
        if not user or user.org_id != org_id:
            logger.warning(
                "deactivate_customer_not_found",
                org_id=org_id,
                customer_user_id=customer_user_id,
            )
            raise NotFoundException("Customer", customer_user_id)

        if user.role.name != RoleName.CUSTOMER.value:
            logger.warning(
                "deactivate_customer_wrong_role",
                user_id=customer_user_id,
                role=user.role.name,
            )
            raise AppException("User is not a customer.", status_code=403)

        user.is_active = False
        await self.db.flush()

        # Revoke all refresh tokens so deactivation is immediate
        await self.token_repo.revoke_all_for_user(customer_user_id)

        logger.info(
            "deactivate_customer_success",
            customer_user_id=customer_user_id,
            org_id=org_id,
        )
        return _map_customer_user(user)

    # ── Private ─────────

    async def _get_or_404(self, org_id: int):
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            logger.warning("organisation_not_found", org_id=org_id)
            raise NotFoundException("Organisation", org_id)
        return org

    def _validate_email_domain(self, email: str, domain: str | None) -> None:
        """Reject email if its domain doesn't match the org domain."""
        if not domain:
            return
        email_domain = email.split("@")[-1].lower()
        if email_domain != domain.lower():
            logger.warning(
                "email_domain_mismatch",
                email=email,
                email_domain=email_domain,
                org_domain=domain,
            )
            raise AppException(
                f"Email domain must match organisation domain '{domain}'.",
                status_code=400,
            )