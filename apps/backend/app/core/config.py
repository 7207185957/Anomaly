from functools import lru_cache
import json

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
    pg_connect_timeout_sec: int = 10

    incident_pg_host: str = ""
    incident_pg_port: int = 5432
    incident_pg_user: str = ""
    incident_pg_password: str = ""
    incident_pg_db: str = ""
    incident_team_name: str = "WCS-DataOps-Tier2"

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

    @field_validator(
        "demo_username",
        "demo_password",
        "ldap_bind_password",
        "ldap_server",
        "ldap_base_dn",
        "ldap_bind_dn",
        "incident_pg_host",
        "incident_pg_user",
        "incident_pg_password",
        "incident_pg_db",
        "incident_team_name",
        mode="before",
    )
    @classmethod
    def strip_wrapping_quotes(cls, value):
        if isinstance(value, str):
            text = value.strip()
            if len(text) >= 2 and (
                (text[0] == '"' and text[-1] == '"')
                or (text[0] == "'" and text[-1] == "'")
            ):
                return text[1:-1].strip()
            return text
        return value

    @field_validator("api_prefix", mode="before")
    @classmethod
    def normalize_api_prefix(cls, value):
        if value is None:
            return "/api/v1"
        if isinstance(value, str):
            text = value.strip()
            if len(text) >= 2 and ((text[0] == '"' and text[-1] == '"') or (text[0] == "'" and text[-1] == "'")):
                text = text[1:-1].strip()
            if not text:
                return "/api/v1"
            if not text.startswith("/"):
                text = "/" + text
            return text
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def normalize_cors_origins(cls, value):
        if value is None:
            return ["http://localhost:3000"]
        if isinstance(value, str):
            text = value.strip()
            if len(text) >= 2 and (
                (text[0] == '"' and text[-1] == '"')
                or (text[0] == "'" and text[-1] == "'")
            ):
                text = text[1:-1].strip()
            if not text:
                return []
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except Exception:
                pass
            return [
                part.strip().strip('"').strip("'")
                for part in text.split(",")
                if part.strip()
            ]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

