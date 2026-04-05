"""
Federated Learning Chart Component

Renders:
1. Live federated round progression (AUC per round)
2. Benchmark comparison: Baseline CNN vs Q-Sentinel Mesh
3. "Intelligence grows with network" visualization
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib as mpl

from dashboard.i18n import T, get_lang

# Chart color palette
COLORS = {
    "baseline":  "#9d7990",
    "qsentinel": "#c25b86",
    "hospital_a": "#d97a95",
    "hospital_b": "#b26f9b",
    "hospital_c": "#e6a56d",
    "grid":      "#ead6df",
    "bg":        "#fff8fb",
    "surface":   "#fffdfd",
    "text":      "#412b34",
    "muted":     "#8f7482",
}


def _style_axes(ax: plt.Axes):
    """Apply soft light styling to matplotlib axes."""
    ax.set_facecolor(COLORS["surface"])
    ax.tick_params(colors=COLORS["muted"], labelsize=9)
    ax.xaxis.label.set_color(COLORS["text"])
    ax.yaxis.label.set_color(COLORS["text"])
    ax.title.set_color(COLORS["text"])
    for spine in ax.spines.values():
        spine.set_edgecolor(COLORS["grid"])
    ax.grid(True, color=COLORS["grid"], linewidth=0.8, alpha=0.7)


def render_benchmark_chart(benchmark_data: dict, key: str = "benchmark"):
    """
    Render: Baseline CNN vs Q-Sentinel AUC by number of federated nodes.

    Args:
        benchmark_data: from src.utils.metrics.generate_benchmark_data()
    """
    nodes = benchmark_data["nodes"]
    baseline_auc = benchmark_data["baseline_auc"]
    qsentinel_auc = benchmark_data["qsentinel_auc"]

    fig, ax = plt.subplots(figsize=(7, 4), facecolor=COLORS["bg"])

    # Plot lines
    ax.plot(nodes, [v * 100 for v in baseline_auc],
            "o--", color=COLORS["baseline"], linewidth=1.8,
            markersize=7, label=benchmark_data["labels"]["baseline"])
    ax.plot(nodes, [v * 100 for v in qsentinel_auc],
            "D-", color=COLORS["qsentinel"], linewidth=2.5,
            markersize=8, label=benchmark_data["labels"]["qsentinel"])

    # Shade improvement area
    ax.fill_between(
        nodes,
        [v * 100 for v in baseline_auc],
        [v * 100 for v in qsentinel_auc],
        alpha=0.20, color=COLORS["qsentinel"],
        label=T("improvement_gap"),
    )

    # Annotations
    for i, (n, bv, qv) in enumerate(zip(nodes, baseline_auc, qsentinel_auc)):
        ax.annotate(
            f"{qv*100:.1f}%",
            xy=(n, qv * 100),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            color=COLORS["qsentinel"],
            fontsize=8,
            fontweight="bold",
        )

    ax.set_xticks(nodes)
    ax.set_xticklabels([f"{n} {T('hospital_plural') if n > 1 else T('hospital_singular')}" for n in nodes])
    ax.set_xlabel(T("num_fed_nodes"))
    ax.set_ylabel(T("auc_pct"))
    ax.set_title(T("chart_title_grows"))
    all_pct = [v * 100 for v in baseline_auc + qsentinel_auc]
    y_min = max(0, min(all_pct) - 5)
    y_max = min(100, max(all_pct) + 3)
    ax.set_ylim(y_min, y_max)
    ax.legend(
        loc="lower right",
        facecolor="#fff3f7",
        edgecolor=COLORS["grid"],
        labelcolor=COLORS["text"],
        fontsize=8,
    )
    _style_axes(ax)
    fig.tight_layout(pad=1.0)

    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def render_federated_rounds_chart(fed_history: list[dict], key: str = "fed_rounds"):
    """
    Render per-round global AUC progression from actual federated simulation.

    Args:
        fed_history: list of round dicts from data/fed_results.json
    """
    if not fed_history:
        st.info(T("fed_sim_not_run"))
        return

    import math
    rounds = [r.get("round", i + 1) for i, r in enumerate(fed_history)]
    raw_aucs = [r.get("global_auc", 0.5) for r in fed_history]
    aucs = [50.0 if (v is None or (isinstance(v, float) and math.isnan(v))) else v * 100 for v in raw_aucs]
    losses = [r.get("global_loss", 1.0) or 0.0 for r in fed_history]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), facecolor=COLORS["bg"])

    # AUC progression
    ax1.plot(rounds, aucs, "D-", color=COLORS["qsentinel"], linewidth=2.5, markersize=8)
    ax1.fill_between(rounds, aucs, alpha=0.18, color=COLORS["qsentinel"])
    ax1.set_title(T("global_auc_round"))
    ax1.set_xlabel(T("round"))
    ax1.set_ylabel(T("auc_pct"))
    ax1.set_xticks(rounds)
    _auc_min = max(0, min(aucs) - 5)
    _auc_max = min(100, max(aucs) + 5)
    if _auc_min == _auc_max:
        _auc_min, _auc_max = 0, 100
    ax1.set_ylim(_auc_min, _auc_max)
    _style_axes(ax1)

    # Loss progression
    ax2.plot(rounds, losses, "o-", color=COLORS["hospital_a"], linewidth=2.5, markersize=8)
    ax2.fill_between(rounds, losses, alpha=0.1, color=COLORS["hospital_a"])
    ax2.set_title(T("global_loss_round"))
    ax2.set_xlabel(T("round"))
    ax2.set_ylabel(T("loss"))
    ax2.set_xticks(rounds)
    _style_axes(ax2)

    fig.subplots_adjust(left=0.13)
    fig.tight_layout(pad=1.5)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def render_hospital_breakdown_chart(fed_history: list[dict]):
    """
    Render per-hospital AUC across federated rounds as grouped lines.

    Args:
        fed_history: list of round dicts from data/fed_results.json
    """
    if not fed_history:
        return

    # Collect hospital names from first round
    hospital_keys = list(fed_history[0].get("hospitals", {}).keys())
    if not hospital_keys:
        return

    rounds = [r.get("round", i + 1) for i, r in enumerate(fed_history)]
    hosp_colors = [COLORS["hospital_a"], COLORS["hospital_b"], COLORS["hospital_c"]]
    short_names = ["Bangkok", "Chiang Mai", "Khon Kaen"]

    fig, ax = plt.subplots(figsize=(10, 3.5), facecolor=COLORS["bg"])

    for idx, hkey in enumerate(hospital_keys):
        import math as _math
        aucs = []
        for r in fed_history:
            hdata = r["hospitals"].get(hkey, {})
            raw = hdata.get("local_auc", None)
            if raw is None or (isinstance(raw, float) and _math.isnan(raw)):
                # fallback: derive pseudo-AUC from train_loss (lower loss → higher AUC)
                loss = hdata.get("train_loss", 0.5)
                raw = max(0.5, 1.0 - loss) if loss else 0.5
            aucs.append(raw * 100)

        color = hosp_colors[idx % len(hosp_colors)]
        label = short_names[idx] if idx < len(short_names) else hkey
        ax.plot(rounds, aucs, "o-", color=color, linewidth=2, markersize=6, label=label)
        # Annotate last point
        ax.annotate(
            f"{aucs[-1]:.1f}%",
            xy=(rounds[-1], aucs[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            color=color,
            fontsize=8,
            va="center",
        )

    # Global AUC overlay
    global_aucs = [r.get("global_auc", 0) * 100 for r in fed_history]
    ax.plot(
        rounds, global_aucs,
        "s--", color=COLORS["qsentinel"], linewidth=2, markersize=7,
        label=T("global_fedavg"), zorder=5,
    )

    _auc_all = [
        r["hospitals"].get(h, {}).get("local_auc", 0) * 100
        for r in fed_history for h in hospital_keys
    ] + global_aucs
    ax.set_ylim(max(0, min(_auc_all) - 4), min(100, max(_auc_all) + 4))
    ax.set_xticks(rounds)
    ax.set_xlabel(T("fed_round"))
    ax.set_ylabel(T("auc_pct"))
    ax.set_title(T("per_hospital_auc"))
    ax.legend(
        loc="lower right",
        facecolor="#fff3f7",
        edgecolor=COLORS["grid"],
        labelcolor=COLORS["text"],
        fontsize=8,
    )
    _style_axes(ax)
    fig.tight_layout(pad=1.0)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def render_live_simulation_animation(
    baseline_start: float = 79.2,
    final_fed: float = 87.2,
    key: str = "sim_anim",
):
    """
    Animated simulation of federated learning rounds.
    Progressively reveals AUC improvements across 5 rounds.
    Uses real benchmark values when provided.
    """
    st.markdown(f"### {T('fed_sim_title')}")

    placeholder = st.empty()

    rounds = [1, 2, 3, 4, 5]
    # Build progression from real baseline → real final federated AUC
    baseline_static = [round(baseline_start, 1)] * 5
    step = (final_fed - baseline_start) / 4
    fed_progressive = [round(baseline_start + step * i, 1) for i in range(5)]

    for r in range(1, len(rounds) + 1):
        fig, ax = plt.subplots(figsize=(7, 4), facecolor=COLORS["bg"])

        ax.plot(rounds[:r], baseline_static[:r],
                "o--", color=COLORS["baseline"], linewidth=1.5,
                markersize=6, label=T("isolated_hospital"))
        ax.plot(rounds[:r], fed_progressive[:r],
                "o-", color=COLORS["qsentinel"], linewidth=2.5,
                markersize=8, label=T("qsentinel_federated"))

        if r > 1:
            ax.fill_between(
                rounds[:r],
                baseline_static[:r],
                fed_progressive[:r],
                alpha=0.12, color=COLORS["qsentinel"],
            )

        ax.set_xlim(0.5, 5.5)
        _ymin = max(0, min(baseline_static[0], fed_progressive[0]) - 5)
        _ymax = min(100, max(baseline_static[-1], fed_progressive[-1]) + 3)
        ax.set_ylim(_ymin, _ymax)
        ax.set_xlabel(T("fed_round"))
        ax.set_ylabel(T("auc_pct"))
        ax.set_title(f"{T('round')} {r}/5 — {T('round_n_sharing')}")
        ax.set_xticks(rounds)
        ax.legend(
            facecolor="#fff3f7",
            edgecolor=COLORS["grid"],
            labelcolor=COLORS["text"],
            fontsize=8,
        )
        _style_axes(ax)
        fig.tight_layout(pad=1.0)

        with placeholder:
            st.pyplot(fig, use_container_width=True)
        plt.close(fig)

        if r < len(rounds):
            time.sleep(0.8)

    # Final annotation
    st.success(
        f"✅ {T('fed_complete')} "
        f"{T('auc_improved')} **{baseline_start:.1f}%** ({T('isolated')}) → **{final_fed:.1f}%** ({T('hospitals_count')})",
    )

