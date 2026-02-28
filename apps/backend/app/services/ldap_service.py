from __future__ import annotations

from dataclasses import dataclass

from ldap3 import ALL, Connection, Server, Tls

from app.core.config import get_settings


@dataclass
class LdapUser:
    username: str
    display_name: str
    groups: list[str]


class LdapAuthService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _server(self) -> Server:
        tls = Tls(validate=0) if self.settings.ldap_use_tls else None
        return Server(
            host=self.settings.ldap_server,
            port=self.settings.ldap_port,
            use_ssl=self.settings.ldap_use_ssl,
            tls=tls,
            get_info=ALL,
        )

    def _user_dn(self, conn: Connection, username: str) -> str | None:
        filt = f"({self.settings.ldap_auth_uid}={username})"
        conn.search(
            search_base=self.settings.ldap_base_dn,
            search_filter=filt,
            attributes=["distinguishedName", "displayName", self.settings.ldap_group_attribute],
            size_limit=1,
        )
        if not conn.entries:
            return None
        entry = conn.entries[0]
        return str(entry.entry_dn)

    def authenticate(self, username: str, password: str) -> LdapUser:
        server = self._server()
        with Connection(
            server,
            user=self.settings.ldap_bind_dn,
            password=self.settings.ldap_bind_password,
            auto_bind=True,
        ) as svc_conn:
            user_dn = self._user_dn(svc_conn, username)
            if not user_dn:
                raise ValueError("User not found in LDAP")

            with Connection(server, user=user_dn, password=password, auto_bind=True):
                pass

            svc_conn.search(
                search_base=self.settings.ldap_base_dn,
                search_filter=f"({self.settings.ldap_auth_uid}={username})",
                attributes=["displayName", self.settings.ldap_group_attribute],
                size_limit=1,
            )
            if not svc_conn.entries:
                raise ValueError("Unable to load LDAP profile")

            entry = svc_conn.entries[0]
            display_name = (
                str(entry.displayName.value)
                if hasattr(entry, "displayName") and entry.displayName.value
                else username
            )

            groups: list[str] = []
            attr = self.settings.ldap_group_attribute
            if hasattr(entry, attr):
                raw_vals = getattr(entry, attr).values or []
                groups = [str(v) for v in raw_vals]

            return LdapUser(username=username, display_name=display_name, groups=groups)

