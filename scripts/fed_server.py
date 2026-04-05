"""
Q-Sentinel Mesh — Federated Learning Server (Production gRPC)

Starts a real Flower gRPC server that coordinates ML training across
hospital nodes on separate machines. Uses ML-KEM-512 (Post-Quantum
Cryptography) for key distribution and AES-256-GCM for weight encryption.

Usage:
    # From project root
    python scripts/fed_server.py

    # Custom port / rounds
    python scripts/fed_server.py --port 8443 --rounds 5

    # With TLS (generate certs first with scripts/gen_tls_certs.py)
    python scripts/fed_server.py --tls

Network:
    - Server machine runs this script
    - Hospital nodes run scripts/fed_client.py --server <SERVER_IP>:8443
    - Default port 8443 — open it in your firewall / router
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import flwr as fl

from src.federated.server import QSentinelHybridStrategy
from src.federated.pqc_crypto import ensure_pqc_backend, pqc_backend_is_real, pqc_backend_name

# ─────────────────────────────────────────────────────────────────────────────


def load_config() -> dict:
    cfg_path = ROOT / "config" / "fed_config.json"
    with open(cfg_path, encoding="utf-8") as f:
        return json.load(f)


def parse_args(cfg: dict):
    server_cfg = cfg["server"]
    parser = argparse.ArgumentParser(
        description="Q-Sentinel Mesh — Federated Learning Server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=server_cfg["port"],
        help=f"gRPC listen port (default: {server_cfg['port']})",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=server_cfg["num_rounds"],
        help=f"Number of federated rounds (default: {server_cfg['num_rounds']})",
    )
    parser.add_argument(
        "--min-clients",
        type=int,
        default=server_cfg["min_clients"],
        help=f"Minimum clients before training starts (default: {server_cfg['min_clients']})",
    )
    parser.add_argument(
        "--results",
        type=str,
        default=server_cfg["results_path"],
        help="Path to save per-round results JSON",
    )
    parser.add_argument(
        "--tls",
        action="store_true",
        default=server_cfg["tls"]["enabled"],
        help="Enable mutual TLS (requires certs in config/certs/)",
    )
    return parser.parse_args()


def build_tls_config(cfg: dict):
    """Load TLS certificates from config/certs/."""
    tls_cfg = cfg["server"]["tls"]
    cert_path = ROOT / tls_cfg["cert_path"]
    key_path  = ROOT / tls_cfg["key_path"]
    ca_path   = ROOT / tls_cfg["ca_cert_path"]

    for p in (cert_path, key_path, ca_path):
        if not p.exists():
            print(f"[TLS] ERROR: Missing certificate file: {p}")
            print("      Run: python scripts/gen_tls_certs.py  to generate self-signed certs")
            sys.exit(1)

    return fl.server.ssl_channel_credentials(
        root_certificates=ca_path.read_bytes(),
        private_key=key_path.read_bytes(),
        certificate_chain=cert_path.read_bytes(),
    )


def main():
    cfg  = load_config()
    args = parse_args(cfg)
    ensure_pqc_backend()

    server_address = f"0.0.0.0:{args.port}"
    results_path   = str(ROOT / args.results)

    print("=" * 60)
    print("  Q-Sentinel Mesh — Federated Learning Server")
    print("=" * 60)
    print(f"  Listen address : {server_address}")
    print(f"  Federated rounds: {args.rounds}")
    print(f"  Min clients     : {args.min_clients}")
    print(f"  TLS             : {'enabled' if args.tls else 'disabled'}")
    print(f"  PQC backend     : {pqc_backend_name()} ({'real' if pqc_backend_is_real() else 'demo-only'})")
    print(f"  Results path    : {results_path}")
    print("=" * 60)

    strategy = QSentinelHybridStrategy(
        num_rounds=args.rounds,
        results_path=results_path,
        fraction_fit=cfg["server"]["fraction_fit"],
        fraction_evaluate=cfg["server"]["fraction_evaluate"],
        min_fit_clients=args.min_clients,
        min_evaluate_clients=args.min_clients,
        min_available_clients=args.min_clients,
    )

    server_config = fl.server.ServerConfig(num_rounds=args.rounds, round_timeout=300)

    # Build optional TLS credentials
    ssl_credentials = build_tls_config(cfg) if args.tls else None

    print("\n[Server] Waiting for hospital nodes to connect...")
    print(f"         On each client machine run:")
    print(f"         python scripts/fed_client.py --server <THIS_IP>:{args.port} --node-id 0")
    print()

    fl.server.start_server(
        server_address=server_address,
        config=server_config,
        strategy=strategy,
        certificates=ssl_credentials,
    )

    print("\n[Server] Federated training complete.")
    print(f"[Server] Results saved to: {results_path}")


if __name__ == "__main__":
    main()
