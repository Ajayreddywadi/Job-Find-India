"""
charts.py — Job Vacancy Scraper
================================
Builds Matplotlib figures from aggregated job data for display
in the Streamlit dashboard.

Charts
------
- jobs_by_source_pie      : Pie chart of job counts per source
- jobs_by_location_bar    : Horizontal bar of top N locations
- jobs_by_type_bar        : Bar chart of job types
- jobs_over_time_line     : Daily posting trend (line chart)
- top_tags_bar            : Most common skill tags (horizontal bar)

All functions return a matplotlib.figure.Figure object.

Author : Job Vacancy Scraper Project
Version: 1.0.0
Updated: 2026-06-16
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

matplotlib.use("Agg")  # non-interactive backend — required for Streamlit

logger = logging.getLogger(__name__)

# ── Design tokens ─────────────────────────────────────────────────────────────

_PALETTE = [
    "#1E88E5",  # blue
    "#43A047",  # green
    "#FB8C00",  # orange
    "#8E24AA",  # purple
    "#E53935",  # red
    "#00ACC1",  # cyan
    "#FFB300",  # amber
    "#6D4C41",  # brown
    "#546E7A",  # blue-grey
    "#D81B60",  # pink
]

_BG = "#0F172A"       # dark navy background
_PANEL = "#1E293B"    # slightly lighter panel
_TEXT = "#E2E8F0"     # near-white text
_GRID = "#334155"     # subtle grid lines
_ACCENT = "#38BDF8"   # sky-blue accent


def _apply_dark_style(fig: plt.Figure, ax: plt.Axes) -> None:
    """Apply a consistent dark theme to a figure and axes pair."""
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_PANEL)
    ax.tick_params(colors=_TEXT, labelsize=9)
    ax.xaxis.label.set_color(_TEXT)
    ax.yaxis.label.set_color(_TEXT)
    ax.title.set_color(_TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(_GRID)


def _make_fig(figsize: tuple[float, float] = (7, 4)) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)
    return fig, ax


# ── Chart builders ────────────────────────────────────────────────────────────

def jobs_by_source_pie(jobs: list[dict[str, str]]) -> Optional[plt.Figure]:
    """Pie chart showing the share of jobs per data source.

    Args:
        jobs: Unified list of job dicts.

    Returns:
        Matplotlib Figure, or None if there is no data.
    """
    if not jobs:
        return None

    counts = Counter(j.get("source", "Unknown") for j in jobs)
    labels = list(counts.keys())
    sizes = list(counts.values())
    colours = _PALETTE[: len(labels)]

    fig, ax = plt.subplots(figsize=(5, 4))
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colours,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.8,
        wedgeprops={"linewidth": 1.5, "edgecolor": _BG},
    )
    for txt in texts:
        txt.set_color(_TEXT)
        txt.set_fontsize(10)
    for at in autotexts:
        at.set_color(_BG)
        at.set_fontsize(9)
        at.set_fontweight("bold")

    ax.set_title("Jobs by Source", color=_TEXT, fontsize=13, pad=12)
    plt.tight_layout()
    return fig


def jobs_by_location_bar(
    jobs: list[dict[str, str]], top_n: int = 10
) -> Optional[plt.Figure]:
    """Horizontal bar chart of the top N locations.

    Args:
        jobs:  Unified list of job dicts.
        top_n: How many locations to display.

    Returns:
        Matplotlib Figure, or None if there is no data.
    """
    if not jobs:
        return None

    counts = Counter(j.get("location", "Unknown") for j in jobs)
    top = counts.most_common(top_n)
    if not top:
        return None

    labels = [loc for loc, _ in reversed(top)]
    values = [cnt for _, cnt in reversed(top)]

    fig, ax = _make_fig(figsize=(7, max(3, len(labels) * 0.45)))
    bars = ax.barh(labels, values, color=_PALETTE[0], edgecolor=_BG, linewidth=0.6)

    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + 0.15,
            bar.get_y() + bar.get_height() / 2,
            str(val),
            va="center",
            ha="left",
            color=_TEXT,
            fontsize=8,
        )

    ax.set_xlabel("Number of Jobs", color=_TEXT, fontsize=9)
    ax.set_title(f"Top {top_n} Locations", color=_TEXT, fontsize=13)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.grid(axis="x", color=_GRID, linewidth=0.5, linestyle="--")
    ax.set_axisbelow(True)
    plt.tight_layout()
    return fig


def jobs_by_type_bar(jobs: list[dict[str, str]]) -> Optional[plt.Figure]:
    """Bar chart of job types (Full-time, Remote, Part-time, etc.).

    Args:
        jobs: Unified list of job dicts.

    Returns:
        Matplotlib Figure, or None if there is no data.
    """
    if not jobs:
        return None

    raw_counts = Counter(j.get("job_type", "") or "Unspecified" for j in jobs)
    # Normalise blanks
    counts: Counter = Counter()
    for k, v in raw_counts.items():
        counts[k.strip() or "Unspecified"] += v

    labels = list(counts.keys())
    values = list(counts.values())
    colours = _PALETTE[: len(labels)]

    fig, ax = _make_fig(figsize=(6, 3.5))
    bars = ax.bar(labels, values, color=colours, edgecolor=_BG, linewidth=0.8)

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            str(val),
            ha="center",
            va="bottom",
            color=_TEXT,
            fontsize=9,
        )

    ax.set_ylabel("Count", color=_TEXT, fontsize=9)
    ax.set_title("Jobs by Type", color=_TEXT, fontsize=13)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.grid(axis="y", color=_GRID, linewidth=0.5, linestyle="--")
    ax.set_axisbelow(True)
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    return fig


def jobs_over_time_line(jobs: list[dict[str, str]]) -> Optional[plt.Figure]:
    """Line chart of daily job postings over time.

    Args:
        jobs: Unified list of job dicts.

    Returns:
        Matplotlib Figure, or None if dates are missing.
    """
    dated = [j for j in jobs if j.get("date_posted")]
    if len(dated) < 2:
        return None

    try:
        df = pd.DataFrame(dated)
        df["date_posted"] = pd.to_datetime(df["date_posted"], errors="coerce")
        df = df.dropna(subset=["date_posted"])
        daily = df.groupby("date_posted").size().reset_index(name="count")
        daily = daily.sort_values("date_posted")
    except Exception as exc:
        logger.warning("jobs_over_time_line: %s", exc)
        return None

    if len(daily) < 2:
        return None

    fig, ax = _make_fig(figsize=(8, 3.5))
    ax.plot(
        daily["date_posted"],
        daily["count"],
        color=_ACCENT,
        linewidth=2,
        marker="o",
        markersize=4,
        markerfacecolor=_ACCENT,
    )
    ax.fill_between(
        daily["date_posted"],
        daily["count"],
        alpha=0.15,
        color=_ACCENT,
    )

    ax.set_ylabel("Jobs Posted", color=_TEXT, fontsize=9)
    ax.set_title("Job Postings Over Time", color=_TEXT, fontsize=13)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.grid(color=_GRID, linewidth=0.5, linestyle="--")
    ax.set_axisbelow(True)
    fig.autofmt_xdate(rotation=30)
    plt.tight_layout()
    return fig


def top_tags_bar(
    jobs: list[dict[str, str]], top_n: int = 15
) -> Optional[plt.Figure]:
    """Horizontal bar chart of the most frequent skill tags.

    Args:
        jobs:  Unified list of job dicts.
        top_n: How many tags to display.

    Returns:
        Matplotlib Figure, or None if there are no tags.
    """
    if not jobs:
        return None

    tag_counter: Counter = Counter()
    for job in jobs:
        raw_tags = job.get("tags", "") or ""
        for tag in raw_tags.split(","):
            tag = tag.strip().lower()
            if tag:
                tag_counter[tag] += 1

    top = tag_counter.most_common(top_n)
    if not top:
        return None

    labels = [t for t, _ in reversed(top)]
    values = [c for _, c in reversed(top)]

    fig, ax = _make_fig(figsize=(7, max(3, len(labels) * 0.38)))
    bars = ax.barh(
        labels,
        values,
        color=[_PALETTE[i % len(_PALETTE)] for i in range(len(labels))],
        edgecolor=_BG,
        linewidth=0.6,
    )

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + 0.1,
            bar.get_y() + bar.get_height() / 2,
            str(val),
            va="center",
            ha="left",
            color=_TEXT,
            fontsize=8,
        )

    ax.set_xlabel("Occurrences", color=_TEXT, fontsize=9)
    ax.set_title(f"Top {top_n} Skill Tags", color=_TEXT, fontsize=13)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.grid(axis="x", color=_GRID, linewidth=0.5, linestyle="--")
    ax.set_axisbelow(True)
    plt.tight_layout()
    return fig
