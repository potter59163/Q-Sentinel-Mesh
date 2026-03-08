"""
Heatmap Overlay Component for Streamlit Dashboard

Displays AI prediction results with Grad-CAM heatmap overlaid
on CT slices. Shows confidence scores and hemorrhage type.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib as mpl
from matplotlib.colors import Normalize

from src.data.rsna_loader import SUBTYPES, apply_window, WINDOWS
from dashboard.i18n import T, get_lang

# Subtype display info (emoji and color only — labels come from i18n)
SUBTYPE_KEYS = {
    "epidural":          ("epidural",          "⚠️",  "#FF6B6B", "epidural_desc"),
    "intraparenchymal":  ("intraparenchymal",  "🔴", "#FF4757", "intraparenchymal_desc"),
    "intraventricular":  ("intraventricular",  "🟠", "#FF6348", "intraventricular_desc"),
    "subarachnoid":      ("subarachnoid",      "🟡", "#FFA502", "subarachnoid_desc"),
    "subdural":          ("subdural",          "🟣", "#9C88FF", "subdural_desc"),
    "any":               ("any_hemorrhage",    "🔵", "#00D4FF", "any_hemorrhage_desc"),
}

def _get_subtype_info(key: str) -> tuple:
    """Return (label, emoji, color, description) with i18n."""
    entry = SUBTYPE_KEYS.get(key, SUBTYPE_KEYS["any"])
    label_key, emoji, color, desc_key = entry
    return T(label_key), emoji, color, T(desc_key)


def render_ai_suggestion(
    xai_results: dict,
    volume_hu: np.ndarray,
    slice_idx: int,
    key_prefix: str = "xai",
    detect_thresh: float = 0.15,
):
    """
    Render AI prediction results with heatmap overlay.

    Args:
        xai_results: Output dict from src.xai.gradcam.analyze_volume()
        volume_hu:   (D, H, W) HU volume
        slice_idx:   Currently selected slice
        key_prefix:  Unique key prefix
        detect_thresh: Sensitivity threshold for flagging lesions
    """
    top_idx = xai_results["top_slice_idx"]
    all_probs = xai_results["all_probs"]  # (D, 6) tensor
    top_class_name = xai_results["top_class_name"]
    top_class_idx = xai_results["top_class_idx"]
    confidence = xai_results["confidence"]
    overlay = xai_results["overlay"]      # (H, W, 3) uint8

    # ── Prediction Summary Banner ─────────────────────────────────────────────
    info = _get_subtype_info(top_class_name)
    label, emoji, color, description = info

    if confidence > detect_thresh:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, {color}22, {color}11);
                        border: 1px solid {color}66; border-radius: 12px;
                        padding: 16px; margin-bottom: 16px;">
                <h3 style="color: {color}; margin: 0 0 4px 0;">{emoji} {label}</h3>
                <p style="color: #E2E8F0; margin: 0; font-size: 14px;">{description}</p>
                <div style="margin-top: 8px;">
                    <span style="color: #94A3B8; font-size: 13px;">{T('confidence')}: </span>
                    <span style="color: {color}; font-size: 20px; font-weight: bold;">
                        {confidence*100:.1f}%
                    </span>
                    {f'<span class="badge badge-triage" style="margin-left:12px; font-size:10px;">{T("smart_triage")}</span>' if confidence < 0.5 else ''}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.success(T("no_hemorrhage_normal"))

    # ── Side-by-Side: Original | Heatmap Overlay ─────────────────────────────
    hu_slice = volume_hu[top_idx]
    brain_slice = apply_window(hu_slice, center=WINDOWS["brain"][0], width=WINDOWS["brain"][1])

    col_orig, col_heat = st.columns(2)

    with col_orig:
        fig, ax = plt.subplots(figsize=(4, 4), facecolor="#0A0E1A")
        ax.imshow(brain_slice, cmap="gray", vmin=0, vmax=1)
        ax.set_title(T("original_ct"), color="#E2E8F0", fontsize=10)
        ax.axis("off")
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        st.caption(f"{T('most_relevant_slice')}: #{top_idx + 1}")

    with col_heat:
        fig, ax = plt.subplots(figsize=(4, 4), facecolor="#0A0E1A")
        ax.imshow(overlay)
        ax.set_title(T("ai_heatmap_hirescam"), color="#00D4FF", fontsize=10)
        ax.axis("off")
        # Colorbar
        norm = Normalize(vmin=0, vmax=1)
        sm = cm.ScalarMappable(cmap=cm.jet, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, fraction=0.04, pad=0.02)
        cbar.ax.yaxis.set_tick_params(color="white")
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white", fontsize=7)
        cbar.set_label(T("activation"), color="white", fontsize=7)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        st.caption(T("high_activation"))

    # ── Volume Scanline Chart ────────────────────────────────────────────────
    st.markdown(f"**{T('volume_prob_profile')}**")
    any_idx = SUBTYPES.index("any")
    v_probs = all_probs[:, any_idx].numpy()
    
    fig_v, ax_v = plt.subplots(figsize=(10, 2), facecolor="#0A0E1A")
    ax_v.set_facecolor("#0F172A")
    ax_v.fill_between(range(len(v_probs)), v_probs * 100, color="#00D4FF", alpha=0.3)
    ax_v.plot(v_probs * 100, color="#00D4FF", linewidth=1.5)
    
    # Mark current/top slice
    ax_v.axvline(top_idx, color="#F87171", linestyle="--", alpha=0.8, label=T("selected_slice"))
    
    ax_v.set_xlim(0, len(v_probs)-1)
    ax_v.set_ylim(0, 105)
    ax_v.set_ylabel("Prob %", color="#94A3B8", fontsize=8)
    ax_v.set_xlabel(T("slice_index"), color="#94A3B8", fontsize=8)
    ax_v.tick_params(colors="#475569", labelsize=7)
    for s in ax_v.spines.values(): s.set_edgecolor("#1E293B")
    fig_v.tight_layout(pad=0.5)
    st.pyplot(fig_v, use_container_width=True)
    plt.close(fig_v)

    # ── Hemorrhage Volume Estimate ───────────────────────────────────────────
    # Heuristic: 512x512 image, approx 0.5mm per pixel, 5mm thickness
    # Volume (ml) ≈ Sum(Probs > 0.5) * (pixel_area * thickness) / 1000
    if confidence > detect_thresh:
        # We use a simplified volume proxy based on probability integration
        # Real volume would need pixel spacing from DICOM/NIfTI header
        vol_score = v_probs.sum() * 0.45 # Rough cubic cm estimate
        
        st.markdown(
            f"""
            <div style="background:rgba(0,212,255,0.05); border-radius:8px; padding:12px; border:1px dashed #1E3050;">
                <span style="color:#94A3B8; font-size:12px;">{T('volumetric_est')}:</span>
                <span style="color:#00D4FF; font-weight:700; font-size:18px; margin-left:8px;">
                    {vol_score:.1f} ml
                </span>
                <p style="color:#475569; font-size:10px; margin:4px 0 0 0;">
                    * {T('vol_est_disclaimer')}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Per-Subtype Probability Bars (LIVE) ──────────────────────────────────
    st.markdown(f"<div style='margin-top:20px'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <b style="font-size:14px;">{T('hemorrhage_type_breakdown')}</b>
            <span style="font-size:10px; color:#475569; letter-spacing:0.05em;">
                {T('live_slice_sync')}: #{slice_idx + 1}
            </span>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    current_probs = all_probs[slice_idx]  # (6,)
    target_probs = all_probs[top_idx]    # (6,)
    
    # We show the currently SELECTED slice's probabilities
    bars_html = ""
    for i, subtype in enumerate(SUBTYPES[:5]):
        prob = float(current_probs[i].item())
        label_name, emoji, bar_color, _ = _get_subtype_info(subtype)
        pct = min(prob * 100, 100.0)
        bars_html += (
            f'<div class="prob-row">'
            f'<span class="prob-label" style="color:{bar_color};">{emoji} {label_name}</span>'
            f'<div class="prob-track">'
            f'<div class="prob-fill" style="width:{pct:.1f}%;background:{bar_color};"></div>'
            f'</div>'
            f'<span class="prob-pct" style="color:{bar_color};">{pct:.1f}%</span>'
            f'</div>'
        )
    st.markdown(bars_html, unsafe_allow_html=True)
    
    # Indicate if this is the "Focus" slice
    if slice_idx == top_idx:
        st.markdown(f"<p style='color:#00D4FF; font-size:11px; text-align:center; margin-top:-10px;'>🎯 {T('current_is_top_focus')}</p>", unsafe_allow_html=True)

    # ── Clinical Findings Summary ─────────────────────────────────────────────
    with st.expander(f"📝 {T('clinical_summary')}", expanded=True):
        if confidence > detect_thresh:
            severity = "CRITICAL" if confidence > 0.7 else "SUSPICIOUS"
            st.markdown(
                f"""
                **Status:** <span style="color:{color}">{severity}</span>  
                **Primary Finding:** {label} ({top_class_name.replace('_', ' ').title()})  
                **Localization:** Focus in slice range {max(0, top_idx-2)} to {min(len(v_probs)-1, top_idx+2)}  
                **AI Interpretation:** High probability areas detected in {T('win_brain')} window. 
                Differential includes {SUBTYPES[0] if top_class_idx != 0 else SUBTYPES[1]}.
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(T("no_hemorrhage_normal"))
