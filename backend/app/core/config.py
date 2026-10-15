"""Настройки приложения (pydantic-settings, .env): БД, JWT, LLM, песочница."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Все настройки приложения; переопределяются переменными окружения."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ITInterview"
    database_url: str = "sqlite:///./itrainterview.sqlite3"
    secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 30
    refresh_token_ttl_days: int = 7

    llm_base_url: str = "http://192.168.2.83:8080/v1"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_timeout_sec: float = 120.0

    sandbox_local_dir: str = "/tmp/sandbox-work"
    sandbox_host_dir: str = "/tmp/sandbox-work"
    sandbox_timeout_sec: int = 5
    sandbox_memory_mb: int = 256
    sandbox_cpus: float = 1.0

    admin_email: str = ""
    admin_password: str = ""
    admin_username: str = "admin"
    seed_on_start: bool = True
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        """cors_origins как список origin (разделитель — запятая)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Кэшированный (lru_cache) экземпляр настроек."""
    return Settings()


settings = get_settings()
