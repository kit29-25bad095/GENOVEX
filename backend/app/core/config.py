import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "GENOVEX Healthcare Platform"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./genovex.db")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "genovex-secure-secret-key-uae-2026")
    ALLOW_SIMULATED_AUTH: bool = os.getenv("ALLOW_SIMULATED_AUTH", "True").lower() == "true" # Dev sandbox only, disabled in production
    
    # Target Market & Language
    DEFAULT_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: list[str] = ["en", "ar"]
    
    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()
