"""
Q-Sentinel Mesh — TLS Certificate Generator

Generates a self-signed CA + server certificate for securing the
Flower gRPC channel between hospital nodes and the central server.

Requirements:
    pip install cryptography  (already in requirements.txt)

Usage:
    python scripts/gen_tls_certs.py

    # Custom server IP / hostname
    python scripts/gen_tls_certs.py --ip 192.168.1.100 --hostname my-server

Output (written to config/certs/):
    ca.crt         — CA certificate (distribute to all client machines)
    server.crt     — Server certificate
    server.key     — Server private key  *** KEEP PRIVATE ***

After generating:
    Server machine: python scripts/fed_server.py --tls
    Client machine: python scripts/fed_client.py --server <IP>:8443 --tls
                    (copy ca.crt to client's config/certs/ directory)
"""

from __future__ import annotations

import argparse
import datetime
import ipaddress
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
CERTS_DIR = ROOT / "config" / "certs"

# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate self-signed TLS certificates for Q-Sentinel gRPC"
    )
    parser.add_argument(
        "--ip",
        type=str,
        default="127.0.0.1",
        help="Server IP address to include as Subject Alternative Name (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--hostname",
        type=str,
        default="q-sentinel-server",
        help="Server hostname (default: q-sentinel-server)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Certificate validity in days (default: 365)",
    )
    parser.add_argument(
        "--key-size",
        type=int,
        default=4096,
        help="RSA key size in bits (default: 4096)",
    )
    return parser.parse_args()


def generate_certificates(server_ip: str, hostname: str, days: int, key_size: int):
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    CERTS_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.utcnow()
    expiry = now + datetime.timedelta(days=days)

    # ── 1. Generate CA key + self-signed certificate ──────────────────────────
    print("[1/4] Generating CA private key ...")
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)

    ca_name = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Q-Sentinel Mesh CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Q-Sentinel Root CA"),
    ])

    print("[2/4] Self-signing CA certificate ...")
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(expiry)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    # ── 2. Generate server key + CSR ──────────────────────────────────────────
    print("[3/4] Generating server private key and certificate ...")
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)

    server_name = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Q-Sentinel Mesh"),
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])

    # Subject Alternative Names — add both IP and hostname so clients can verify
    san_entries = [x509.DNSName(hostname), x509.DNSName("localhost")]
    try:
        san_entries.append(x509.IPAddress(ipaddress.ip_address(server_ip)))
    except ValueError:
        print(f"  WARNING: '{server_ip}' is not a valid IP — skipping IP SAN")

    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(expiry)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(san_entries),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_encipherment=True,
                content_commitment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    # ── 3. Write files ────────────────────────────────────────────────────────
    print("[4/4] Writing certificate files ...")

    ca_cert_path = CERTS_DIR / "ca.crt"
    server_cert_path = CERTS_DIR / "server.crt"
    server_key_path  = CERTS_DIR / "server.key"

    ca_cert_path.write_bytes(
        ca_cert.public_bytes(serialization.Encoding.PEM)
    )
    server_cert_path.write_bytes(
        server_cert.public_bytes(serialization.Encoding.PEM)
    )
    server_key_path.write_bytes(
        server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    print()
    print("=" * 60)
    print("  TLS Certificates Generated")
    print("=" * 60)
    print(f"  CA cert    : {ca_cert_path}")
    print(f"  Server cert: {server_cert_path}")
    print(f"  Server key : {server_key_path}  *** KEEP PRIVATE ***")
    print(f"  Valid for  : {days} days")
    print(f"  Server IP  : {server_ip}")
    print(f"  Hostname   : {hostname}")
    print()
    print("  Next steps:")
    print("  1. Run server:  python scripts/fed_server.py --tls")
    print("  2. Copy ca.crt  to each client machine's config/certs/")
    print("  3. Run client:  python scripts/fed_client.py --server <IP>:8443 --tls")
    print("=" * 60)


def main():
    args = parse_args()
    try:
        generate_certificates(
            server_ip=args.ip,
            hostname=args.hostname,
            days=args.days,
            key_size=args.key_size,
        )
    except ImportError:
        print("ERROR: cryptography package not found.")
        print("       Run: pip install cryptography")
        sys.exit(1)


if __name__ == "__main__":
    main()
