"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All configuration values for the auth service."""

    # Database
    DATABASE_URL: str 

    # JWT
    JWT_SECRET_KEY: str 
    JWT_ALGORITHM: str 
    ACCESS_TOKEN_EXPIRE_MINUTES: int 
    REFRESH_TOKEN_EXPIRE_DAYS: int 

    # App
    APP_ENV: str
    APP_PORT: int 
    
    
    EMAIL_FROM : str
    SMTP_HOST : str
    SMTP_PORT :int
    SMTP_USER : str
    SMTP_PASSWORD :str

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
