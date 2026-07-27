"""Data access + transforms for the DocuParse results dashboard.

This module deliberately depends only on the Python standard library so it can
be unit-tested without Streamlit, pandas, or the heavy extraction stack. The
Streamlit app (``dashboard/app.py``) imports these functions and only handles
rendering.

All data comes from files the pipeline already produced and committed to the
repo (evaluation metrics, benchmarks, cost analysis, drift analysis, reports).
The dashboard does not run the pipeline; it visualizes its recorded outputs.
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Repo root = parent of the dashboard/ package.
REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> Optional[Any]:
    """Load JSON, returning None if the file is missing or malformed."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _latest(pattern: str) -> Optional[Path]:
    """Return the most recently modified file matching a glob under the repo."""
    matches = glob.glob(str(REPO_ROOT / pattern))
    if not matches:
        return None
    return Path(max(matches, key=os.path.getmtime))


# --------------------------------------------------------------------------- #
# Evaluation metrics
# --------------------------------------------------------------------------- #
def load_metrics(root: Path = REPO_ROOT) -> Dict[str, Any]:
    """Load the headline evaluation metrics (metrics.json)."""
    return _read_json(root / "metrics.json") or {}


def load_metrics_history(root: Path = REPO_ROOT) -> List[Dict[str, Any]]:
    """Load the time series of evaluation runs, sorted by timestamp."""
    data = _read_json(root / "evaluation" / "metrics" / "metrics_history.json") or []
    if not isinstance(data, list):
        return []
    return sorted(data, key=lambda r: r.get("timestamp", ""))


def metric_cards(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Shape the headline metrics into display cards with pass/fail vs thresholds.

    Each card: {label, value, target, unit, passed, lower_is_better}.
    """
    thresholds = metrics.get("thresholds", {})
    cards = [
        {
            "label": "Text WER",
            "value": metrics.get("text_avg_wer"),
            "target": thresholds.get("wer_threshold"),
            "lower_is_better": True,
        },
        {
            "label": "Text CER",
            "value": metrics.get("text_avg_cer"),
            "target": thresholds.get("cer_threshold"),
            "lower_is_better": True,
        },
        {
            "label": "Table Precision",
            "value": metrics.get("table_avg_precision"),
            "target": thresholds.get("precision_threshold"),
            "lower_is_better": False,
        },
        {
            "label": "Table Recall",
            "value": metrics.get("table_avg_recall"),
            "target": thresholds.get("recall_threshold"),
            "lower_is_better": False,
        },
        {
            "label": "Table F1",
            "value": metrics.get("table_avg_f1"),
            "target": thresholds.get("f1_threshold"),
            "lower_is_better": False,
        },
        {
            "label": "Overall Pass Rate",
            "value": metrics.get("overall_pass_rate"),
            "target": None,
            "lower_is_better": False,
        },
    ]
    for card in cards:
        value, target = card["value"], card["target"]
        if value is None or target is None:
            card["passed"] = None
        elif card["lower_is_better"]:
            card["passed"] = value <= target
        else:
            card["passed"] = value >= target
    return cards


# --------------------------------------------------------------------------- #
# Benchmarks (per-stage runtime + memory)
# --------------------------------------------------------------------------- #
def load_benchmark(root: Path = REPO_ROOT) -> Dict[str, Any]:
    """Load the most recent corrected pipeline benchmark."""
    path = _latest("benchmarks/results/CORRECTED_pipeline_benchmark_*.json")
    return _read_json(path) if path else {}


def stage_performance(benchmark: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten per-stage runtime/memory/failure counts for charting."""
    rows = []
    for stage, data in (benchmark.get("stage_benchmarks") or {}).items():
        mem = data.get("memory_usage", {}) or {}
        rows.append(
            {
                "stage": stage,
                "runtime_seconds": data.get("total_runtime_seconds"),
                "pages_processed": data.get("pages_processed"),
                "pages_failed": data.get("pages_failed", 0),
                "peak_memory_mb": mem.get("peak_memory_mb"),
                "failure_count": len(data.get("failures", []) or []),
                "avg_time_per_page": data.get("avg_time_per_page"),
            }
        )
    return rows


def benchmark_failures(benchmark: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect every recorded failure across stages (honest surfacing)."""
    failures: List[Dict[str, Any]] = []
    for stage, data in (benchmark.get("stage_benchmarks") or {}).items():
        for fail in data.get("failures", []) or []:
            failures.append({"stage": stage, **fail})
    return failures


# --------------------------------------------------------------------------- #
# Cost analysis (build vs buy)
# --------------------------------------------------------------------------- #
def load_cost_analysis(root: Path = REPO_ROOT) -> Dict[str, Any]:
    """Load the most recent cloud vs infrastructure cost analysis."""
    path = _latest("benchmarks/results/cost_analysis_*.json")
    return _read_json(path) if path else {}


def cloud_cost_rows(cost: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten cloud service processor costs into {service, processor, total_usd}."""
    rows = []
    services = (cost.get("cloud_cost_estimates", {}) or {}).get("service_costs", {}) or {}
    for service, processors in services.items():
        for processor, vals in processors.items():
            rows.append(
                {
                    "service": service,
                    "processor": processor,
                    "total_cost_usd": vals.get("total_cost_usd"),
                    "cost_per_page": vals.get("cost_per_page"),
                }
            )
    return rows


def infrastructure_rows(cost: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten self-hosted infrastructure options into {option, total_usd, ...}."""
    rows = []
    infra = (cost.get("infrastructure_comparison", {}) or {}).get(
        "infrastructure_costs", {}
    ) or {}
    for option, vals in infra.items():
        rows.append(
            {
                "option": option,
                "total_cost_usd": vals.get("total_cost_usd"),
                "description": vals.get("description", option),
            }
        )
    return rows


def break_even(cost: Dict[str, Any]) -> Dict[str, Any]:
    """Return the break-even summary block."""
    return (cost.get("infrastructure_comparison", {}) or {}).get(
        "break_even_analysis", {}
    ) or {}


# --------------------------------------------------------------------------- #
# Distribution drift
# --------------------------------------------------------------------------- #
def load_drift(root: Path = REPO_ROOT) -> Dict[str, Any]:
    """Load drift analysis raw distributions."""
    return _read_json(
        root / "evaluation" / "visualizations" / "drift_analysis_results.json"
    ) or {}


def drift_series(drift: Dict[str, Any], section: str, field: str) -> List[float]:
    """Pull a numeric series (e.g. text word_counts) out of the drift data."""
    raw = (drift.get(section, {}) or {}).get("raw_data", {}) or {}
    values = raw.get(field, []) or []
    return [v for v in values if isinstance(v, (int, float))]


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
def list_reports(root: Path = REPO_ROOT) -> List[Path]:
    """Return committed markdown reports, excluding placeholders."""
    reports_dir = root / "reports"
    if not reports_dir.exists():
        return []
    return sorted(p for p in reports_dir.glob("*.md") if p.stat().st_size > 0)


def read_report(path: Path) -> str:
    """Read a report's markdown text."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""
