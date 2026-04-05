"""
Q-Sentinel Mesh — Federated Learning Client (Production gRPC)

Runs a hospital node that trains locally and sends PQC-encrypted
weight updates to the central aggregation server.

Usage:
    # Hospital A — node 0 (run on first machine)
    python scripts/fed_client.py --server 192.168.1.100:8443 --node-id 0

    # Hospital B — node 1 (run on second machine)
    python scripts/fed_client.py --server 192.168.1.100:8443 --node-id 1

    # Hospital C — node 2 (also on second machine, different terminal)
    python scripts/fed_client.py --server 192.168.1.100:8443 --node-id 2

    # Use real DICOM/NIfTI data directory instead of mock data
    python scripts/fed_client.py --server 192.168.1.100:8443 --node-id 0 --data-dir /data/hospital_a

    # With TLS
    python scripts/fed_client.py --server 192.168.1.100:8443 --node-id 0 --tls

Node IDs:
    0 = Hospital A (Bangkok)
    1 = Hospital B (Chiang Mai)
    2 = Hospital C (Khon Kaen)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import torch
from torch.utils.data import DataLoader, random_split

import flwr as fl

from src.federated.hybrid_client import HybridQSentinelClient
from src.data.mock_data import MockCTDataset

HOSPITAL_NAMES = [
    "Hospital A (Bangkok)",
    "Hospital B (Chiang Mai)",
    "Hospital C (Khon Kaen)",
]

# ─────────────────────────────────────────────────────────────────────────────


def load_config() -> dict:
    cfg_path = ROOT / "config" / "fed_config.json"
    with open(cfg_path, encoding="utf-8") as f:
        return json.load(f)


def parse_args(cfg: dict):
    client_cfg = cfg["client"]
    parser = argparse.ArgumentParser(
        description="Q-Sentinel Mesh — Federated Learning Client (Hospital Node)"
    )
    parser.add_argument(
        "--server",
        type=str,
        default=client_cfg["server_address"],
        help=f"Server address host:port (default: {client_cfg['server_address']})",
    )
    parser.add_argument(
        "--node-id",
        type=int,
        default=0,
        choices=[0, 1, 2],
        help="Hospital node ID: 0=Bangkok, 1=ChiangMai, 2=KhonKaen (default: 0)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=client_cfg["local_epochs"],
        help=f"Local training epochs per federated round (default: {client_cfg['local_epochs']})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=client_cfg["batch_size"],
        help=f"Training batch size (default: {client_cfg['batch_size']})",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=client_cfg["mock_samples"],
        help=f"Mock dataset samples (ignored if --data-dir is set, default: {client_cfg['mock_samples']})",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Path to real patient data directory (uses mock data if not set)",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default=client_cfg["pretrained_path"],
        help="Path to pretrained hybrid model weights",
    )
    parser.add_argument(
        "--tls",
        action="store_true",
        default=client_cfg["tls"]["enabled"],
        help="Enable TLS (must match server --tls flag)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Torch device: cuda or cpu (auto-detected by default)",
    )
    return parser.parse_args()


def build_data_loaders(args, node_id: int, batch_size: int):
    """
    Build train/val DataLoaders.

    If --data-dir is provided, attempts to load real DICOM/NIfTI data.
    Falls back to mock synthetic CT data for development / demo.
    """
    if args.data_dir:
        try:
            from src.data.rsna_loader import RSNADataset
            dataset = RSNADataset(
                data_dir=Path(args.data_dir),
                split="train",
            )
            print(f"  [Node {node_id}] Loaded real data: {len(dataset)} samples from {args.data_dir}")
        except Exception as e:
            print(f"  [Node {node_id}] WARNING: Could not load real data ({e})")
            print(f"  [Node {node_id}] Falling back to synthetic mock data")
            dataset = MockCTDataset(n_samples=args.samples, seed=node_id * 100)
    else:
        # Each node gets a different random seed → simulates different hospital distributions
        dataset = MockCTDataset(n_samples=args.samples, seed=node_id * 100)
        print(f"  [Node {node_id}] Using synthetic mock CT data: {len(dataset)} samples")

    # 80/20 train/val split
    n_train = int(0.8 * len(dataset))
    n_val   = len(dataset) - n_train
    train_ds, val_ds = random_split(
        dataset,
        [n_train, n_val],
        generator=torch.Generator().manual_seed(node_id),
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,   # 0 for Windows compatibility
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )
    return train_loader, val_loader


def build_tls_credentials(cfg: dict):
    """Load CA certificate for client-side TLS verification."""
    ca_path = ROOT / cfg["client"]["tls"]["ca_cert_path"]
    if not ca_path.exists():
        print(f"[TLS] ERROR: CA certificate not found: {ca_path}")
        print("      Run: python scripts/gen_tls_certs.py  to generate self-signed certs")
        sys.exit(1)
    return ca_path.read_bytes()


def main():
    cfg  = load_config()
    args = parse_args(cfg)

    hospital_name = HOSPITAL_NAMES[args.node_id]
    pretrained    = ROOT / args.weights if args.weights else None

    print("=" * 60)
    print(f"  Q-Sentinel Mesh — Hospital Node {args.node_id}")
    print(f"  {hospital_name}")
    print("=" * 60)
    print(f"  Server          : {args.server}")
    print(f"  Device          : {args.device}")
    print(f"  Local epochs    : {args.epochs}")
    print(f"  Batch size      : {args.batch_size}")
    print(f"  TLS             : {'enabled' if args.tls else 'disabled'}")
    print(f"  Pretrained      : {pretrained}")
    print("=" * 60)
    print()

    # Build DataLoaders
    train_loader, val_loader = build_data_loaders(args, args.node_id, args.batch_size)
    print(
        f"  [Node {args.node_id}] Train batches: {len(train_loader)} | "
        f"Val batches: {len(val_loader)}"
    )

    # Instantiate the Quantum+PQC Flower client
    client = HybridQSentinelClient(
        partition_id=args.node_id,
        train_loader=train_loader,
        val_loader=val_loader,
        device=args.device,
        local_epochs=args.epochs,
        pretrained_path=pretrained if (pretrained and pretrained.exists()) else None,
    )

    print(f"\n[Node {args.node_id}] Connecting to server at {args.server} ...")
    print(f"[Node {args.node_id}] PQC: ML-KEM-512 + AES-256-GCM — weights encrypted end-to-end")
    print()

    # Build optional TLS root certificate
    root_certificates = build_tls_credentials(cfg) if args.tls else None

    # Start real gRPC connection to server
    fl.client.start_numpy_client(
        server_address=args.server,
        client=client,
        root_certificates=root_certificates,
    )

    print(f"\n[Node {args.node_id}] Federated training complete.")


if __name__ == "__main__":
    main()
