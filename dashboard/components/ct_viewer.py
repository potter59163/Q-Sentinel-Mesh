"""
CT Scan Slice Viewer Component for Streamlit Dashboard

Renders an interactive DICOM/volume viewer with:
- Axial slice slider
- Multi-window display options
- HU statistics and mini histogram
"""

from __future__ import annotations

import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib as mpl

from dashboard.i18n import T, get_lang

# Use a font that supports Thai characters on Windows
for _thai_font in ["Tahoma", "Leelawadee UI", "Leelawadee", "Arial Unicode MS", "DejaVu Sans"]:
    try:
        mpl.font_manager.findfont(_thai_font, raise_if_missing=True)
        mpl.rcParams["font.family"] = _thai_font
        break
    except Exception:
        continue


_WINDOW_PRESETS = {
    "brain":    (40,   80,  "🧠"),
    "blood":    (60,  120,  "🩸"),
    "subdural": (75,  215,  "🔵"),
    "bone":     (400, 2000, "🦴"),
    "wide":     (50,  400,  "🔭"),
}


def _apply_window_display(hu: np.ndarray, window: str) -> np.ndarray:
    center, width, _ = _WINDOW_PRESETS.get(window, _WINDOW_PRESETS["brain"])
    low  = center - width / 2.0
    high = center + width / 2.0
    return np.clip((hu - low) / (high - low), 0.0, 1.0)


def render_ct_viewer(
    volume_hu: np.ndarray,
    title: str = "CT Scan Viewer",
    key_prefix: str = "ctv",
) -> tuple[int, str]:
    """
    Render interactive CT Scan viewer with slice slider and HU histogram.

    Returns:
        (selected_slice_idx, selected_window)
    """
    depth = volume_hu.shape[0]

    # ── Title row ─────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between;
                    margin-bottom:10px;">
            <h3 style="color:#E2E8F0; margin:0; font-size:15px; font-weight:600;">
                {title}
            </h3>
            <span style="background:rgba(0,212,255,0.1); border:1px solid rgba(0,212,255,0.2);
                         border-radius:6px; padding:3px 10px; color:#00D4FF;
                         font-size:11px; font-family:monospace;">
                {depth} {T('slices')}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Controls row ───────────────────────────────────────────────────────────
    col_slider, col_window = st.columns([4, 2])

    with col_slider:
        slice_idx = st.slider(
            T("axial_slice"),
            min_value=0,
            max_value=depth - 1,
            value=depth // 2,
            key=f"{key_prefix}_slice_slider",
            help=T("scroll_slices"),
            label_visibility="collapsed",
        )

    _WIN_LABELS = {
        "brain": T("win_brain"),
        "blood": T("win_blood"),
        "subdural": T("win_subdural"),
        "bone": T("win_bone"),
        "wide": T("win_wide"),
    }

    with col_window:
        window_options = list(_WINDOW_PRESETS.keys())
        window = st.selectbox(
            T("window"),
            options=window_options,
            format_func=lambda w: f"{_WINDOW_PRESETS[w][2]} {_WIN_LABELS.get(w, w.title())}",
            index=0,
            key=f"{key_prefix}_window_select",
            label_visibility="collapsed",
        )

    # ── CT Image ───────────────────────────────────────────────────────────────
    hu_slice = volume_hu[slice_idx]
    display_slice = _apply_window_display(hu_slice, window)

    _, wwidth, _ = _WINDOW_PRESETS[window]
    wcenter, _, _ = _WINDOW_PRESETS[window]

    fig, ax = plt.subplots(figsize=(5, 5), facecolor="#060A14")
    ax.imshow(display_slice, cmap="gray", vmin=0, vmax=1, interpolation="bilinear")

    # Clinical overlay: slice info
    ax.text(
        5, 10,
        f"S{slice_idx + 1:02d}/{depth}",
        color="#00D4FF", fontsize=8, family="monospace",
        bbox=dict(facecolor="#060A14", alpha=0.6, edgecolor="none", pad=2),
    )
    ax.text(
        5, display_slice.shape[0] - 6,
        f"W:{wwidth} / C:{wcenter}",
        color="#94A3B8", fontsize=7, family="monospace",
        bbox=dict(facecolor="#060A14", alpha=0.5, edgecolor="none", pad=2),
    )

    # HU stats
    roi_hu = hu_slice[(hu_slice > -200) & (hu_slice < 200)]
    if len(roi_hu) > 0:
        ax.text(
            display_slice.shape[1] - 5, display_slice.shape[0] - 6,
            f"HU {roi_hu.mean():.0f}±{roi_hu.std():.0f}",
            color="#FFD166", fontsize=7, family="monospace", ha="right",
            bbox=dict(facecolor="#060A14", alpha=0.5, edgecolor="none", pad=2),
        )

    ax.axis("off")
    fig.tight_layout(pad=0.3)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    # ── Slice position bar ────────────────────────────────────────────────────
    pct = (slice_idx + 1) / depth * 100
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:8px; margin-top:4px;">
            <div style="flex:1; background:#1A2540; border-radius:3px; height:4px; overflow:hidden;">
                <div style="width:{pct:.1f}%; background:linear-gradient(90deg,#0066CC,#00D4FF);
                             height:100%; border-radius:3px; transition:width 0.3s;"></div>
            </div>
            <span style="color:#475569; font-size:11px; font-family:monospace; min-width:50px; text-align:right;">
                {pct:.0f}% {T('depth')}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Mini HU histogram ──────────────────────────────────────────────────────
    with st.expander(T("hu_histogram"), expanded=False):
        hu_flat = hu_slice.flatten()
        hu_valid = hu_flat[(hu_flat > -1100) & (hu_flat < 3100)]

        fig2, ax2 = plt.subplots(figsize=(5, 1.8), facecolor="#060A14")
        ax2.set_facecolor("#0A0F1C")
        ax2.hist(hu_valid, bins=60, color="#00D4FF", alpha=0.7, rwidth=0.85)

        # Mark tissue ranges
        for _, lo, hi, color in [
            ("Air", -1000, -200, "#475569"),
            ("Brain", -50, 80, "#4ADE80"),
            ("Blood", 50, 100, "#F87171"),
            ("Bone", 300, 3000, "#FFD166"),
        ]:
            mask = (hu_valid >= lo) & (hu_valid <= hi)
            if mask.any():
                ax2.axvspan(lo, hi, alpha=0.08, color=color)

        ax2.set_xlabel(T("hu_value"), color="#64748B", fontsize=7)
        ax2.set_ylabel(T("count"), color="#64748B", fontsize=7)
        ax2.tick_params(colors="#475569", labelsize=7)
        for spine in ax2.spines.values():
            spine.set_edgecolor("#1A2540")
        ax2.grid(True, color="#1A2540", linewidth=0.5, alpha=0.6)
        fig2.tight_layout(pad=0.5)
        st.pyplot(fig2, use_container_width=True)
        plt.close(fig2)

        # Tissue legend
        st.markdown(
            """
            <div style="display:flex; gap:14px; flex-wrap:wrap; margin-top:6px;">
                <span style="color:#475569; font-size:11px;">◼ Air (-1000)</span>
                <span style="color:#4ADE80; font-size:11px;">◼ Brain (20–40)</span>
                <span style="color:#F87171; font-size:11px;">◼ Blood (50–80)</span>
                <span style="color:#FFD166; font-size:11px;">◼ Bone (400+)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return slice_idx, window
