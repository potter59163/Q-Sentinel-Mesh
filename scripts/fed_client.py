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

import flwr as fl

from src.federated.hybrid_client import HybridQSentinelClient
from src.federated.data_utils import build_client_dataloaders
from src.federated.pqc_crypto import ensure_pqc_backend, pqc_backend_is_real, pqc_backend_name

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
        help="Legacy shortcut for a real patient data directory. Prefer --nii-dir / --dicom-dir or --manifest.",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="JSON manifest describing this node's local dataset.",
    )
    parser.add_argument(
        "--data-source",
        type=str,
        default=client_cfg.get("data_source", "mock"),
        choices=["mock", "ctich", "rsna"],
        help="Dataset mode for this node.",
    )
    parser.add_argument(
        "--nii-dir",
        type=str,
        default=client_cfg.get("nii_dir"),
        help="CT-ICH NIfTI directory for local hospital data.",
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        default=client_cfg.get("csv_path"),
        help="CT-ICH hemorrhage_diagnosis_raw_ct.csv path.",
    )
    parser.add_argument(
        "--dicom-dir",
        type=str,
        default=client_cfg.get("dicom_dir"),
        help="RSNA-style DICOM directory for local hospital data.",
    )
    parser.add_argument(
        "--labels-csv",
        type=str,
        default=client_cfg.get("labels_csv"),
        help="RSNA-style labels CSV used with --dicom-dir.",
    )
    parser.add_argument(
        "--patient-ids",
        type=str,
        default=client_cfg.get("patient_ids"),
        help="Comma-separated CT-ICH patient IDs owned by this node.",
    )
    parser.add_argument(
        "--auto-partition",
        action="store_true",
        default=client_cfg.get("auto_partition", False),
        help="Deterministically partition CT-ICH patients by node id when sharing one dataset copy across machines.",
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
    ensure_pqc_backend()

    hospital_name = HOSPITAL_NAMES[args.node_id]
    pretrained    = ROOT / args.weights if args.weights else None
    img_size = int(cfg["client"].get("img_size", 224))

    data_source = args.data_source
    if args.manifest:
        data_source = data_source
    elif args.nii_dir or args.csv_path:
        data_source = "ctich"
    elif args.dicom_dir or args.labels_csv:
        data_source = "rsna"
    elif args.data_dir and not (args.nii_dir or args.dicom_dir):
        data_source = "rsna"
        args.dicom_dir = args.data_dir

    print("=" * 60)
    print(f"  Q-Sentinel Mesh — Hospital Node {args.node_id}")
    print(f"  {hospital_name}")
    print("=" * 60)
    print(f"  Server          : {args.server}")
    print(f"  Device          : {args.device}")
    print(f"  Local epochs    : {args.epochs}")
    print(f"  Batch size      : {args.batch_size}")
    print(f"  Image size      : {img_size}")
    print(f"  Data source     : {data_source}")
    print(f"  TLS             : {'enabled' if args.tls else 'disabled'}")
    print(f"  PQC backend     : {pqc_backend_name()} ({'real' if pqc_backend_is_real() else 'demo-only'})")
    print(f"  Pretrained      : {pretrained}")
    print("=" * 60)
    print()

    # Build DataLoaders
    train_loader, val_loader, dataset_info = build_client_dataloaders(
        node_id=args.node_id,
        batch_size=args.batch_size,
        img_size=img_size,
        mock_samples=args.samples,
        val_split=float(cfg["client"].get("val_split", 0.2)),
        data_source=data_source,
        manifest_path=args.manifest,
        nii_dir=args.nii_dir,
        csv_path=args.csv_path,
        dicom_dir=args.dicom_dir,
        labels_csv=args.labels_csv,
        patient_ids=args.patient_ids,
        auto_partition=args.auto_partition,
    )
    print(
        f"  [Node {args.node_id}] Train batches: {len(train_loader)} | "
        f"Val batches: {len(val_loader)}"
    )
    print(f"  [Node {args.node_id}] Dataset info: {dataset_info}")

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
