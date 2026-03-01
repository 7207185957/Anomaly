from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Enterprise AIOps API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    pg_host: str = "127.0.0.1"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: str = ""
    pg_db: str = "postgres"

    loki_url: str = "http://localhost:3100/loki/api/v1/query_range"

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    mlflow_tracking_uri: str = ""
    mlflow_experiment: str = "wcs-dataops-mlflow/dataops/infra-anomalies"
    mlflow_tracking_username: str = ""
    mlflow_tracking_password: str = ""

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 480

    ldap_server: str = "ldap://dwad.prod.aws.amazon.net"
    ldap_port: int = 389
    ldap_use_ssl: bool = False
    ldap_use_tls: bool = False
    ldap_base_dn: str = "OU=aws,OU=dwad,DC=dwad,DC=prod,DC=aws,DC=amazon,DC=net"
    ldap_bind_dn: str = "CN=svc_jupiter,OU=Service Accounts,OU=aws,OU=dwad,DC=dwad,DC=prod,DC=aws,DC=amazon,DC=net"
    ldap_bind_password: str = ""
    ldap_auth_uid: str = "sAMAccountName"
    ldap_group_attribute: str = "memberOf"
    ldap_admin_group_keyword: str = "Admins"

    redis_url: str = "redis://localhost:6379/0"
    rca_queue_name: str = "rca-jobs"

    nebula_host: str = "127.0.0.1"
    nebula_port: int = 9669
    nebula_user: str = "root"
    nebula_password: str = "nebula"
    nebula_space: str = "inventory_tracking"
    nebula_edge_limit: int = 5000

    frontend_base_url: str = "http://localhost:3000"

    demo_mode: bool = False
    demo_username: str = "demo"
    demo_password: str = "demo123"
    demo_display_name: str = "AIOps Demo User"
    demo_groups: list[str] = Field(default_factory=lambda: ["AIOps-Demo", "Admins"])

    @field_validator("ldap_use_ssl", "ldap_use_tls", "demo_mode", mode="before")
    @classmethod
    def parse_bool_env(cls, value):
        if isinstance(value, str):
            text = value.strip()
            if len(text) >= 2 and ((text[0] == '"' and text[-1] == '"') or (text[0] == "'" and text[-1] == "'")):
                text = text[1:-1].strip()
            lowered = text.lower()
            bool_map = {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
                "yes": True,
                "no": False,
                "on": True,
                "off": False,
            }
            if lowered in bool_map:
                return bool_map[lowered]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

