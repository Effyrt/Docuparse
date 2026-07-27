"""Unit tests for the dashboard data loader.

These exercise the pure-stdlib transforms against both synthetic fixtures and
the real committed pipeline outputs, without importing Streamlit/pandas.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from dashboard import data_loader as dl  # noqa: E402


# --- transforms on synthetic fixtures --------------------------------------- #
def test_metric_cards_pass_fail_direction():
    metrics = {
        "text_avg_wer": 0.02,
        "table_avg_f1": 0.95,
        "thresholds": {"wer_threshold": 0.05, "f1_threshold": 0.87},
    }
    cards = {c["label"]: c for c in dl.metric_cards(metrics)}
    # Lower-is-better metric under its threshold passes.
    assert cards["Text WER"]["passed"] is True
    # Higher-is-better metric above its threshold passes.
    assert cards["Table F1"]["passed"] is True


def test_metric_cards_fail_when_worse_than_threshold():
    metrics = {
        "text_avg_wer": 0.10,
        "table_avg_f1": 0.50,
        "thresholds": {"wer_threshold": 0.05, "f1_threshold": 0.87},
    }
    cards = {c["label"]: c for c in dl.metric_cards(metrics)}
    assert cards["Text WER"]["passed"] is False
    assert cards["Table F1"]["passed"] is False


def test_metric_cards_none_when_missing():
    cards = {c["label"]: c for c in dl.metric_cards({})}
    assert cards["Text WER"]["passed"] is None


def test_stage_performance_and_failures():
    benchmark = {
        "stage_benchmarks": {
            "text_extraction": {
                "total_runtime_seconds": 1.5,
                "pages_processed": 0,
                "memory_usage": {"peak_memory_mb": 70.0},
                "failures": [{"file": "x.pdf", "error": "boom"}],
            }
        }
    }
    rows = dl.stage_performance(benchmark)
    assert rows[0]["stage"] == "text_extraction"
    assert rows[0]["peak_memory_mb"] == 70.0
    assert rows[0]["failure_count"] == 1
    failures = dl.benchmark_failures(benchmark)
    assert failures == [{"stage": "text_extraction", "file": "x.pdf", "error": "boom"}]


def test_drift_series_filters_non_numeric():
    drift = {"text_analysis": {"raw_data": {"word_counts": [1, 2, None, "x", 3]}}}
    assert dl.drift_series(drift, "text_analysis", "word_counts") == [1, 2, 3]


def test_loaders_tolerate_missing_files(tmp_path):
    # An empty repo root yields empty structures, never exceptions.
    assert dl.load_metrics(tmp_path) == {}
    assert dl.load_metrics_history(tmp_path) == []
    assert dl.list_reports(tmp_path) == []


# --- transforms on the real committed data ---------------------------------- #
def test_real_metrics_present_and_cards_shaped():
    metrics = dl.load_metrics()
    assert metrics, "metrics.json should be committed and non-empty"
    cards = dl.metric_cards(metrics)
    assert len(cards) == 6
    assert all("label" in c and "passed" in c for c in cards)


def test_real_benchmark_has_stages():
    rows = dl.stage_performance(dl.load_benchmark())
    stages = {r["stage"] for r in rows}
    assert {"text_extraction", "table_extraction", "docling"} <= stages


def test_real_cost_analysis_break_even():
    be = dl.break_even(dl.load_cost_analysis())
    assert "break_even_volume_pages" in be
    assert dl.infrastructure_rows(dl.load_cost_analysis()), "infra options expected"


def test_real_reports_listed():
    names = {p.name for p in dl.list_reports()}
    assert "benchmarks.md" in names
    assert "xbrl_cross_verification_report.md" in names
