from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = "development"
    database_url: str = "sqlite:///./change_radar.db"
    db_host: str | None = Field(default=None, validation_alias=AliasChoices("DB_HOST", "MYSQL_HOST"))
    db_port: int = Field(default=3306, validation_alias=AliasChoices("DB_PORT", "MYSQL_PORT"))
    db_user: str | None = Field(default=None, validation_alias=AliasChoices("DB_USER", "MYSQL_USER"))
    db_password: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DB_PASSWORD", "MYSQL_PASSWORD"),
    )
    db_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DB_NAME", "MYSQL_DATABASE", "MYSQL_DBNAME"),
    )
    cache_backend: Literal["null", "memory", "redis"] = "memory"
    redis_url: str = "redis://localhost:6379/0"
    auto_create_tables: bool = False
    seed_demo_data: bool = True
    internal_user_key: str = "internal-demo"
    wechat_appid: str | None = None
    require_wechat_identity: bool = False
    market_data_provider: Literal["database_demo", "sina", "eastmoney"] = "sina"
    market_sync_interval_seconds: int = 15
    market_candidate_limit_per_board: int = 20
    market_http_timeout_seconds: int = 12
    market_http_use_environment_proxy: bool = False

    @model_validator(mode="after")
    def validate_database_configuration(self) -> "Settings":
        mysql_values = {
            "DB_HOST": self.db_host,
            "DB_USER": self.db_user,
            "DB_PASSWORD": self.db_password,
            "DB_NAME": self.db_name,
        }
        configured_values = [bool(value) for value in mysql_values.values()]
        if any(configured_values) and not all(configured_values):
            missing = ", ".join(key for key, value in mysql_values.items() if not value)
            raise ValueError(f"CloudBase MySQL 配置不完整，缺少：{missing}")

        if self.is_production and self.sqlalchemy_url().get_backend_name() != "mysql":
            raise ValueError(
                "生产环境必须配置 CloudBase MySQL。请设置 DB_HOST、DB_PORT、DB_USER、"
                "DB_PASSWORD、DB_NAME，或提供 mysql+pymysql DATABASE_URL。"
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"prod", "production"}

    def sqlalchemy_url(self) -> URL:
        if self.db_host and self.db_user and self.db_password and self.db_name:
            return URL.create(
                drivername="mysql+pymysql",
                username=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                query={"charset": "utf8mb4"},
            )
        return make_url(self.database_url)

    @property
    def database_backend(self) -> str:
        return self.sqlalchemy_url().get_backend_name()

    def sqlalchemy_url_string(self) -> str:
        return self.sqlalchemy_url().render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
