"""Authenticate a Veyon connection using a key or an OS account."""
from typing import Optional
import requests

KEY_AUTH_UUID = "0c69b301-81b4-42d6-8fae-128cdd113314"
LOGON_AUTH_UUID = "63611f7c-be4a-490a-b7e4-2cb0618b2b37"


def authenticate_key(
    session:  requests.Session,
    base_url: str,
    host:     str,
    key_name: str,
    key_data: str,
) -> Optional[str]:
    """
    Key-based authentication.
    key_name — name configured in Veyon (e.g. "class")
    key_data — raw content of the .pem private-key file
    Returns connection-uid on success, None on failure.
    """
    try:
        r = session.post(
            f"{base_url}/authentication/{host}",
            json={
                "method":      KEY_AUTH_UUID,
                "credentials": {"keyname": key_name, "keydata": key_data},
            },
            timeout=5,
        )
        if r.status_code == 200:
            return r.json().get("connection-uid")
    except requests.RequestException:
        pass
    return None


def authenticate_logon(
    session:  requests.Session,
    base_url: str,
    host:     str,
    username: str,
    password: str,
) -> Optional[str]:
    """
    Logon (username/password) authentication.
    username — OS account username on the monitored machine (or domain account)
    password — corresponding password
    Returns connection-uid on success, None on failure.
    """
    try:
        r = session.post(
            f"{base_url}/authentication/{host}",
            json={
                "method":      LOGON_AUTH_UUID,
                "credentials": {"username": username, "password": password},
            },
            timeout=5,
        )
        if r.status_code == 200:
            return r.json().get("connection-uid")
    except requests.RequestException:
        pass
    return None


def authenticate(
    session:  requests.Session,
    base_url: str,
    host:     str,
    cfg:      dict,
) -> Optional[str]:
    """
    Dispatch to the correct auth method based on cfg["auth_method"].
    "key"   → authenticate_key()   (requires key_name, key_data)
    "logon" → authenticate_logon() (requires logon_username, logon_password)
    """
    method = cfg.get("auth_method", "key")
    if method == "logon":
        return authenticate_logon(
            session, base_url, host,
            cfg.get("logon_username", ""),
            cfg.get("logon_password", ""),
        )
    # default: key-based
    return authenticate_key(
        session, base_url, host,
        cfg.get("key_name", ""),
        cfg.get("key_data", ""),
    )
