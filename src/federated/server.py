"""
Flower Federated Learning Server + Strategy

Uses FedAvg aggregation strategy with:
- fraction_fit=1.0 (all 3 hospitals train each round)
- 5 federated rounds
- Per-round accuracy/AUC logging for benchmark charts
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

import flwr as fl
import numpy as np
from flwr.common import (
    FitIns,
    FitRes,
    Parameters,
    Scalar,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
from flwr.server import ServerApp, ServerConfig
from flwr.server.strategy import FedAvg
from flwr.server.client_proxy import ClientProxy

from .pqc_crypto import generate_pqc_keypair, pqc_decrypt_flwr_params, ndarray_to_payload, PQCKeyPair


# ─── Custom FedAvg Strategy with Logging ──────────────────────────────────────

class QSentinelStrategy(FedAvg):
    """
    FedAvg strategy extended with per-round metric logging.
    Records accuracy and AUC per round for the benchmark comparison chart.
    """

    def __init__(self, num_rounds: int = 5, results_path: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.num_rounds = num_rounds
        self.results_path = Path(results_path) if results_path else Path("results/fed_results.json")
        self.history: list[dict] = []

    def aggregate_fit(
        self,
        server_round: int,
        results: list,
        failures: list,
    ):
        """Aggregate model weights + log metrics."""
        aggregated_params, aggregated_metrics = super().aggregate_fit(
            server_round, results, failures
        )

        # Extract per-hospital training losses
        round_metrics = {"round": server_round, "hospitals": {}}
        for client_proxy, fit_res in results:
            metrics = fit_res.metrics
            hospital = metrics.get("hospital", f"Hospital_{id(client_proxy)}")
            round_metrics["hospitals"][hospital] = {
                "train_loss": metrics.get("train_loss", 0.0),
                "num_examples": fit_res.num_examples,
            }

        self.history.append(round_metrics)
        print(f"\n[Server] Round {server_round}/{self.num_rounds} aggregation complete.")
        return aggregated_params, aggregated_metrics

    def aggregate_evaluate(
        self,
        server_round: int,
        results: list,
        failures: list,
    ):
        """Aggregate evaluation metrics + log AUC."""
        loss, metrics = super().aggregate_evaluate(server_round, results, failures)

        # Compute weighted average AUC across hospitals
        total_examples = 0
        weighted_auc = 0.0
        for client_proxy, eval_res in results:
            n = eval_res.num_examples
            auc = eval_res.metrics.get("auc", 0.5)
            weighted_auc += auc * n
            total_examples += n

        avg_auc = weighted_auc / max(total_examples, 1)

        # Update history with eval metrics
        if self.history and self.history[-1]["round"] == server_round:
            self.history[-1]["global_auc"] = avg_auc
            self.history[-1]["global_loss"] = loss
        else:
            self.history.append({
                "round": server_round,
                "global_auc": avg_auc,
                "global_loss": loss,
            })

        print(f"[Server] Round {server_round} — Global AUC: {avg_auc:.4f}, Loss: {loss:.4f}")

        # Save results after each round
        self._save_results()

        return loss, {"auc": avg_auc}

    def _save_results(self):
        """Persist federated learning results to JSON for dashboard charts."""
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.results_path, "w") as f:
            json.dump(self.history, f, indent=2)
        print(f"[Server] Results saved to {self.results_path}")


# ─── Quantum-Enhanced Federated Strategy (CNN + VQC + PQC) ───────────────────

class QSentinelHybridStrategy(FedAvg):
    """
    FedAvg strategy for Quantum-Enhanced Federated Learning.

    Extends QSentinelStrategy with:
    - ML-KEM-512 key pair generation at server startup
    - Public key distribution to clients via configure_fit()
    - PQC decryption of incoming encrypted weight payloads before aggregation
    - Per-round PQC + quantum telemetry logging
    """

    def __init__(self, num_rounds: int = 5, results_path: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.num_rounds = num_rounds
        self.results_path = Path(results_path) if results_path else Path("results/fed_results.json")
        self.history: list[dict] = []

        # Generate server-side ML-KEM-512 key pair
        self.keypair: PQCKeyPair = generate_pqc_keypair()
        self._pqc_pk_hex: str = self.keypair.public_key.hex()
        print(
            f"\n[PQC] ML-KEM-512 keypair generated"
            f" | public_key={len(self.keypair.public_key)}B"
            f" | secret_key={len(self.keypair.secret_key)}B"
        )

    def configure_fit(self, server_round, parameters, client_manager):
        """Inject ML-KEM-512 public key into each client's fit config."""
        client_config_pairs = super().configure_fit(server_round, parameters, client_manager)
        updated = []
        for client, fit_ins in client_config_pairs:
            new_config = {**fit_ins.config, "pqc_public_key": self._pqc_pk_hex}
            updated.append((client, FitIns(fit_ins.parameters, new_config)))
        return updated

    def aggregate_fit(self, server_round, results, failures):
        """Decrypt PQC-encrypted client payloads, then run standard FedAvg."""
        decrypted_results = []
        round_metrics = {"round": server_round, "hospitals": {}, "pqc_rounds": 0}

        for client_proxy, fit_res in results:
            metrics = fit_res.metrics or {}
            hospital = metrics.get("hospital", f"Node_{id(client_proxy)}")

            if metrics.get("pqc_encrypted"):
                # Decode encrypted payload from the single uint8 ndarray
                arr = parameters_to_ndarrays(fit_res.parameters)[0]
                payload = ndarray_to_payload(arr)
                weights_list = pqc_decrypt_flwr_params(payload, self.keypair.secret_key)

                # Rebuild FitRes with plaintext parameters for FedAvg
                new_params = ndarrays_to_parameters(weights_list)
                new_fit_res = FitRes(
                    status=fit_res.status,
                    parameters=new_params,
                    num_examples=fit_res.num_examples,
                    metrics=metrics,
                )
                round_metrics["pqc_rounds"] += 1
                print(
                    f"  [Server] Decrypted {hospital}: "
                    f"KEM={metrics.get('kem_bytes', '?')}B "
                    f"payload={metrics.get('payload_bytes', '?')}B"
                )
            else:
                new_fit_res = fit_res

            round_metrics["hospitals"][hospital] = {
                "train_loss": float(metrics.get("train_loss", 0.0)),
                "num_examples": fit_res.num_examples,
                "pqc_encrypted": bool(metrics.get("pqc_encrypted", False)),
                "quantum_layer": bool(metrics.get("quantum_layer", False)),
            }
            decrypted_results.append((client_proxy, new_fit_res))

        aggregated_params, aggregated_metrics = super().aggregate_fit(
            server_round, decrypted_results, failures
        )

        self.history.append(round_metrics)
        print(
            f"\n[Server] Round {server_round}/{self.num_rounds} aggregated "
            f"| PQC nodes: {round_metrics['pqc_rounds']}/{len(results)}"
        )
        return aggregated_params, aggregated_metrics

    def aggregate_evaluate(self, server_round, results, failures):
        """Aggregate evaluation metrics + log per-round AUC."""
        loss, metrics = super().aggregate_evaluate(server_round, results, failures)

        total_examples = 0
        weighted_auc = 0.0
        for _, eval_res in results:
            n = eval_res.num_examples
            auc = eval_res.metrics.get("auc", 0.5)
            weighted_auc += auc * n
            total_examples += n

        avg_auc = weighted_auc / max(total_examples, 1)

        safe_loss = float(loss) if loss is not None else 0.0

        if self.history and self.history[-1]["round"] == server_round:
            self.history[-1]["global_auc"] = float(avg_auc)
            self.history[-1]["global_loss"] = safe_loss
        else:
            self.history.append({
                "round": server_round,
                "global_auc": float(avg_auc),
                "global_loss": safe_loss,
            })

        print(
            f"[Server] Round {server_round} — Global AUC: {avg_auc:.4f} "
            f"| Loss: {safe_loss:.4f} | quantum_layer=True"
        )
        self._save_results()
        return safe_loss, {"auc": avg_auc}

    def _save_results(self):
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.results_path, "w") as f:
            json.dump(self.history, f, indent=2)
        print(f"[Server] Results saved → {self.results_path}")


def build_hybrid_server_app(num_rounds: int = 5, results_path: Optional[str] = None) -> ServerApp:
    """Build Flower ServerApp with Quantum-Enhanced + PQC strategy."""

    def server_fn(context):
        strategy = QSentinelHybridStrategy(
            num_rounds=num_rounds,
            results_path=results_path,
            fraction_fit=1.0,
            fraction_evaluate=1.0,
            min_fit_clients=3,
            min_evaluate_clients=3,
            min_available_clients=3,
        )
        config = ServerConfig(num_rounds=num_rounds)
        return fl.server.ServerAppComponents(strategy=strategy, config=config)

    return ServerApp(server_fn=server_fn)


def build_server_app(num_rounds: int = 5, results_path: Optional[str] = None) -> ServerApp:
    """Build the Flower ServerApp with Q-Sentinel strategy."""

    def server_fn(context):
        strategy = QSentinelStrategy(
            num_rounds=num_rounds,
            results_path=results_path,
            fraction_fit=1.0,
            fraction_evaluate=1.0,
            min_fit_clients=3,
            min_evaluate_clients=3,
            min_available_clients=3,
        )
        config = ServerConfig(num_rounds=num_rounds)
        return fl.server.ServerAppComponents(strategy=strategy, config=config)

    return ServerApp(server_fn=server_fn)
