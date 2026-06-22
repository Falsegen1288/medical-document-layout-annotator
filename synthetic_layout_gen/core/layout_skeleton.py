# core/layout_skeleton.py
"""
Layout skeleton abstraction: provides empirically-sourced or heuristic
page geometry to domain generators.

A LayoutSkeleton is a frozen snapshot of page-level geometry:
  margins, zones, column structure, and element ordering hints.

SkeletonBackend is the abstract interface; two concrete backends:
  - EmpiricalCorpusBackend  (loads harvested DocLayNet stats)
  - HeuristicFallbackBackend (wraps existing hardcoded defaults)
"""

import json
import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class LayoutSkeleton:
    """Frozen page-geometry snapshot consumed by domain generators."""
    page_width_pt: float = 612.0
    page_height_pt: float = 792.0
    margin_left: float = 60.0
    margin_right: float = 60.0
    margin_top: float = 60.0
    margin_bottom: float = 60.0
    header_zone_height: float = 40.0
    footer_zone_height: float = 30.0
    n_columns: int = 1
    column_gap_pt: float = 12.0
    element_sequence: List[Tuple[str, float]] = field(default_factory=list)

    @property
    def body_width(self) -> float:
        return self.page_width_pt - self.margin_left - self.margin_right

    @property
    def body_height(self) -> float:
        return (self.page_height_pt - self.margin_top - self.margin_bottom
                - self.header_zone_height - self.footer_zone_height)

    @property
    def column_width(self) -> float:
        if self.n_columns <= 1:
            return self.body_width
        total_gap = self.column_gap_pt * (self.n_columns - 1)
        return (self.body_width - total_gap) / self.n_columns


# ──────────────────────────────────────────────
# Backend interface
# ──────────────────────────────────────────────

class SkeletonBackend:
    """Abstract backend that domain generators call to get page geometry."""

    def sample_skeleton(self, domain: str, rng: random.Random) -> LayoutSkeleton:
        raise NotImplementedError


# ──────────────────────────────────────────────
# Empirical corpus backend
# ──────────────────────────────────────────────

def _sample_from_percentiles(percentiles: Dict[str, float],
                              rng: random.Random) -> float:
    """Sample a value from a percentile distribution using linear interp."""
    keys = sorted(percentiles.keys(), key=lambda k: float(k))
    vals = [percentiles[k] for k in keys]
    # Pick a random percentile position and interpolate
    t = rng.random()
    idx = t * (len(vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(vals) - 1)
    frac = idx - lo
    return vals[lo] + frac * (vals[hi] - vals[lo])


def _sample_from_histogram(histogram: Dict[str, float],
                            rng: random.Random) -> int:
    """Sample an integer key from a histogram {key: probability}."""
    items = list(histogram.items())
    keys = [int(k) for k, _ in items]
    weights = [v for _, v in items]
    total = sum(weights)
    if total == 0:
        return keys[0] if keys else 1
    weights = [w / total for w in weights]
    return rng.choices(keys, weights=weights, k=1)[0]


class EmpiricalCorpusBackend(SkeletonBackend):
    """Loads pre-harvested layout statistics from layout_corpora/ JSON files."""

    def __init__(self, corpora_dir: str = "layout_corpora"):
        self._corpora_dir = corpora_dir
        self._cache: Dict[str, dict] = {}

    def _load_stats(self, domain: str) -> Optional[dict]:
        if domain in self._cache:
            return self._cache[domain]
        path = os.path.join(self._corpora_dir, f"{domain}_skeleton_stats.json")
        if not os.path.exists(path):
            self._cache[domain] = None
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._cache[domain] = data
        return data

    def sample_skeleton(self, domain: str, rng: random.Random) -> LayoutSkeleton:
        stats = self._load_stats(domain)
        if stats is None:
            # No corpus file → return default
            return LayoutSkeleton()

        dims = stats.get("page_dimensions", {})
        margins = stats.get("margins", {})
        zones = stats.get("zones", {})
        cols = stats.get("column_count", {"1": 1.0})

        skel = LayoutSkeleton(
            page_width_pt=_sample_from_percentiles(
                dims.get("width_pt", {"0": 612, "100": 612}), rng),
            page_height_pt=_sample_from_percentiles(
                dims.get("height_pt", {"0": 792, "100": 792}), rng),
            margin_left=_sample_from_percentiles(
                margins.get("left", {"0": 50, "100": 72}), rng),
            margin_right=_sample_from_percentiles(
                margins.get("right", {"0": 50, "100": 72}), rng),
            margin_top=_sample_from_percentiles(
                margins.get("top", {"0": 50, "100": 72}), rng),
            margin_bottom=_sample_from_percentiles(
                margins.get("bottom", {"0": 50, "100": 72}), rng),
            header_zone_height=_sample_from_percentiles(
                zones.get("header_height", {"0": 20, "100": 60}), rng),
            footer_zone_height=_sample_from_percentiles(
                zones.get("footer_height", {"0": 15, "100": 40}), rng),
            n_columns=_sample_from_histogram(cols, rng),
            column_gap_pt=_sample_from_percentiles(
                zones.get("column_gap", {"0": 10, "100": 18}), rng),
        )
        return skel


# ──────────────────────────────────────────────
# Heuristic fallback backend (per-domain defaults)
# ──────────────────────────────────────────────

_HEURISTIC_DEFAULTS: Dict[str, dict] = {
    "financial_invoice": dict(
        margin_left=60, margin_right=60, margin_top=60, margin_bottom=50,
        header_zone_height=45, footer_zone_height=30, n_columns=1,
    ),
    "scientific_paper": dict(
        margin_left=54, margin_right=54, margin_top=72, margin_bottom=72,
        header_zone_height=36, footer_zone_height=24, n_columns=2,
        column_gap_pt=18,
    ),
    "legal_opinion": dict(
        margin_left=72, margin_right=72, margin_top=72, margin_bottom=72,
        header_zone_height=30, footer_zone_height=30, n_columns=1,
    ),
    "medical_report": dict(
        margin_left=60, margin_right=60, margin_top=60, margin_bottom=50,
        header_zone_height=40, footer_zone_height=25, n_columns=1,
    ),
    "commercial_catalog": dict(
        margin_left=36, margin_right=36, margin_top=36, margin_bottom=36,
        header_zone_height=48, footer_zone_height=24, n_columns=2,
        column_gap_pt=14,
    ),
}


class HeuristicFallbackBackend(SkeletonBackend):
    """Wraps the original hardcoded margins. Used when no empirical data exists."""

    def sample_skeleton(self, domain: str, rng: random.Random) -> LayoutSkeleton:
        defaults = _HEURISTIC_DEFAULTS.get(domain, {})
        # Add ±5% jitter for variety
        def jitter(val: float) -> float:
            return val * (1.0 + rng.uniform(-0.05, 0.05))

        return LayoutSkeleton(
            page_width_pt=612.0,
            page_height_pt=792.0,
            margin_left=jitter(defaults.get("margin_left", 60)),
            margin_right=jitter(defaults.get("margin_right", 60)),
            margin_top=jitter(defaults.get("margin_top", 60)),
            margin_bottom=jitter(defaults.get("margin_bottom", 50)),
            header_zone_height=jitter(defaults.get("header_zone_height", 40)),
            footer_zone_height=jitter(defaults.get("footer_zone_height", 30)),
            n_columns=defaults.get("n_columns", 1),
            column_gap_pt=defaults.get("column_gap_pt", 12),
        )


# ──────────────────────────────────────────────
# Convenience: auto-select best backend for a domain
# ──────────────────────────────────────────────

_GLOBAL_BACKEND: Optional[SkeletonBackend] = None


def get_skeleton_backend(corpora_dir: str = "layout_corpora") -> SkeletonBackend:
    """Return the best available backend (empirical if files exist, else heuristic)."""
    global _GLOBAL_BACKEND
    if _GLOBAL_BACKEND is not None:
        return _GLOBAL_BACKEND

    empirical = EmpiricalCorpusBackend(corpora_dir)
    # Check if any corpus file exists
    if os.path.isdir(corpora_dir) and any(
        f.endswith("_skeleton_stats.json") for f in os.listdir(corpora_dir)
    ):
        _GLOBAL_BACKEND = empirical
    else:
        _GLOBAL_BACKEND = HeuristicFallbackBackend()
    return _GLOBAL_BACKEND


def sample_skeleton_for_domain(domain: str, rng: random.Random,
                                corpora_dir: str = "layout_corpora") -> LayoutSkeleton:
    """One-call convenience: get a skeleton for the given domain."""
    backend = get_skeleton_backend(corpora_dir)
    skel = backend.sample_skeleton(domain, rng)

    # If empirical returned defaults (no file), try heuristic
    if isinstance(backend, EmpiricalCorpusBackend):
        stats = backend._load_stats(domain)
        if stats is None:
            fallback = HeuristicFallbackBackend()
            skel = fallback.sample_skeleton(domain, rng)

    return skel
