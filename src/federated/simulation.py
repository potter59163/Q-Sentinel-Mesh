"""
Federated Learning Simulation Entry Point

Simulates 3 hospital nodes training independently, then
aggregating their model updates on the central server.

Run with:
    python -m src.federated.simulation
"""

from __future__ import annotations

# Windows + CUDA compatibility — must be first
import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import json
import os
from pathlib import Path
from typing import Optional

import torch
import numpy as np
from torch.utils.data import DataLoader, random_split, Subset
import flwr as fl
from flwr.client import ClientApp
from flwr.common import Context
from flwr.simulation import run_simulation

from .client import QSentinelClient
from .hybrid_client import HybridQSentinelClient
from .server import build_server_app, build_hybrid_server_app

# ─── Configuration ────────────────────────────────────────────────────────────

NUM_CLIENTS = 3
NUM_ROUNDS = 5
LOCAL_EPOCHS = 1
BATCH_SIZE = 16
IMG_SIZE = 224
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

DATA_DIR = Path("data")
LABELS_CSV = Path("data/stage_2_train.csv")
RESULTS_PATH = Path("results/fed_results.json")


# ─── Dataset Partitioning ─────────────────────────────────────────────────────

def prepare_partitions(
    dataset,
    num_clients: int = NUM_CLIENTS,
    val_split: float = 0.15,
    seed: int = 42,
):
    """
    Split dataset into N equal partitions (one per hospital), each with
    its own train/val split. Uses random_split for reproducibility.
    """
    total = len(dataset)
    partition_size = total // num_clients
    sizes = [partition_size] * num_clients
    sizes[-1] += total - sum(sizes)  # remainder to last partition

    generator = torch.Generator().manual_seed(seed)
    partitions = random_split(dataset, sizes, generator=generator)

    splits = []
    for part in partitions:
        n_val = max(1, int(len(part) * val_split))
        n_train = len(part) - n_val
        gen = torch.Generator().manual_seed(seed)
        train, val = random_split(part, [n_train, n_val], generator=gen)
        splits.append((train, val))

    return splits


# ─── Client Factory ───────────────────────────────────────────────────────────

# Global dataset splits (populated in main)
_partitions: list = []


def client_fn(context: Context):
    """Flower ClientApp factory — called per virtual client per round."""
    partition_id = int(context.node_config["partition-id"])
    train_set, val_set = _partitions[partition_id]

    train_loader = DataLoader(
        train_set,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=2,
        pin_memory=(DEVICE == "cuda"),
    )
    val_loader = DataLoader(
        val_set,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=2,
        pin_memory=(DEVICE == "cuda"),
    )

    client = QSentinelClient(
        partition_id=partition_id,
        train_loader=train_loader,
        val_loader=val_loader,
        device=DEVICE,
        local_epochs=LOCAL_EPOCHS,
    )
    return client.to_client()


client_app = ClientApp(client_fn=client_fn)
server_app = build_server_app(num_rounds=NUM_ROUNDS, results_path=str(RESULTS_PATH))


# ─── Hybrid Quantum Client Factory ────────────────────────────────────────────

_hybrid_partitions: list = []


def _hybrid_client_fn(context: Context):
    """Flower ClientApp factory for HybridQSentinelClient."""
    partition_id = int(context.node_config["partition-id"])
    train_set, val_set = _hybrid_partitions[partition_id]

    train_loader = DataLoader(
        train_set, batch_size=BATCH_SIZE, shuffle=True,
        num_workers=0, pin_memory=False,
    )
    val_loader = DataLoader(
        val_set, batch_size=BATCH_SIZE, shuffle=False,
        num_workers=0, pin_memory=False,
    )

    # Use pretrained hybrid weights if available (fast convergence)
    pretrained = Path("weights/hybrid_qsentinel.pth")

    client = HybridQSentinelClient(
        partition_id=partition_id,
        train_loader=train_loader,
        val_loader=val_loader,
        device=DEVICE,
        local_epochs=LOCAL_EPOCHS,
        pretrained_path=pretrained if pretrained.exists() else None,
    )
    return client.to_client()


hybrid_client_app = ClientApp(client_fn=_hybrid_client_fn)
hybrid_server_app = build_hybrid_server_app(
    num_rounds=NUM_ROUNDS, results_path=str(RESULTS_PATH)
)


# ─── Main ─────────────────────────────────────────────────────────────────────

def run(dataset=None):
    """
    Launch federated simulation.

    Args:
        dataset: RSNADataset or any torch Dataset. If None, uses mock data.
    """
    global _partitions

    if dataset is None:
        # Use mock data if real data not available
        print("[Simulation] Real dataset not provided — using mock data.")
        from ..data.mock_data import build_mock_dataset
        dataset = build_mock_dataset(n_samples=300 * NUM_CLIENTS)

    _partitions = prepare_partitions(dataset, num_clients=NUM_CLIENTS)
    print(f"[Simulation] Partitions: {[len(p[0]) for p in _partitions]} train samples per node")

    # NOTE: num_gpus=0.0 is intentional for Windows CUDA IPC safety.
    # Each ClientApp manages CUDA internally.
    backend_config = {
        "client_resources": {
            "num_cpus": 2,
            "num_gpus": 0.0,
        }
    }

    print(f"\n{'='*60}")
    print(f"  Q-Sentinel Mesh — Federated Learning Simulation")
    print(f"  Nodes: {NUM_CLIENTS} hospitals | Rounds: {NUM_ROUNDS}")
    print(f"  Device: {DEVICE.upper()}")
    print(f"{'='*60}\n")

    run_simulation(
        server_app=server_app,
        client_app=client_app,
        num_supernodes=NUM_CLIENTS,
        backend_config=backend_config,
    )

    print(f"\n[Simulation] Complete. Results saved to {RESULTS_PATH}")
    return json.loads(RESULTS_PATH.read_text()) if RESULTS_PATH.exists() else []


# ─── Quantum-Enhanced Federated Simulation ────────────────────────────────────

def run_hybrid(dataset=None) -> list[dict]:
    """
    Launch Quantum-Enhanced Federated Learning simulation.

    Each hospital node uses HybridQSentinel (CNN + VQC).
    Model weights are PQC-encrypted (ML-KEM-512) before transmission.

    Args:
        dataset: Torch Dataset. If None, falls back to mock data.

    Returns:
        List of per-round federated metrics dicts.
    """
    global _hybrid_partitions

    if dataset is None:
        print("[Simulation] No real dataset — using mock data for hybrid FL.")
        from ..data.mock_data import build_mock_dataset
        dataset = build_mock_dataset(n_samples=300 * NUM_CLIENTS)

    _hybrid_partitions = prepare_partitions(dataset, num_clients=NUM_CLIENTS)
    print(
        f"[Simulation] Hybrid partitions: "
        f"{[len(p[0]) for p in _hybrid_partitions]} train samples per node"
    )

    backend_config = {
        "client_resources": {
            "num_cpus": 2,
            "num_gpus": 0.0,
        }
    }

    print(f"\n{'='*60}")
    print(f"  Q-Sentinel Mesh — Quantum-Enhanced Federated Learning")
    print(f"  Model: HybridQSentinel (EfficientNet-B4 + VQC)")
    print(f"  Crypto: ML-KEM-512 + AES-256-GCM (Post-Quantum)")
    print(f"  Nodes: {NUM_CLIENTS} hospitals | Rounds: {NUM_ROUNDS}")
    print(f"  Device: {DEVICE.upper()}")
    print(f"{'='*60}\n")

    run_simulation(
        server_app=hybrid_server_app,
        client_app=hybrid_client_app,
        num_supernodes=NUM_CLIENTS,
        backend_config=backend_config,
    )

    print(f"\n[Simulation] Quantum-Enhanced FL complete. Results → {RESULTS_PATH}")
    return json.loads(RESULTS_PATH.read_text()) if RESULTS_PATH.exists() else []


if __name__ == "__main__":
    run_hybrid()
