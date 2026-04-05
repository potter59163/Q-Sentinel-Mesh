"""
Q-Sentinel Mesh — Main Streamlit Dashboard

Doctor-facing interface for:
1. CT Scan 3D viewer with slice navigation
2. AI-powered hemorrhage detection with Grad-CAM explanation
3. Federated learning intelligence dashboard
4. Post-Quantum security layer visualization
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import streamlit as st

# ─── Path Setup ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ─── Page Config (must be first st command) ───────────────────────────────────
st.set_page_config(
    page_title="Q-Sentinel Mesh",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Lazy Heavy Imports ───────────────────────────────────────────────────────
try:
    import numpy as np
    import torch
    from src.data.rsna_loader import SUBTYPES
    from src.utils.metrics import generate_benchmark_data, load_fed_results
    from dashboard.components.ct_viewer import render_ct_viewer
    from dashboard.components.fed_chart import (
        render_benchmark_chart,
        render_federated_rounds_chart,
        render_live_simulation_animation,
        render_hospital_breakdown_chart,
    )
    from dashboard.i18n import T, get_lang
    from dashboard.utils.pdf_export import generate_report_pdf
except Exception as _import_err:
    st.error(f"❌ Import Error: {_import_err}")
    st.code(traceback.format_exc())
    st.stop()


# ─── Session State Init ───────────────────────────────────────────────────────
if "scans_analyzed" not in st.session_state:
    st.session_state["scans_analyzed"] = 0
# Stored for PDF export
if "last_ct_slice" not in st.session_state:
    st.session_state["last_ct_slice"] = None
if "last_overlay" not in st.session_state:
    st.session_state["last_overlay"] = None
if "last_probs" not in st.session_state:
    st.session_state["last_probs"] = [0.0] * 5
if "last_detection" not in st.session_state:
    st.session_state["last_detection"] = ("—", 0.0)
if "pdf_bytes" not in st.session_state:
    st.session_state["pdf_bytes"] = None

# ─── Custom CSS ───────────────────────────────────────────────────────────────
with open(ROOT / "dashboard/assets/styles.css", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ─── Weights Download ─────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Downloading model weights & CT samples...")
def ensure_weights():
    """Download model weights and CT-ICH demo scans from HF Hub if not present locally."""
    from huggingface_hub import hf_hub_download

    # ── Model weights ──────────────────────────────────────────────────────────
    weights_dir = ROOT / "weights"
    weights_dir.mkdir(exist_ok=True)
    weight_files = ["finetuned_ctich.pth", "high_acc_b4.pth", "hybrid_qsentinel.pth"]
    missing_weights = [f for f in weight_files if not (weights_dir / f).exists()]
    if missing_weights:
        try:
            for fname in missing_weights:
                hf_hub_download(
                    repo_id="Pottersk/q-sentinel-weights",
                    filename=fname,
                    local_dir=str(weights_dir),
                )
        except Exception as e:
            st.warning(f"Could not download weights: {e}")

    # ── CT-ICH demo scans (real NIfTI, 049–055) ────────────────────────────────
    # /mount/src/ is read-only on Streamlit Cloud → use /tmp/ instead
    import shutil
    ct_dir = Path("/tmp/ct_samples")
    ct_dir.mkdir(parents=True, exist_ok=True)
    ct_patients = ["049", "050", "051", "052", "053", "054", "055"]
    missing_ct = [p for p in ct_patients if not (ct_dir / f"{p}.nii").exists()]
    if missing_ct:
        try:
            for pid in missing_ct:
                cached_path = hf_hub_download(
                    repo_id="Pottersk/q-sentinel-weights",
                    filename=f"ct_scans/{pid}.nii",
                )
                shutil.copy2(cached_path, str(ct_dir / f"{pid}.nii"))
        except Exception as e:
            st.warning(f"Could not download CT demo scans: {e}")

ensure_weights()

# ─── Model Loading ────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading AI model...")
def load_model(model_type: str = "baseline"):
    """Load model (cached across sessions)."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    weights_dir = ROOT / "weights"

    if model_type == "hybrid":
        weights_path = weights_dir / "hybrid_qsentinel.pth"
        if weights_path.exists():
            try:
                from src.models.hybrid_model import load_hybrid_model
                return load_hybrid_model(str(weights_path), device), device
            except Exception as _e:
                st.warning(f"Hybrid model unavailable ({_e}), falling back to CNN baseline.")

    # Prefer finetuned_ctich.pth (AUC 96%), fall back to high_acc, then baseline
    weights_path = weights_dir / "finetuned_ctich.pth"
    if not weights_path.exists():
        weights_path = weights_dir / "high_acc_b4.pth"
    if not weights_path.exists():
        weights_path = weights_dir / "baseline_b4.pth"
    if weights_path.exists():
        from src.models.cnn_encoder import load_baseline
        return load_baseline(str(weights_path), device), device

    return None, device


@st.cache_data(show_spinner=False)
def load_calibrated_thresholds() -> dict:
    """Load per-class optimal thresholds from training calibration."""
    thr_path = ROOT / "results" / "optimal_thresholds.json"
    if thr_path.exists():
        with open(thr_path, encoding="utf-8") as f:
            return json.load(f)
    # Default fallback thresholds
    return {
        "epidural": 0.13, "intraparenchymal": 0.11, "intraventricular": 0.09,
        "subarachnoid": 0.05, "subdural": 0.50, "any": 0.15,
    }


# ─── CT-ICH Dataset Paths ─────────────────────────────────────────────────────
# /tmp/ct_samples/ → writable temp dir used on Streamlit Cloud
# data/samples/    → local dev fallback
_CT_TMP_DIR   = Path("/tmp/ct_samples")
_CT_LOCAL_DIR = ROOT / "data" / "samples"


def _find_ct_file(patient_id: str):
    """Return Path to NIfTI file, checking /tmp first then local."""
    for d in [_CT_TMP_DIR, _CT_LOCAL_DIR]:
        p = d / f"{patient_id}.nii"
        if p.exists():
            return p
    return None


def get_dataset_patients() -> list:
    """Return sorted list of patient IDs available (checks both /tmp and local)."""
    found = set()
    for d in [_CT_TMP_DIR, _CT_LOCAL_DIR]:
        if d.exists():
            for f in d.glob("*.nii"):
                found.add(f.stem)
    return sorted(found)


def load_dataset_ct(patient_id: str) -> np.ndarray:
    """Load a real NIfTI CT scan and return as (D, H, W) HU array."""
    import nibabel as nib

    nii_path = _find_ct_file(patient_id)
    if nii_path is None:
        # Fallback: generate realistic synthetic volume
        from src.data.mock_data import generate_mock_volume
        return generate_mock_volume(depth=30, size=256, seed=int(patient_id) if patient_id.isdigit() else 42)

    img  = nib.load(str(nii_path))
    data = img.get_fdata(dtype=np.float32)

    if data.ndim == 4:
        data = data[..., 0]

    # Ensure (D, H, W): NIfTI is usually (H, W, D)
    shape = data.shape
    if shape[2] < shape[0] and shape[2] < shape[1]:
        volume = np.transpose(data, (2, 0, 1))
    else:
        volume = data

    volume = np.ascontiguousarray(volume)

    # HU intercept correction
    vmin, vmax = float(volume.min()), float(volume.max())
    if vmax < 5:
        volume = (volume - vmin) / (vmax - vmin + 1e-6) * 1000.0 - 500.0
    elif vmin >= 0 and vmax < 600:
        volume = (volume / (vmax + 1e-6)) * 1000.0 - 500.0
    elif vmin >= 0 and vmax > 500 and vmax < 5000:
        volume = volume - 1024.0

    return volume


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f"""
        <div style="text-align:center; padding:16px 0 8px;">
            <div style="font-size:36px; margin-bottom:6px;">🧠</div>
            <h2 style="color:#412b34; margin:0; font-size:1.2rem; letter-spacing:0.02em; font-weight:700;">
                {T('brand_name')}
            </h2>
            <p style="color:#9c7f8c; margin:4px 0 8px; font-size:11px; letter-spacing:0.06em; text-transform:uppercase;">
                {T('brand_subtitle')}
            </p>
            <span class="badge badge-online">
                <span class="dot-online"></span>{T('online')}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    # System Status
    device_str = "cuda" if torch.cuda.is_available() else "cpu"
    device_label = (
        f"🟢 {T('gpu_mode')} · {torch.cuda.get_device_name(0)}"
        if torch.cuda.is_available()
        else f"🟡 {T('cpu_mode')}"
    )
    _finetuned_exists = (ROOT / "weights" / "finetuned_ctich.pth").exists()
    _high_acc_exists = (ROOT / "weights" / "high_acc_b4.pth").exists()
    _base_exists = (ROOT / "weights" / "baseline_b4.pth").exists()
    weights_exist = _finetuned_exists or _high_acc_exists or _base_exists
    _model_label = "Fine-Tuned CT-ICH (AUC 96.0%)" if _finetuned_exists else ("High-Acc (AUC 87.6%)" if _high_acc_exists else T('loaded'))
    model_status = f"🟢 {_model_label}" if weights_exist else f"🟠 {T('mock')}"

    st.markdown(
        f"""
        <div style="background:#fff1f6; border:1px solid #ecd9e2;
                    border-radius:8px; padding:12px 14px; margin-bottom:12px;">
            <div style="font-size:10px; color:#9c7f8c; text-transform:uppercase;
                        letter-spacing:0.06em; margin-bottom:8px; font-weight:600;">{T('system_status')}</div>
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                <span style="color:#9c7f8c; font-size:12px;">{T('compute')}</span>
                <span style="color:#6d5360; font-size:12px;">{device_label}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="color:#9c7f8c; font-size:12px;">{T('ai_model_label')}</span>
                <span style="color:#6d5360; font-size:12px;">{model_status}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f"**{T('hospital_node')}**")
    hospital = st.selectbox(
        T("select_node"),
        ["Hospital A (Bangkok)", "Hospital B (Chiang Mai)", "Hospital C (Khon Kaen)"],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown(f"**{T('demo_case')}**")
    _available_patients = get_dataset_patients()
    if _available_patients:
        # Badge: show patient count
        st.markdown(
            f"""<div style="margin-bottom:6px;">
                <span style="background:#fdeaf1; border:1px solid #efb4c8;
                             border-radius:5px; padding:2px 10px; color:#c25b86;
                             font-size:11px; font-family:monospace; font-weight:500;">
                    CT-ICH dataset &nbsp;·&nbsp; {len(_available_patients)} ตัวอย่าง
                </span>
            </div>""",
            unsafe_allow_html=True,
        )
        patient_id = st.selectbox(
            "Patient ID",
            _available_patients,
            index=0,
            label_visibility="collapsed",
            help="CT-ICH Dataset (PhysioNet) — 7 demo cases",
        )
    else:
        patient_id = "049"
        st.caption("CT-ICH demo · patient 049")
    case_type = patient_id  # unified alias used elsewhere

    model_type = st.radio(
        T("ai_model_label"),
        options=["baseline", "hybrid"],
        format_func=lambda x: T('cnn_baseline') if x == "baseline" else T('qsentinel_hybrid'),
        horizontal=False,
    )

    st.divider()

    # ── CT Upload (NIfTI or DICOM) ─────────────────────────────────────────────
    st.markdown(f"**{T('upload_section')}**")

    # NIfTI uploader (.nii)
    uploaded_nii = st.file_uploader(
        "📂 NIfTI (.nii)",
        type=["nii"],
        accept_multiple_files=False,
        help="อัปโหลดไฟล์ .nii (NIfTI) หนึ่งไฟล์ต่อหนึ่ง CT scan",
        key="nii_uploader",
    )

    # DICOM uploader (.dcm)
    uploaded_dcm = st.file_uploader(
        T("upload_dicom"),
        type=["dcm"],
        accept_multiple_files=True,
        help=T("upload_dicom_help"),
        key="dicom_uploader",
    )

    if uploaded_nii:
        if st.button("⬆️ Load NIfTI Volume", use_container_width=True, type="primary", key="load_nii"):
            with st.spinner("กำลังโหลด NIfTI..."):
                try:
                    import nibabel as nib
                    import io as _io
                    import tempfile, os

                    # nibabel ต้องการ file path จริง — เขียน temp file
                    _tmp = tempfile.NamedTemporaryFile(suffix=".nii", delete=False)
                    _tmp.write(uploaded_nii.read())
                    _tmp.close()

                    _img = nib.load(_tmp.name)
                    _data = _img.get_fdata(dtype=np.float32)  # (H, W, D) or (H, W, D, T)
                    os.unlink(_tmp.name)

                    # ── Handle Dimensions ──────────────────────────────────────────
                    # NIfTI axes: often (H, W, D) or (D, H, W)
                    # We want (D, H, W) for the axial viewer
                    if _data.ndim == 4:
                        _data = _data[..., 0]
                    
                    # Heuristic: smallest dimension is usually Depth (D)
                    # If Depth is at index 0, it's already (D, H, W)
                    # If Depth is at index 2, transpose from (H, W, D)
                    _shape = _data.shape
                    if _shape[2] < _shape[0] and _shape[2] < _shape[1]:
                        _volume = np.transpose(_data, (2, 0, 1))  # (D, H, W)
                    else:
                        _volume = _data  # Assume already (D, H, W)
                    
                    _volume = np.ascontiguousarray(_volume)

                    # ── Robust Intensity Normalization ──────────────────────
                    _vmin, _vmax = float(_volume.min()), float(_volume.max())
                    _hu_warning = None
                    
                    # If range is very small (e.g. [0, 1] or [0, 3]), it's likely normalized
                    if _vmax < 5:
                        _volume = (_volume - _vmin) / (_vmax - _vmin + 1e-6) * 1000.0 - 500.0
                        _hu_warning = f"Likely normalized [0,1] range -> Mapped to [-500, 500] HU"
                    elif _vmin >= 0 and _vmax < 600:
                        _volume = (_volume / (_vmax + 1e-6)) * 1000.0 - 500.0
                        _hu_warning = f"Detected 8/9-bit range [0, {_vmax:.0f}] -> Estimated HU mapping applied"
                    elif _vmin >= 0 and _vmax > 500 and _vmax < 5000:
                        _volume = _volume - 1024.0
                        _hu_warning = f"Detected raw uint range [0, {_vmax:.0f}] -> Applied -1024 Intercept shift"
                    
                    st.session_state["real_volume"] = _volume
                    st.session_state["real_volume_name"] = uploaded_nii.name
                    st.session_state["ai_ran"] = False
                    if _hu_warning:
                        st.info(f"💡 {T('intensity_adjusted')}: {_hu_warning}")
                    st.toast(T("upload_dicom_success"), icon="✅")
                    st.rerun()
                except Exception as _e:
                    st.error(f"โหลด NIfTI ไม่สำเร็จ: {_e}")

    if uploaded_dcm:
        if st.button(T("load_dicom_btn"), use_container_width=True, type="primary", key="load_dicom"):
            with st.spinner(T("loading_dicom")):
                try:
                    import pydicom
                    import io as _io
                    
                    from src.data.rsna_loader import dicom_to_hu

                    _slices = []
                    for _f in uploaded_dcm:
                        _dcm = pydicom.dcmread(_io.BytesIO(_f.read()))
                        _slices.append(_dcm)

                    def _sort_key(s):
                        if hasattr(s, "InstanceNumber"):
                            try:
                                return float(s.InstanceNumber)
                            except Exception:
                                pass
                        if hasattr(s, "SliceLocation"):
                            try:
                                return float(s.SliceLocation)
                            except Exception:
                                pass
                        return 0.0

                    _slices.sort(key=_sort_key)
                    _hu_stack = np.stack([dicom_to_hu(s) for s in _slices])  # (D, H, W)
                    st.session_state["real_volume"] = _hu_stack
                    st.session_state["real_volume_name"] = "DICOM series"
                    st.session_state["ai_ran"] = False
                    st.toast(T("upload_dicom_success"), icon="✅")
                    st.rerun()
                except Exception as _e:
                    st.error(f"{T('upload_dicom_error')}: {_e}")

    if "real_volume" in st.session_state:
        _vs = st.session_state["real_volume"].shape
        _vname = st.session_state.get("real_volume_name", "CT")
        st.markdown(
            f"""<div style="background:#eef9f1; border:1px solid #b7dec6;
                            border-radius:8px; padding:8px 12px; font-size:11px;
                            color:#4c8f6b; margin:6px 0 8px;">
                ✅ <strong>{_vname}</strong><br>
                {_vs[0]} {T('slices')} &nbsp;·&nbsp; {_vs[1]}×{_vs[2]} px
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button(T("clear_real_ct"), use_container_width=True, key="clear_real_ct"):
            del st.session_state["real_volume"]
            st.session_state["ai_ran"] = False
            st.rerun()

    st.divider()

    st.markdown(f"**{T('export')}**")
    _cached_pdf = st.session_state.get("pdf_bytes")
    if _cached_pdf:
        st.download_button(
            label=T("export_pdf"),
            data=_cached_pdf,
            file_name=f"qsentinel_report_patient{patient_id}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.button(T("export_pdf_disabled"), use_container_width=True, disabled=True)

    st.markdown(
        f"""
        <div style="padding:16px 0 0; color:#9c7f8c; font-size:11px; text-align:center;">
            {T('version_line')}<br>
            <span style="color:#b89cab;">{T('prototype_line')}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Header ───────────────────────────────────────────────────────────────────

st.markdown(
    f"""
    <div class="hero-header">
        <div style="position:absolute; right:24px; top:10px; font-size:72px; font-weight:900;
                    color:#f0d8e4; letter-spacing:-6px; user-select:none; pointer-events:none;">
            QSM
        </div>
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:16px;">
            <div>
                <h1 style="color:#412b34; margin:0 0 4px; font-size:28px; font-weight:700; letter-spacing:-0.02em;">
                    🧠 Q-Sentinel Mesh
                </h1>
                <p style="color:#6d5360; margin:0 0 12px; font-size:13px;">
                    {T('page_desc')}
                </p>
                <div style="display:flex; gap:6px; flex-wrap:wrap;">
                    <span class="tech-pill">⚡ EfficientNet-B4</span>
                    <span class="tech-pill">🔬 VQC 4-qubit</span>
                    <span class="tech-pill">🔒 ML-KEM-512</span>
                    <span class="tech-pill">🌐 3 Hospital Nodes</span>
                </div>
            </div>
            <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                <span class="badge badge-online">
                    <span class="dot-online"></span>{T('online')}
                </span>
                <span class="badge badge-pqc">PQC · NIST FIPS 203</span>
                <span class="badge" style="background:#fdeaf1;border:1px solid #efb4c8;color:#c25b86;">
                    {T('quantum_enhanced')}
                </span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Quick Metrics Strip ───────────────────────────────────────────────────────
_ha_path = ROOT / "results" / "high_acc_results.json"
_bm_path = ROOT / "results" / "benchmark_results.json"
_global_auc_value = "—"
_global_auc_delta = T("run_pipeline_first")
if _ha_path.exists():
    try:
        with open(_ha_path, encoding="utf-8") as _f:
            _ha = json.load(_f)
        _global_auc_value = f"{_ha['best_auc'] * 100:.1f}%"
        _global_auc_delta = "High-Acc trained"
    except Exception:
        _global_auc_delta = T("run_pipeline")
elif _bm_path.exists():
    try:
        with open(_bm_path, encoding="utf-8") as _f:
            _bm = json.load(_f)
        _global_auc_value = f"{_bm['qsentinel_auc'][-1] * 100:.1f}%"
        _global_auc_delta = T("real_trained")
    except Exception:
        _global_auc_delta = T("run_pipeline")

st.markdown("<div class='metrics-shell'>", unsafe_allow_html=True)
m1, m2, m3 = st.columns(3)

with m1:
    st.metric(T("active_nodes"), "3", delta=T("federation_online"))

with m2:
    st.metric(T("global_auc"), _global_auc_value, delta=_global_auc_delta)

with m3:
    _scans = st.session_state["scans_analyzed"]
    st.metric(T("scans_analyzed"), str(_scans), delta=T("this_session"))
st.markdown("</div>", unsafe_allow_html=True)

st.divider()


# ─── Tab Layout ───────────────────────────────────────────────────────────────
tab_diag, tab_fed, tab_sec = st.tabs([
    T("tab_diagnostic"),
    T("tab_federated"),
    T("tab_security"),
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: DIAGNOSTIC VIEW
# ══════════════════════════════════════════════════════════════════════════════

with tab_diag:
    st.markdown(
        f"""
        <div class="dashboard-intro">
            <div class="panel-eyebrow">Diagnostic Workflow</div>
            <div class="dashboard-intro-title">Review the CT first, then run AI when the slice and model settings look right.</div>
            <p class="dashboard-intro-copy">
                The left panel is for image inspection and windowing. The right panel is for triage settings,
                AI execution, and clinical interpretation so the main action path stays easy to follow.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_viewer, col_ai = st.columns([1, 1], gap="large")

    with col_viewer:
        st.markdown(
            """
            <div class="panel-card">
                <div class="panel-header">
                    <div class="panel-header-copy">
                        <div class="panel-eyebrow">Viewer</div>
                        <h3 class="panel-title">CT inspection</h3>
                        <p class="panel-subtitle">Browse slices, change windows, and confirm the region you want the model to focus on.</p>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )
        if "real_volume" in st.session_state:
            volume = st.session_state["real_volume"]
            _ct_title = f"🏥 {T('using_real_ct')}"
        else:
            volume = load_dataset_ct(patient_id)
            _is_real = _find_ct_file(patient_id) is not None
            _ct_title = (
                f"📋 Patient {patient_id} \u2014 CT-ICH Dataset"
                if _is_real
                else f"🔬 Patient {patient_id} \u2014 Demo Data"
            )

        slice_idx, window = render_ct_viewer(
            volume,
            title=_ct_title,
            key_prefix="main_ct",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_ai:
        st.markdown(
            f"""
            <div class="panel-card">
                <div class="panel-header">
                    <div class="panel-header-copy">
                        <div class="panel-eyebrow">Analysis</div>
                        <h3 class="panel-title">{T('ai_analysis')}</h3>
                        <p class="panel-subtitle">Configure the detection behavior, run the model, and review the explanation in one place.</p>
                    </div>
                </div>
                <div class="meta-cluster">
                    <span class="meta-pill">
                        📍 {hospital}
                    </span>
                    <span class="meta-pill">
                        📋 Patient {patient_id}
                    </span>
                    <span class="meta-pill highlight">
                        {'⚛️ Q-Sentinel Hybrid' if model_type == 'hybrid' else '🔷 CNN Baseline'}
                    </span>
                </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"⚙️ {T('analysis_config')}", expanded=False):
            analysis_mode = st.radio(
                T("analysis_mode"),
                ["auto", "current"],
                index=0,
                format_func=lambda x: "🚀 Auto-Triage (Best Slice)" if x == "auto" else "📍 Current Selected Slice",
                horizontal=True,
            )

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            # Load calibrated threshold for 'any' class as the default sensitivity
            _cal_thr = load_calibrated_thresholds()
            _default_sensitivity = float(_cal_thr.get("any", 0.15))
            sensitivity = st.slider(
                T("ai_sensitivity"),
                min_value=0.01,
                max_value=0.50,
                value=_default_sensitivity,
                step=0.01,
                help=T("ai_sensitivity_help") + f" (Calibrated default: {_default_sensitivity:.2f})"
            )

        ai_button = st.button(
            T("run_ai_analysis"),
            type="primary",
            use_container_width=True,
            key="ai_suggest_btn",
        )

        if ai_button or st.session_state.get("ai_ran"):
            # Increment counter only on actual button click, not reruns
            if ai_button:
                st.session_state["scans_analyzed"] += 1
            st.session_state["ai_ran"] = True

            with st.spinner(T("running_analysis")):
                model, device = load_model(model_type)

                if model is None:
                    st.error(f"⚠️ **{T('demo_mode_active')}**: {T('missing_weights_msg')}")
                else:
                    try:
                        from src.xai.gradcam import analyze_volume, overlay_heatmap
                        from src.data.rsna_loader import get_volume_slice_tensor, apply_window, get_brain_mask
                        _gradcam_ok = True
                    except Exception as _gcam_err:
                        _gradcam_ok = False
                        st.warning(f"Explainability module unavailable: {_gcam_err}")

                    target_idx = None if analysis_mode == "auto" else slice_idx

                    if _gradcam_ok:
                        xai_results = analyze_volume(
                            volume_hu=volume,
                            model=model,
                            device=device,
                            target_slice_idx=target_idx,
                        )
                    else:
                        # Score-only fallback (no heatmap)
                        from src.data.rsna_loader import get_volume_slice_tensor, apply_window, WINDOWS
                        from src.data.rsna_loader import SUBTYPES as _SUBTYPES
                        best_idx = target_idx if target_idx is not None else volume.shape[0] // 2
                        _probs_list = []
                        with torch.no_grad():
                            for _i in range(volume.shape[0]):
                                _t = get_volume_slice_tensor(volume, _i).to(device)
                                _probs_list.append(model.predict_proba(_t).cpu())
                        _all_p = torch.cat(_probs_list, dim=0)
                        if target_idx is None:
                            best_idx = int(_all_p[:, 5].argmax())
                        _sp = _all_p[best_idx]
                        _tc = int(_sp[:5].argmax())
                        _conf = max(float(_sp[5]), float(_sp[:5].max()))
                        _hu  = volume[best_idx]
                        _bs  = apply_window(_hu, center=40, width=80)
                        _rgb = np.stack([_bs, _bs, _bs], axis=-1)
                        xai_results = {
                            "top_slice_idx":  best_idx,
                            "all_probs":      _all_p,
                            "top_class_idx":  _tc,
                            "top_class_name": _SUBTYPES[_tc],
                            "confidence":     _conf,
                            "heatmap":        np.zeros(_bs.shape, dtype=np.float32),
                            "overlay":        np.clip(_rgb * 255, 0, 255).astype(np.uint8),
                        }
                        st.info("Showing AI scores (heatmap unavailable)")
                    
                    # ── Preprocessing Debug View ────────────────────────
                    with st.expander(T("model_input_debug"), expanded=False):
                        t_in = get_volume_slice_tensor(volume, xai_results["top_slice_idx"], normalize=False)
                        t_np = t_in[0].permute(1, 2, 0).numpy() # (H, W, 3)
                        st.image(t_np, caption="AI Multi-Window Input (Red=Brain, Green=Blood, Blue=Subdural)", use_container_width=True, clamp=True)

                    # ── Heatmap Customization ───────────────────────────
                    with st.expander(f"🎨 {T('visualization_settings')}", expanded=False):
                        hm_opacity = st.slider(
                            T("heatmap_opacity"),
                            min_value=0.0,
                            max_value=1.0,
                            value=0.5,
                            step=0.05,
                            key="hm_alpha_slider",
                        )
                        # Re-generate overlay on-the-fly with selected alpha
                        _hu = volume[xai_results["top_slice_idx"]]
                        _brain = apply_window(_hu, center=40, width=80)
                        _mask = get_brain_mask(_hu)
                        xai_results["overlay"] = overlay_heatmap(_brain, xai_results["heatmap"], alpha=hm_opacity, brain_mask=_mask)

                    # Store for PDF
                    _hu = volume[xai_results["top_slice_idx"]]
                    st.session_state["last_ct_slice"] = apply_window(_hu, 40, 80)
                    st.session_state["last_overlay"]  = xai_results["overlay"]
                    _ap = xai_results["all_probs"][xai_results["top_slice_idx"]]
                    st.session_state["last_probs"] = [float(_ap[i]) for i in range(5)]
                    st.session_state["last_detection"] = (
                        xai_results["top_class_name"], xai_results["confidence"]
                    )
                    from dashboard.components.heatmap_overlay import render_ai_suggestion
                    render_ai_suggestion(xai_results, volume, slice_idx, key_prefix="ai_res", detect_thresh=sensitivity)

            # ── Generate & Cache PDF bytes (only on actual button click) ──
            if ai_button:
                try:
                    _fed_hist_pdf = load_fed_results(ROOT / "results/fed_results.json")
                    _bm_path_pdf = ROOT / "results" / "benchmark_results.json"
                    _bl_auc_pdf = _hy_auc_pdf = None
                    if _bm_path_pdf.exists():
                        with open(_bm_path_pdf, encoding="utf-8") as _bf2:
                            _bmd2 = json.load(_bf2)
                        _bl_auc_pdf = _bmd2["baseline_auc"][-1]
                        _hy_auc_pdf = _bmd2["qsentinel_auc"][-1]
                    _det_label_pdf, _det_conf_pdf = st.session_state["last_detection"]
                    st.session_state["pdf_bytes"] = generate_report_pdf(
                        hospital=hospital,
                        case_type=case_type,
                        model_type=model_type,
                        ct_slice=st.session_state["last_ct_slice"],
                        overlay=st.session_state["last_overlay"],
                        detection_label=_det_label_pdf,
                        confidence=_det_conf_pdf,
                        probs=st.session_state["last_probs"],
                        fed_history=_fed_hist_pdf,
                        baseline_auc=_bl_auc_pdf,
                        hybrid_auc=_hy_auc_pdf,
                    )
                except Exception as _pdf_err:
                    st.session_state["pdf_bytes"] = None
                    st.toast(f"PDF generation failed: {_pdf_err}", icon="⚠️")

            # ── Model Comparison Card ──────────────────────────────────────
            _bm_path_ai = ROOT / "results" / "benchmark_results.json"
            if _bm_path_ai.exists():
                try:
                    with open(_bm_path_ai, encoding="utf-8") as _bf:
                        _bmd = json.load(_bf)
                    _bl = _bmd["baseline_auc"][-1] * 100
                    _hy = _bmd["qsentinel_auc"][-1] * 100
                    _gain = _hy - _bl
                    _active_bl = model_type == "baseline"
                    _active_hy = model_type == "hybrid"
                    # Pre-compute all conditional values to keep HTML clean
                    _bl_bg  = "#fdeaf1" if _active_bl else "#fff1f6"
                    _bl_bdr = "#efb4c8" if _active_bl else "#ecd9e2"
                    _bl_col = "#c25b86" if _active_bl else "#9c7f8c"
                    _bl_tag = '<div style="color:#c25b86;font-size:10px;margin-top:4px;font-weight:600;">▶ Active</div>' if _active_bl else ""
                    _hy_bg  = "#fdeaf1" if _active_hy else "#fff1f6"
                    _hy_bdr = "#efb4c8" if _active_hy else "#ecd9e2"
                    _hy_col = "#c25b86" if _active_hy else "#9c7f8c"
                    _hy_tag = '<div style="color:#c25b86;font-size:10px;margin-top:4px;font-weight:600;">▶ Active</div>' if _active_hy else ""
                    st.markdown(
                        f"""<div style="background:#fffdfd;border:1px solid #ecd9e2;border-radius:10px;padding:14px 16px;margin-top:14px;">
<div style="color:#9c7f8c;font-size:10px;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px;font-weight:600;">{T('model_comparison')}</div>
<div style="display:flex;gap:8px;margin-bottom:8px;">
<div style="flex:1;background:{_bl_bg};border:1px solid {_bl_bdr};border-radius:8px;padding:10px 12px;text-align:center;">
<div style="color:#9c7f8c;font-size:10px;margin-bottom:4px;">🔷 CNN Baseline</div>
<div style="color:{_bl_col};font-size:18px;font-weight:700;font-family:monospace;">{_bl:.1f}%</div>
{_bl_tag}</div>
<div style="flex:1;background:{_hy_bg};border:1px solid {_hy_bdr};border-radius:8px;padding:10px 12px;text-align:center;">
<div style="color:#9c7f8c;font-size:10px;margin-bottom:4px;">⚛️ Q-Sentinel</div>
<div style="color:{_hy_col};font-size:18px;font-weight:700;font-family:monospace;">{_hy:.1f}%</div>
{_hy_tag}</div>
<div style="flex:1;background:#eef9f1;border:1px solid #b7dec6;border-radius:8px;padding:10px 12px;text-align:center;">
<div style="color:#9c7f8c;font-size:10px;margin-bottom:4px;">⚡ {T('quantum_gain')}</div>
<div style="color:#4c8f6b;font-size:18px;font-weight:700;font-family:monospace;">+{_gain:.1f}%</div>
</div></div></div>""",
                        unsafe_allow_html=True,
                    )
                except Exception:
                    pass
        else:
            st.markdown(
                f"""
                <div class="empty-state-card heatmap-placeholder">
                    <div style="font-size:52px; margin-bottom:12px; opacity:0.6;">🧠</div>
                    <div style="color:#6d5360; font-size:14px; font-weight:600; margin-bottom:6px;">
                        {T('ai_heatmap_ready')}
                    </div>
                    <div style="color:#9c7f8c; font-size:12px; max-width:220px; margin:0 auto; line-height:1.5;">
                        {T('click_run_ai')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="info-card" style="padding:14px 16px;">
                    <div style="color:#c25b86; font-size:12px; font-weight:700; margin-bottom:8px;">
                        {T('what_ai_does')}
                    </div>
                    <ul style="color:#6d5360; font-size:12px; margin:0; padding-left:16px; line-height:1.7;">
                        <li>{T('ai_does_1')}</li>
                        <li>{T('ai_does_2')}</li>
                        <li>{T('ai_does_3')}</li>
                        <li>{T('ai_does_4')}</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: FEDERATED INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

with tab_fed:
    st.markdown(
        f"""
        <div style="margin-bottom:20px;">
            <h2 style="color:#412b34; margin:0 0 6px; font-size:20px; font-weight:600;">{T('fed_title')}</h2>
            <p style="color:#6d5360; margin:0; font-size:13px;">
                {T('fed_subtitle')}
                <strong style="color:#4c8f6b;">{T('no_data_leaves')}</strong> {T('local_servers')}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Benchmark Chart ────────────────────────────────────────────────────────
    _benchmark_path = ROOT / "results" / "benchmark_results.json"
    if _benchmark_path.exists():
        try:
            with open(_benchmark_path, encoding="utf-8") as _f:
                benchmark_data = json.load(_f)
            data_source = T("real_results")
        except Exception:
            benchmark_data = generate_benchmark_data()
            data_source = T("sim_json_error")
    else:
        benchmark_data = generate_benchmark_data()
        data_source = T("sim_run_pipeline")

    col_chart, col_stats = st.columns([3, 1], gap="large")

    with col_chart:
        st.markdown(
            f"""
            <div class="section-heading">{T('benchmark_heading')}</div>
            <div style="color:#9c7f8c; font-size:11px; margin-bottom:8px;">{data_source}</div>
            """,
            unsafe_allow_html=True,
        )
        render_benchmark_chart(benchmark_data)

    with col_stats:
        st.markdown(f"<div class='section-heading'>{T('key_metrics')}</div>", unsafe_allow_html=True)
        _meta = benchmark_data.get("metadata", {})
        _baseline_best = _meta.get("baseline_best_auc", benchmark_data["baseline_auc"][-1])
        _hybrid_best   = _meta.get("hybrid_best_auc",   benchmark_data["qsentinel_auc"][-1])
        _fed_final     = _meta.get("fed_final_auc",      benchmark_data["qsentinel_auc"][-1])
        _improvement   = (_fed_final - _baseline_best) * 100

        st.metric(T("baseline_auc"),   f"{_baseline_best*100:.1f}%")
        st.metric(T("hybrid_auc"),     f"{_hybrid_best*100:.1f}%",   delta=f"+{(_hybrid_best-_baseline_best)*100:.1f}%")
        st.metric(T("federated_auc"),  f"{_fed_final*100:.1f}%",     delta=f"+{_improvement:.1f}% {T('vs_isolated')}")
        st.metric(T("nodes"),          "3",                           delta="Bangkok · CM · KK")

    st.divider()

    # ── Animation ─────────────────────────────────────────────────────────────
    col_anim, col_info = st.columns([3, 1], gap="large")

    with col_anim:
        if st.button(T("animate_fed"), use_container_width=True):
            _b_start = benchmark_data["baseline_auc"][0] * 100
            _b_end   = benchmark_data["qsentinel_auc"][-1] * 100
            render_live_simulation_animation(baseline_start=_b_start, final_fed=_b_end)

    with col_info:
        st.markdown(
            f"""
            <div style="background:#fff1f6; border:1px solid #ecd9e2;
                        border-radius:10px; padding:14px;">
                <div style="color:#9c7f8c; font-size:10px; text-transform:uppercase;
                            letter-spacing:0.06em; margin-bottom:10px; font-weight:600;">{T('round_config')}</div>
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="color:#9c7f8c; font-size:12px;">{T('rounds')}</span>
                    <span style="color:#6d5360; font-size:12px; font-family:monospace;">5</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="color:#9c7f8c; font-size:12px;">{T('hospitals')}</span>
                    <span style="color:#6d5360; font-size:12px; font-family:monospace;">3</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="color:#9c7f8c; font-size:12px;">{T('algorithm')}</span>
                    <span style="color:#c25b86; font-size:12px; font-family:monospace; font-weight:600;">FedAvg</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#9c7f8c; font-size:12px;">{T('privacy')}</span>
                    <span style="color:#4c8f6b; font-size:12px; font-weight:600;">{T('preserved')}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Per-round results ──────────────────────────────────────────────────────
    fed_history = load_fed_results(ROOT / "results/fed_results.json")
    if fed_history:
        st.markdown(f"<div class='section-heading'>{T('last_sim_results')}</div>", unsafe_allow_html=True)
        render_federated_rounds_chart(fed_history)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        render_hospital_breakdown_chart(fed_history)
    else:
        st.markdown(
            f"""
            <div style="background:#fff1f6; border:1px solid #ecd9e2;
                        border-radius:10px; padding:20px 24px;">
                <div style="color:#c25b86; font-weight:600; font-size:14px; margin-bottom:8px;">
                    {T('run_full_pipeline')}
                </div>
                <div style="color:#6d5360; font-size:13px; margin-bottom:12px;">
                    {T('run_full_pipeline_desc')}
                </div>
                <code style="display:block; background:#fffdfd; border:1px solid #ecd9e2;
                             border-radius:8px; padding:10px 14px; font-size:13px; color:#4c8f6b;">
                    python run_all.py
                </code>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Node Status ────────────────────────────────────────────────────────────
    st.markdown(f"<div class='section-heading'>{T('node_status')}</div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;">'
        '<span class="tech-pill">🌐 3/3 Nodes Online</span>'
        '<span class="tech-pill">🔒 PQC Encrypted</span>'
        '<span class="tech-pill">🔬 Quantum Enhanced</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    _last_round = fed_history[-1]["hospitals"] if fed_history else {}
    _node_defaults = [
        (c1, "Hospital A", "Bangkok",    "Hospital A (Bangkok)",    847,  85.1),
        (c2, "Hospital B", "Chiang Mai", "Hospital B (Chiang Mai)", 612,  83.7),
        (c3, "Hospital C", "Khon Kaen",  "Hospital C (Khon Kaen)",  534,  82.9),
    ]
    for col, short, city, fed_key, default_cases, default_auc in _node_defaults:
        _hdata = _last_round.get(fed_key, {})
        cases = _hdata.get("num_examples", default_cases)
        auc   = _hdata.get("local_auc", default_auc / 100) * 100 if _hdata else default_auc
        with col:
            st.markdown(
                f"""
                <div class="node-card">
                    <div class="node-title">
                        🏥 {short}
                        <span style="color:#9c7f8c; font-weight:400; font-size:12px;">· {city}</span>
                    </div>
                    <div class="node-auc">{auc:.1f}%</div>
                    <div class="node-stat">
                        <span class="node-stat-label">{T('local_dataset')}</span>
                        <span class="node-stat-value">{cases} {T('scans')}</span>
                    </div>
                    <div class="node-stat">
                        <span class="node-stat-label">{T('status')}</span>
                        <span class="node-stat-value green">
                            <span class="dot-online"></span>{T('online')}
                        </span>
                    </div>
                    <div class="node-stat">
                        <span class="node-stat-label">{T('encryption')}</span>
                        <span class="node-stat-value cyan">ML-KEM-512</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: SECURITY LAYER
# ══════════════════════════════════════════════════════════════════════════════

with tab_sec:
    st.markdown(
        f"""
        <div style="margin-bottom:20px;">
            <h2 style="color:#412b34; margin:0 0 6px; font-size:20px; font-weight:600;">{T('pqc_title')}</h2>
            <p style="color:#6d5360; margin:0; font-size:13px;">
                {T('pqc_subtitle')}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_flow, col_spec = st.columns([3, 2], gap="large")

    with col_flow:
        st.markdown(f"<div class='section-heading'>{T('secure_flow')}</div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="background:#fffdfd;
                        border:1px solid #ecd9e2; border-radius:12px; padding:20px 24px;">

                <div class="flow-step">
                    <div class="flow-num">1</div>
                    <div class="flow-body">
                        <div class="flow-title">{T('flow1_title')}</div>
                        <div class="flow-desc">{T('flow1_desc')}</div>
                    </div>
                </div>

                <div class="flow-step">
                    <div class="flow-num">2</div>
                    <div class="flow-body">
                        <div class="flow-title">{T('flow2_title')}</div>
                        <div class="flow-desc">{T('flow2_desc')}</div>
                    </div>
                </div>

                <div class="flow-step">
                    <div class="flow-num">3</div>
                    <div class="flow-body">
                        <div class="flow-title">{T('flow3_title')}</div>
                        <div class="flow-desc">{T('flow3_desc')}</div>
                    </div>
                </div>

                <div class="flow-step">
                    <div class="flow-num" style="background:#fdeaf1;border:1px solid #efb4c8;">→</div>
                    <div class="flow-body">
                        <div class="flow-title" style="color:#c25b86;">{T('flow4_title')}</div>
                        <div class="flow-desc" style="color:#9c7f8c;">{{ kem_ciphertext · aes_ciphertext · nonce · salt }}</div>
                    </div>
                </div>

                <div class="flow-step">
                    <div class="flow-num">4</div>
                    <div class="flow-body">
                        <div class="flow-title">{T('flow5_title')}</div>
                        <div class="flow-desc">{T('flow5_desc')}</div>
                    </div>
                </div>

                <div class="flow-step" style="border-bottom:none; padding-bottom:0;">
                    <div class="flow-num">5</div>
                    <div class="flow-body">
                        <div class="flow-title">{T('flow6_title')}</div>
                        <div class="flow-desc">{T('flow6_desc')}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_spec:
        st.markdown(f"<div class='section-heading'>{T('specifications')}</div>", unsafe_allow_html=True)
        specs = [
            (T("kem_algorithm"),    "ML-KEM-512",           "cyan"),
            (T("standard"),         "NIST FIPS 203",         "cyan"),
            (T("security_level"),   T("security_level_val"), "text"),
            (T("symmetric_cipher"), "AES-256-GCM",           "text"),
            (T("key_derivation"),   "HKDF-SHA256",           "text"),
            (T("transport"),        "TLS 1.3 + PQC",         "text"),
            (T("data_privacy"),     T("data_privacy_val"),    "green"),
            (T("compliance"),       "PDPA · HIPAA-aligned",  "text"),
        ]
        spec_rows = "".join(
            f"""
            <div class="node-stat">
                <span class="node-stat-label">{label}</span>
                <span class="node-stat-value {color}">{value}</span>
            </div>
            """
            for label, value, color in specs
        )
        st.markdown(
            f"""
            <div style="background:#fffdfd;
                        border:1px solid #ecd9e2; border-radius:12px; padding:18px 20px;">
                {spec_rows}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        st.markdown(f"<div class='section-heading'>{T('live_pqc_demo')}</div>", unsafe_allow_html=True)
        if st.button(T("gen_keypair"), use_container_width=True):
            with st.spinner(T("generating_keys")):
                try:
                    from src.federated.pqc_crypto import (
                        generate_pqc_keypair,
                        encrypt_weights,
                        decrypt_weights,
                    )

                    keypair = generate_pqc_keypair()
                    dummy_weights = np.random.randn(10).astype(np.float32).tobytes()
                    payload = encrypt_weights(dummy_weights, keypair.public_key)
                    recovered = decrypt_weights(payload, keypair.secret_key)
                    success = recovered == dummy_weights

                    st.markdown(
                        f"""
                        <div style="background:#eef9f1; border:1px solid #b7dec6;
                                    border-radius:10px; padding:14px 16px; margin-top:8px;">
                            <div style="color:#4c8f6b; font-weight:600; margin-bottom:10px;">{T('pqc_success')}</div>
                            <div style="font-family:monospace; font-size:12px; color:#6d5360; line-height:1.8;">
                                Public Key &nbsp;&nbsp;{len(keypair.public_key):,} bytes<br>
                                Secret Key &nbsp;&nbsp;{len(keypair.secret_key):,} bytes<br>
                                KEM Cipher &nbsp;&nbsp;{len(payload.kem_ciphertext):,} bytes<br>
                                AES Payload &nbsp;{len(payload.aes_ciphertext):,} bytes<br>
                                Decrypt &nbsp;&nbsp;&nbsp;&nbsp;{T('decrypt_ok') if success else T('decrypt_failed')}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                except ImportError:
                    st.warning(T("pqc_not_installed"), icon="⚠️")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()
    st.markdown(
        f"""
        <div style="background:#fdeaf1; border:1px solid #efb4c8;
                    border-radius:12px; padding:18px 22px;">
            <div style="color:#c25b86; font-weight:600; font-size:14px; margin-bottom:8px;">
                {T('why_pqc')}
            </div>
            <div style="color:#6d5360; font-size:13px; line-height:1.7;">
                {T('why_pqc_text')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



