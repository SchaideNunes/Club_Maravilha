"""
Configurações centralizadas da aplicação utilizando Pydantic v2 Settings.
Lê variáveis de ambiente ou arquivos .env de forma segura e tipada.
"""
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Metadados da Aplicação
    PROJECT_NAME: str = "Club Maravilha - Sistema de Gestão"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT_BACKEND: int = 8000
    
    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Banco de Dados
    POSTGRES_SERVER: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "club_maravilha"
    POSTGRES_USER: str = "club_admin"
    POSTGRES_PASSWORD: str = "club_secret_password_change_in_prod"
    
    DATABASE_URL: str = (
        "postgresql+asyncpg://club_admin:club_secret_password_change_in_prod@db:5432/club_maravilha"
    )
    DATABASE_SYNC_URL: str = (
        "postgresql://club_admin:club_secret_password_change_in_prod@db:5432/club_maravilha"
    )

    # Segurança & JWT
    SECRET_KEY: str = "insecure_dev_secret_key_change_in_production_12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Gateway Pix & Webhooks
    PIX_GATEWAY_PROVIDER: str = "EFI_GERENCIANET"
    PIX_CLIENT_ID: str = "mock_client_id"
    PIX_CLIENT_SECRET: str = "mock_client_secret"
    PIX_CERTIFICATE_PATH: str = "/app/certs/pix_certificate.pem"
    PIX_WEBHOOK_SECRET: str = "mock_webhook_secret_dev"

    # WhatsApp (Régua de Cobrança)
    WHATSAPP_PROVIDER: str = "EVOLUTION_API"
    WHATSAPP_API_URL: str = "http://localhost:8080"
    WHATSAPP_API_KEY: str = "mock_whatsapp_key"
    WHATSAPP_INSTANCE_NAME: str = "club_maravilha_instance"

    # Catraca Facial
    TURNSTILE_HOST: str = "127.0.0.1"
    TURNSTILE_PORT: int = 8080
    TURNSTILE_API_TOKEN: str = "mock_turnstile_token"
    TURNSTILE_TIMEOUT_SECONDS: int = 5

    # Regras de Negócio do Clube
    VALOR_MENSALIDADE_PADRAO: float = 150.00
    DIA_VENCIMENTO_PADRAO: int = 10
    FRANQUIA_CONVITES_MENSAL: int = 8
    VALOR_CONVITE_EXCEDENTE: float = 35.00
    LIMITE_RESERVAS_SIMULTANEAS_PADRAO: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
