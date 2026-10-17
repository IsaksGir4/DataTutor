from pathlib import Path
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# TutorDatos/.env
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # Base de Datos
    DATABASE_URL: str

    # IA y Modelos (Ollama)
    OLLAMA_URL: str
    OLLAMA_KEEP_ALIVE: str = "5m"
    CHAT_MODEL: str = "qwen2.5:3b"
    EMBED_MODEL: str
    EMBED_DIM: int = Field(gt=0)
    NUM_CTX: int = Field(default=4096, gt=0)
    TEMPERATURE: float = Field(default=0.0, ge=0.0)
    NUM_PREDICT: int = Field(default=512, gt=0)

    # Ingesta y RAG (valores vigentes conservados)
    CHUNK_SIZE: int = Field(gt=0)
    CHUNK_OVERLAP: int = Field(ge=0)
    TOP_K: int = Field(default=4, gt=0)
    SIM_THRESHOLD: float = Field(default=0.65, ge=0.0, le=1.0)
    SIM_LOW: float = Field(default=0.50, ge=0.0, le=1.0)
    MAX_UPLOAD_MB: int = Field(default=30, gt=0)

    # Autenticación (Keycloak) y CORS
    KEYCLOAK_URL: str
    KEYCLOAK_REALM: str
    KEYCLOAK_CLIENT_ID: str
    KEYCLOAK_AUDIENCE: str
    KEYCLOAK_JWKS_URL: Optional[str] = None
    CORS_ORIGINS: str

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def keycloak_issuer(self) -> str:
        base_url = self.KEYCLOAK_URL.rstrip("/").replace(
            "://127.0.0.1", "://localhost"
        )
        return f"{base_url}/realms/{self.KEYCLOAK_REALM}"

    @property
    def keycloak_jwks_url(self) -> str:
        if self.KEYCLOAK_JWKS_URL:
            return self.KEYCLOAK_JWKS_URL
        internal_base = self.KEYCLOAK_URL.rstrip("/").replace(
            "://localhost", "://127.0.0.1"
        )
        return (
            f"{internal_base}/realms/{self.KEYCLOAK_REALM}"
            "/protocol/openid-connect/certs"
        )

    @model_validator(mode="after")
    def validate_chunk_settings(self):
        if self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError(
                "CHUNK_OVERLAP debe ser menor que CHUNK_SIZE"
            )
        return self


settings = Settings()