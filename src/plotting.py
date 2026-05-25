"""Plotting helpers for pilot recovery and gap outputs."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import gettempdir
from typing import Iterable

os.environ.setdefault("MPLCONFIGDIR", str(Path(gettempdir()) / "hk_visitor_conversion_mpl"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(gettempdir()) / "hk_visitor_conversion_cache"))

import matplotlib.pyplot as plt
import pandas as pd


def _prepare_axis(title: str, ylabel: str):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title(title)
    ax.set_xlabel("Month")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    return fig, ax


def plot_recovery_indices(
    df: pd.DataFrame,
    index_columns: Iterable[str],
    *,
    date_col: str = "month",
    output_path: str | Path | None = None,
):
    """Plot recovery index columns and optionally save the figure."""
    fig, ax = _prepare_axis("Recovery indices, 2018-2019 average = 100", "Index")
    plot_df = df.copy()
    plot_df[date_col] = pd.to_datetime(plot_df[date_col])

    for col in index_columns:
        if col in plot_df.columns:
            ax.plot(plot_df[date_col], plot_df[col], label=col.replace("_recovery_index", ""))

    ax.axhline(100, color="black", linewidth=1, alpha=0.5)
    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()

    if output_path:
        save_figure(fig, output_path)
    return fig, ax


def plot_conversion_gaps(
    df: pd.DataFrame,
    gap_columns: Iterable[str],
    *,
    date_col: str = "month",
    output_path: str | Path | None = None,
):
    """Plot visitor conversion gap columns and optionally save the figure."""
    fig, ax = _prepare_axis("Recovery gap versus visitor arrivals", "Index points")
    plot_df = df.copy()
    plot_df[date_col] = pd.to_datetime(plot_df[date_col])

    for col in gap_columns:
        if col in plot_df.columns:
            ax.plot(plot_df[date_col], plot_df[col], label=col.replace("_vs_visitors_gap", ""))

    ax.axhline(0, color="black", linewidth=1, alpha=0.5)
    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()

    if output_path:
        save_figure(fig, output_path)
    return fig, ax


def save_figure(fig, output_path: str | Path, *, dpi: int = 150) -> None:
    """Save a figure, creating parent directories if needed."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
