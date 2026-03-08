"""
Variational Quantum Circuit (VQC) Layer — PennyLane 0.44.0

Architecture:
    AmplitudeEmbedding (n_qubits=4, input_dim=16)
    → StronglyEntanglingLayers (n_layers=2)
    → PauliZ expectation measurements
    → TorchLayer (fully differentiable via backprop)

NOTE: VQC runs on CPU. CNN backbone runs on CUDA.
      Tensors are explicitly moved between devices in HybridModel.
"""

from __future__ import annotations

import pennylane as qml
from pennylane import numpy as pnp
import torch
import torch.nn as nn

# ─── Quantum Circuit Configuration ────────────────────────────────────────────

N_QUBITS = 4        # 2^4 = 16 → matches projection from CNN feature dim
N_LAYERS = 2        # StronglyEntanglingLayers depth
INPUT_DIM = 2 ** N_QUBITS  # 16 → AmplitudeEmbedding input size

dev = qml.device("default.qubit", wires=N_QUBITS)


# ─── Quantum Node ──────────────────────────────────────────────────────────────

@qml.qnode(dev, interface="torch", diff_method="backprop")
def variational_circuit(inputs: torch.Tensor, weights: torch.Tensor) -> list:
    """
    Core VQC: encodes classical features into quantum states,
    applies entangling layers, and returns expectation values.

    Args:
        inputs:  (INPUT_DIM,) = (16,) normalized feature vector
        weights: StronglyEntanglingLayers shape (N_LAYERS, N_QUBITS, 3)
    Returns:
        list of N_QUBITS PauliZ expectation values in [-1, 1]
    """
    # Encode classical data as quantum amplitudes
    qml.AmplitudeEmbedding(inputs, wires=range(N_QUBITS), normalize=True, pad_with=0.0)

    # Variational ansatz: parameterized entangling layers
    qml.StronglyEntanglingLayers(weights, wires=range(N_QUBITS))

    # Measure expectation values of Z on each qubit
    return [qml.expval(qml.PauliZ(i)) for i in range(N_QUBITS)]


# ─── TorchLayer Wrapper ───────────────────────────────────────────────────────

def build_vqc_layer() -> qml.qnn.TorchLayer:
    """
    Returns a differentiable nn.Module-compatible VQC layer.

    Input shape:  (batch, 16)
    Output shape: (batch, 4)  — PauliZ measurements
    """
    weight_shapes = {
        "weights": qml.StronglyEntanglingLayers.shape(
            n_layers=N_LAYERS, n_wires=N_QUBITS
        )
    }
    return qml.qnn.TorchLayer(variational_circuit, weight_shapes)


# ─── Standalone VQC Module (for direct use / testing) ─────────────────────────

class VQCModule(nn.Module):
    """
    Standalone VQC module with input projection.

    Input:  (B, feature_dim)
    Output: (B, N_QUBITS)
    """

    def __init__(self, feature_dim: int = 1792):
        super().__init__()

        # Project CNN features to quantum input dimension (2^n_qubits)
        self.projection = nn.Sequential(
            nn.Linear(feature_dim, INPUT_DIM),
            nn.LayerNorm(INPUT_DIM),
            nn.Tanh(),   # bound to [-1,1] → more stable AmplitudeEmbedding
        )

        self.vqc = build_vqc_layer()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (B, feature_dim) on CUDA
        Returns:
            q_out: (B, N_QUBITS) on CPU
        """
        # Project on GPU for speed
        projected = self.projection(x)          # (B, 16) on CUDA

        # VQC must run on CPU (PennyLane default.qubit is CPU-only)
        projected_cpu = projected.cpu()          # move to CPU

        q_out = self.vqc(projected_cpu)          # (B, 4) on CPU
        return q_out
