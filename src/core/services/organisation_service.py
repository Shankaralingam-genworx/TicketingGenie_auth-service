"""Business logic for organisation management.

System admin:
  - create_organisation()  → creates org + org_admin user + sends welcome email
  - list_organisations()
  - get_organisation()
  - update_organisation()

org_admin:
  - get_my_organisation()
  - list_org_customers()
  - add_customer()         → creates customer user + profile; tier inherited from org
  - deactivate_customer()  → deactivates user + revokes all active refresh tokens
"""

import logging
import secrets
import string

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.auth_constants import RoleName
from src.core.security import hash_password
from src.core.services.email_service import EmailService
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

logger = logging.getLogger("organisation.service")

ORG_ADMIN_ROLE = "org_admin"


def _generate_temp_password(length: int = 12) -> str:
    """Generate a secure random temporary password meeting complexity rules."""
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
        self.org_repo     = OrganisationRepository(db)
        self.user_repo    = UserRepository(db)
        self.role_repo    = RoleRepository(db)
        self.cust_repo    = CustomerRepository(db)
        self.token_repo   = RefreshTokenRepository(db)
        self.email_svc    = EmailService()
        self.db           = db

    # ── System admin: Organisation CRUD ───────────────────────────────────────

    async def list_organisations(self) -> list[OrganisationResponse]:
        return [_map_org(o) for o in await self.org_repo.get_all()]

    async def get_organisation(self, org_id: int) -> OrganisationResponse:
        return _map_org(await self._get_or_404(org_id))

    async def create_organisation(
        self, data: OrganisationCreate
    ) -> OrganisationCreatedResponse:
        """
        Creates an Organisation and an org_admin user atomically.
        Generates a temporary password and emails it to the new admin.
        """
        if await self.org_repo.get_by_name(data.name):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Organisation '{data.name}' already exists.",
            )

        if data.domain and await self.org_repo.get_by_domain(data.domain):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Domain '{data.domain}' is already used by another organisation.",
            )

        self._validate_email_domain(str(data.admin_email), data.domain)

        org_admin_role = await self.role_repo.get_by_name(ORG_ADMIN_ROLE)
        if not org_admin_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Role 'org_admin' not found. "
                    "Restart the application once to auto-seed it."
                ),
            )

        # Normalise email to lowercase for consistent lookup and storage
        admin_email = str(data.admin_email).lower().strip()

        if await self.user_repo.get_by_email(admin_email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{admin_email}' is already registered.",
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

        await self.email_svc.send_org_admin_welcome(
            to_email=admin_email,
            name=data.admin_name,
            org_name=data.name,
            temp_password=temp_password,
        )

        logger.info(
            "Organisation created: '%s' (id=%s) | org_admin: %s",
            org.name, org.id, admin_user.email,
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
        org = await self._get_or_404(org_id)

        if payload.name and payload.name != org.name:
            if await self.org_repo.get_by_name(payload.name):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Organisation '{payload.name}' already exists.",
                )

        if payload.domain and payload.domain != org.domain:
            if await self.org_repo.get_by_domain(payload.domain):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Domain '{payload.domain}' is already used by another organisation.",
                )

        updated = await self.org_repo.update(
            org,
            name=payload.name,
            customer_tier_id=payload.customer_tier_id,
            domain=payload.domain,
            is_active=payload.is_active,
        )
        return _map_org(updated)

    # ── org_admin: manage own organisation ────────────────────────────────────

    async def get_my_organisation(self, org_id: int) -> OrganisationResponse:
        return _map_org(await self._get_or_404(org_id))

    async def list_org_customers(self, org_id: int) -> list[OrgCustomerResponse]:
        await self._get_or_404(org_id)
        users = await self.org_repo.get_customers(org_id)
        return [_map_customer_user(u) for u in users]

    async def add_customer(
        self, org_id: int, payload: OrgCustomerCreate
    ) -> OrgCustomerResponse:
        """
        Creates a customer user + customer profile under this organisation.
        Tier is always inherited from the org — not overridable per customer.
        """
        org = await self._get_or_404(org_id)

        if not org.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organisation is inactive.",
            )

        # Normalise email before domain check and storage
        customer_email = str(payload.email).lower().strip()
        self._validate_email_domain(customer_email, org.domain)

        customer_role = await self.role_repo.get_by_name(RoleName.CUSTOMER.value)
        if not customer_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Role 'customer' not seeded.",
            )

        if await self.user_repo.get_by_email(customer_email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{customer_email}' is already registered.",
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

        await self.email_svc.send_customer_welcome(
            to_email=customer_email,
            name=payload.name,
            org_name=org.name,
            temp_password=temp_password,
        )

        logger.info(
            "Customer created: %s in org '%s' (id=%s) tier_id=%s",
            user.email, org.name, org.id, org.customer_tier_id,
        )

        fresh_user = await self.user_repo.get_by_id(user.id)
        return _map_customer_user(fresh_user)

    async def deactivate_customer(
        self, org_id: int, customer_user_id: int
    ) -> OrgCustomerResponse:
        """org_admin deactivates a customer that belongs to their org."""
        user = await self.user_repo.get_by_id(customer_user_id)
        if not user or user.org_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found in your organisation.",
            )
        if user.role.name != RoleName.CUSTOMER.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a customer.",
            )

        user.is_active = False
        await self.db.flush()

        # Revoke all active refresh tokens so the deactivation takes effect
        # immediately — not just on the next token expiry.
        await self.token_repo.revoke_all_for_user(customer_user_id)

        return _map_customer_user(user)

    # ── Private ────────────────────────────────────────────────────────────────

    async def _get_or_404(self, org_id: int):
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organisation not found.",
            )
        return org

    def _validate_email_domain(self, email: str, domain: str | None) -> None:
        """
        Ensures the email domain matches the organisation domain.
        Skipped silently if no domain restriction is set on the organisation.
        """
        if not domain:
            return
        email_domain = email.split("@")[-1].lower()
        if email_domain != domain.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email domain must match organisation domain '{domain}'.",
            )