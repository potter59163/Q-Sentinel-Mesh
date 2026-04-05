---
title: Q-Sentinel Mesh
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: 1.54.0
app_file: dashboard/app.py
pinned: true
---

# Q-Sentinel Mesh 🧠

> **CEDT Hackathon 2026** — Quantum-Enhanced Federated AI for Intracranial Hemorrhage Detection

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.10-red)](https://pytorch.org)
[![PennyLane](https://img.shields.io/badge/PennyLane-0.44-purple)](https://pennylane.ai)
[![Flower](https://img.shields.io/badge/Flower-1.9-green)](https://flower.ai)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## Overview

**Q-Sentinel Mesh** is a privacy-preserving AI platform for detecting **Intracranial Hemorrhage (ICH)** from CT scans. It combines classical deep learning, quantum computing, and federated learning to deliver hospital-grade diagnostics without sharing patient data.

### Five Core Pillars

| # | Component | Technology | Purpose |
|---|-----------|-----------|---------|
| 1 | CNN Baseline | EfficientNet-B4 | High-accuracy CT feature extraction |
| 2 | Quantum VQC | PennyLane 4-qubit | Quantum pattern classification |
| 3 | Hybrid Model | CNN + VQC | Best-of-both-worlds inference |
| 4 | Federated Learning | Flower (flwr) | Privacy-preserving multi-hospital training |
| 5 | Post-Quantum Crypto | ML-KEM-512 + AES-256-GCM | Quantum-safe weight encryption |

---

## Results

### Cross-Dataset Evaluation — 75 Patients (RSNA-trained → CT-ICH NIfTI)

| Hemorrhage Type | AUC | Accuracy | Sensitivity | Specificity |
|----------------|-----|----------|-------------|-------------|
| **Any ICH** | **0.934** | **86.7%** | **88.9%** | **84.6%** |
| Subdural | 0.961 | 93.3% | 100.0% | 93.0% |
| Intraparenchymal | 0.898 | 84.0% | 75.0% | 86.4% |
| Subarachnoid | 0.868 | 74.7% | 85.7% | 73.5% |
| Epidural | 0.849 | 74.7% | 76.2% | 74.1% |
| Intraventricular | 0.826 | 81.3% | 60.0% | 82.9% |

> **Training**: 674,258 DICOM slices from RSNA ICH Detection Challenge
> **Testing**: 75 independent patients from CT-ICH NIfTI dataset (cross-dataset generalization)

### Federated Learning

| Metric | Value |
|--------|-------|
| Hospitals / Clients | 3 |
| FL Rounds | 3 |
| Communication | Post-Quantum Encrypted |
| Privacy Guarantee | No raw data leaves hospital |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Q-Sentinel Mesh                      │
│                                                         │
│  CT Scan Input                                          │
│      │                                                  │
│      ▼                                                  │
│  ┌─────────────────────────────────────────┐            │
│  │        CNN Encoder (EfficientNet-B4)    │            │
│  │   674K training slices (RSNA dataset)  │            │
│  └─────────────────┬───────────────────────┘            │
│                    │ 1792-dim features                  │
│                    ▼                                    │
│  ┌─────────────────────────────────────────┐            │
│  │    Quantum VQC Layer (PennyLane)        │            │
│  │  4 qubits · AngleEmbedding · StronglyEntangling │   │
│  └─────────────────┬───────────────────────┘            │
│                    │                                    │
│                    ▼                                    │
│  ┌─────────────────────────────────────────┐            │
│  │    Classification Head (6 ICH types)   │            │
│  └─────────────────────────────────────────┘            │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │           Federated Learning Layer              │    │
│  │                                                 │    │
│  │  Hospital A ──► Local Train ──► Weights (🔐)  │    │
│  │  Hospital B ──► Local Train ──► Weights (🔐) ─┼──► Aggregate │
│  │  Hospital C ──► Local Train ──► Weights (🔐)  │    │
│  │                                                 │    │
│  │  Encryption: ML-KEM-512 + AES-256-GCM (PQC)   │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## ICH Classification

The model detects **6 hemorrhage subtypes** simultaneously:

| Type | Description |
|------|-------------|
| **Epidural** | Bleeding between skull and dura mater |
| **Intraparenchymal** | Bleeding within brain tissue |
| **Intraventricular** | Bleeding into brain ventricles |
| **Subarachnoid** | Bleeding in subarachnoid space |
| **Subdural** | Bleeding between dura and brain |
| **Any ICH** | Any intracranial hemorrhage present |

---

## Project Structure

```
q-sentinel-mesh/
├── dashboard/              # Streamlit clinical dashboard
│   ├── app.py              # Main UI
│   ├── assets/styles.css   # Custom CSS
│   └── components/         # CT viewer, heatmap, federated chart
│
├── src/
│   ├── models/
│   │   ├── cnn_encoder.py      # EfficientNet-B4 backbone
│   │   ├── vqc_layer.py        # PennyLane 4-qubit VQC
│   │   └── hybrid_model.py     # CNN + VQC combined
│   │
│   ├── federated/
│   │   ├── server.py           # Flower server + FedAvg strategy
│   │   ├── client.py           # Hospital FL client
│   │   ├── hybrid_client.py    # Quantum-enabled FL client
│   │   ├── pqc_crypto.py       # Post-quantum encryption (Kyber-512)
│   │   └── simulation.py       # 3-hospital FL simulation
│   │
│   ├── data/
│   │   ├── rsna_loader.py      # RSNA DICOM dataset loader
│   │   ├── nifti_loader.py     # CT-ICH NIfTI loader
│   │   └── mock_data.py        # Demo data generator
│   │
│   └── xai/
│       └── gradcam.py          # Grad-CAM / HiResCAM heatmaps
│
├── scripts/
│   ├── train_combined.py       # Main RSNA training script
│   ├── finetune_ctich.py       # CT-ICH fine-tuning
│   ├── eval_75patients.py      # Cross-dataset evaluation
│   └── train_hybrid.py         # Quantum hybrid training
│
├── weights/                    # Pre-trained model weights (Git LFS)
│   ├── finetuned_ctich.pth     # Best model (AUC 96.0%)
│   ├── high_acc_b4.pth         # CNN baseline (AUC 87.6%)
│   └── hybrid_qsentinel.pth    # Quantum hybrid model
│
├── results/                    # Evaluation JSON outputs
└── requirements.txt
```

---

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/potter59163/QsentinelMesh.git
cd QsentinelMesh
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac

# Install PyTorch with CUDA 12.8 (RTX 4000/5000 series)
pip install torch==2.10.0+cu128 torchvision==0.25.0+cu128 \
    --index-url https://download.pytorch.org/whl/cu128

# Install all other dependencies
pip install -r requirements.txt

# Verify the machine is ready for training / federated runs
python scripts/healthcheck.py
```

### 3. Run Dashboard

```bash
streamlit run dashboard/app.py
```

Then open [http://localhost:8501](http://localhost:8501)

---

## Dashboard Features

| Feature | Description |
|---------|-------------|
| **CT Upload** | Upload DICOM / NIfTI / PNG CT scan |
| **AI Analysis** | Real-time hemorrhage detection with probabilities |
| **Heatmap** | Grad-CAM / HiResCAM attention visualization |
| **Federated View** | Live FL training chart across 3 hospitals |
| **PDF Export** | Clinical report generation |
| **Thai/English** | Bilingual UI support |

---

## Training

### RSNA ICH Dataset (Main Training)

```bash
python scripts/train_combined.py \
    --data_dir /path/to/rsna-intracranial-hemorrhage-detection \
    --epochs 5 \
    --batch_size 8
```

### CT-ICH Fine-tuning (NIfTI)

```bash
python scripts/finetune_ctich.py \
    --data_dir /path/to/ct-ich \
    --epochs 8 \
    --lr 3e-4
```

### Federated Learning Simulation

```python
from src.federated.simulation import run_hybrid
run_hybrid()
```

### Real Multi-Machine Federated Run

1. On the server machine:

```bash
python scripts/fed_server.py --port 8443 --rounds 5 --min-clients 2
```

2. On hospital node machine A:

```bash
python scripts/fed_client.py ^
  --server <SERVER_IP>:8443 ^
  --node-id 0 ^
  --data-source ctich ^
  --nii-dir C:\data\ctich\ct_scans ^
  --csv-path C:\data\ctich\hemorrhage_diagnosis_raw_ct.csv ^
  --patient-ids 49,50,51
```

3. On hospital node machine B:

```bash
python scripts/fed_client.py ^
  --server <SERVER_IP>:8443 ^
  --node-id 1 ^
  --data-source ctich ^
  --nii-dir C:\data\ctich\ct_scans ^
  --csv-path C:\data\ctich\hemorrhage_diagnosis_raw_ct.csv ^
  --patient-ids 52,53,54
```

Optional:
- Run a third client in another terminal with `--node-id 2`
- Use `--auto-partition` when every machine has the same CT-ICH copy and you want deterministic patient assignment by node id
- Use `--manifest path\to\node.json` to keep node-local dataset settings in a file

Important:
- Real PQC now requires `kyber-py` or `pqcrypto`; insecure fallback is disabled by default
- Open TCP port `8443` on the server firewall/router
- Use `--tls` on both server and clients after generating certs with `python scripts/gen_tls_certs.py`

---

## Technology Stack

### Deep Learning
- **EfficientNet-B4** — compound scaling CNN, ImageNet pretrained
- **PyTorch 2.10** — CUDA 12.8 acceleration
- **timm** — model library for EfficientNet variants

### Quantum Computing
- **PennyLane 0.44** — quantum machine learning framework
- **4-qubit VQC** — Variational Quantum Circuit with StronglyEntanglingLayers
- **AngleEmbedding** — classical-to-quantum data encoding

### Federated Learning
- **Flower (flwr) 1.9** — production-grade FL framework
- **FedAvg** — Federated Averaging aggregation strategy
- **3-hospital simulation** — heterogeneous data distribution

### Post-Quantum Cryptography
- **ML-KEM-512 (Kyber)** — NIST PQC standard key encapsulation
- **AES-256-GCM** — symmetric encryption for model weights
- **kyber-py / pqcrypto** — real ML-KEM backends required for production runs

### Medical Imaging
- **pydicom** — DICOM file parsing
- **nibabel** — NIfTI file support
- **Grad-CAM** — gradient-based explainability

---

## Why Federated + Quantum?

### The Problem
Traditional AI for medical imaging requires centralizing patient data — a serious **PDPA/HIPAA violation** risk. Each hospital trains on limited data, leading to biased models.

### Our Solution

```
Traditional:  Hospital Data → Central Server → AI Model
              (❌ Privacy risk, data leaves hospital)

Q-Sentinel:   Hospital A trains locally ──┐
              Hospital B trains locally ──┼──► Secure Aggregation ──► Better Model
              Hospital C trains locally ──┘   (ML-KEM-512 encrypted)
              (✅ Data never leaves hospital)
```

The **Quantum VQC layer** adds computational expressiveness to the classification head, potentially capturing patterns in high-dimensional CT feature spaces that classical neural networks miss.

---

## Evaluation Protocol

- **Patient-level aggregation**: 90th percentile of per-slice probabilities
- **Threshold calibration**: Youden's J index per hemorrhage class
- **TTA (Test-Time Augmentation)**: 5× horizontal flip ensemble
- **Cross-dataset**: Train on RSNA DICOM → Test on CT-ICH NIfTI

---

## For

**CEDT Hackathon 2026** — ท้ายจุฬาเฮิร์บ

---

## License

MIT License — see [LICENSE](LICENSE)

---

## Citation

```bibtex
@software{qsentinelmesh2026,
  title  = {Q-Sentinel Mesh: Quantum-Enhanced Federated AI for ICH Detection},
  author = {CEDT Team},
  year   = {2026},
  url    = {https://github.com/potter59163/QsentinelMesh}
}
```
