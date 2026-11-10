"""Reuse a valid TLS certificate or generate a replacement when needed."""
import datetime
import logging
from pathlib import Path
from backend.core.tls_certificate import generate_self_signed_cert

log = logging.getLogger(__name__)


def _cert_expired(cert_path: Path) -> bool:
    """True if the existing certificate is past its notAfter date."""
    from cryptography import x509
    try:
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        return cert.not_valid_after_utc <= datetime.datetime.now(datetime.timezone.utc)
    except Exception as exc:
        log.warning("could not parse %s (%s) — will regenerate", cert_path, exc)
        return True


def ensure_self_signed_cert(cert_path: Path, key_path: Path) -> None:
    """
    Make sure a usable cert/key pair exists at the given paths.

    • Both files present and cert not expired → leave them untouched
      (this is how an institution-provided cert is respected).
    • Anything missing, unparsable, or expired → (re)generate both.

    Raises on generation failure — main.py treats that as fatal rather than
    silently falling back to plaintext HTTP.
    """
    if cert_path.exists() and key_path.exists() and not _cert_expired(cert_path):
        return
    generate_self_signed_cert(cert_path, key_path)
