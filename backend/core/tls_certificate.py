"""Generate a self-signed certificate and its private key."""
import datetime
import ipaddress
import logging
import socket
from pathlib import Path

log = logging.getLogger(__name__)
CERT_VALIDITY_DAYS = 3650


def _lan_ip() -> str | None:
    """Best-effort local LAN IP (no packets are actually sent)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 80))  # TEST-NET-1 — never routed
            return s.getsockname()[0]
    except OSError:
        return None


def generate_self_signed_cert(cert_path: Path, key_path: Path) -> None:
    """
    Generate an RSA-2048 self-signed certificate + private key at the given
    paths, overwriting whatever is there. SANs: localhost, 127.0.0.1, the
    machine hostname, and the current LAN IP (if detectable).
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    hostname = socket.gethostname()
    san: list[x509.GeneralName] = [
        x509.DNSName("localhost"),
        x509.DNSName(hostname),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]
    lan = _lan_ip()
    if lan:
        try:
            san.append(x509.IPAddress(ipaddress.ip_address(lan)))
        except ValueError:
            pass

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    now  = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)  # self-signed: issuer == subject
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))  # clock-skew slack
        .not_valid_after(now + datetime.timedelta(days=CERT_VALIDITY_DAYS))
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    try:
        key_path.chmod(0o600)  # meaningful on POSIX; no-op semantics on Windows
    except OSError:
        pass
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    log.info(
        "generated self-signed TLS certificate at %s (SANs: %s)",
        cert_path, ", ".join(str(s.value) for s in san),
    )
