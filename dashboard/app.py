"""DocuParse results dashboard (Streamlit).

Visualizes the pipeline's *recorded* outputs — evaluation metrics, per-stage
benchmarks, build-vs-buy cost analysis, distribution drift, and the markdown
reports. It does NOT run the extraction pipeline (that needs the heavy stack and
minutes per document); it reads the JSON/markdown the pipeline already produced.

Run locally:
    pip install -r dashboard/requirements.txt
    streamlit run dashboard/app.py

All data access lives in dashboard/data_loader.py (pure stdlib, unit-tested).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard import data_loader as dl  # noqa: E402

st.set_page_config(page_title="DocuParse Dashboard", page_icon="📄", layout="wide")


def _fmt(value, digits: int = 4) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
st.sidebar.title("📄 DocuParse")
st.sidebar.caption(
    "Results dashboard for the SEC-filing extraction pipeline. "
    "Figures are read from committed pipeline outputs, not generated live."
)
page = st.sidebar.radio(
    "View",
    ["Overview", "Benchmarks", "Cost (Build vs Buy)", "Distribution Drift", "Reports"],
)
st.sidebar.info(
    "This dashboard visualizes recorded runs. A live 'upload a PDF and parse' "
    "demo is intentionally out of scope — the extraction stack (Docling, layout "
    "models, OCR) is heavy and slow to host."
)


# --------------------------------------------------------------------------- #
# Overview
# --------------------------------------------------------------------------- #
def render_overview() -> None:
    st.title("Evaluation Overview")
    metrics = dl.load_metrics()
    if not metrics:
        st.warning("No metrics.json found.")
        return

    cards = dl.metric_cards(metrics)
    cols = st.columns(3)
    for i, card in enumerate(cards):
        with cols[i % 3]:
            target = card["target"]
            help_txt = None
            if target is not None:
                direction = "≤" if card["lower_is_better"] else "≥"
                help_txt = f"Target {direction} {target}"
            badge = ""
            if card["passed"] is True:
                badge = " ✅"
            elif card["passed"] is False:
                badge = " ❌"
            digits = 3 if card["label"] == "Overall Pass Rate" else 4
            st.metric(card["label"] + badge, _fmt(card["value"], digits), help=help_txt)

    st.caption(
        f"Evaluated on {metrics.get('total_evaluations', '—')} ground-truth items. "
        "Note: the current ground-truth set is small and hand-built — treat these "
        "as directional, not production-grade accuracy."
    )

    history = dl.load_metrics_history()
    if len(history) > 1:
        st.subheader("Metric history")
        df = pd.DataFrame(history)
        keys = [k for k in ["text_avg_wer", "text_avg_cer", "table_avg_f1",
                            "overall_pass_rate"] if k in df.columns]
        fig = px.line(df, x="timestamp", y=keys, markers=True)
        fig.update_layout(legend_title_text="metric", yaxis_title="value")
        st.plotly_chart(fig, width="stretch")


# --------------------------------------------------------------------------- #
# Benchmarks
# --------------------------------------------------------------------------- #
def render_benchmarks() -> None:
    st.title("Pipeline Benchmarks")
    benchmark = dl.load_benchmark()
    if not benchmark:
        st.warning("No benchmark results found.")
        return

    info = benchmark.get("benchmark_info", {})
    sysinfo = info.get("system_info", {})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Platform", sysinfo.get("platform", "—"))
    c2.metric("CPU cores", sysinfo.get("cpu_count_logical", "—"))
    c3.metric("Total memory (GB)", sysinfo.get("total_memory_gb", "—"))
    c4.metric("Max pages/stage", info.get("max_pages_per_stage", "—"))

    rows = dl.stage_performance(benchmark)
    if rows:
        df = pd.DataFrame(rows)
        left, right = st.columns(2)
        with left:
            st.subheader("Runtime by stage (s)")
            st.plotly_chart(
                px.bar(df, x="stage", y="runtime_seconds", text="runtime_seconds"),
                width="stretch",
            )
        with right:
            st.subheader("Peak memory by stage (MB)")
            st.plotly_chart(
                px.bar(df, x="stage", y="peak_memory_mb", text="peak_memory_mb"),
                width="stretch",
            )
        st.dataframe(df, width="stretch")

    failures = dl.benchmark_failures(benchmark)
    if failures:
        st.subheader("⚠️ Recorded failures in this run")
        st.caption("Surfaced honestly from the benchmark — not hidden.")
        st.dataframe(pd.DataFrame(failures), width="stretch")


# --------------------------------------------------------------------------- #
# Cost
# --------------------------------------------------------------------------- #
def render_cost() -> None:
    st.title("Cost: Build vs Buy")
    cost = dl.load_cost_analysis()
    if not cost:
        st.warning("No cost analysis found.")
        return

    info = cost.get("analysis_info", {})
    st.caption(
        f"Based on {info.get('pages_analyzed', '—')} pages · "
        f"pricing snapshot {info.get('pricing_date', '—')}. "
        "Static public-pricing estimate; excludes engineering/maintenance cost."
    )

    be = dl.break_even(cost)
    if be:
        c1, c2, c3 = st.columns(3)
        c1.metric("Cheapest cloud (per 1k pages)", f"${be.get('cloud_cost_usd', 0):.2f}")
        c2.metric("Cheapest self-hosted", f"${be.get('cheapest_infrastructure_cost_usd', 0):.2f}")
        c3.metric("Break-even volume (pages)", f"{be.get('break_even_volume_pages', 0):,}")

    cloud = dl.cloud_cost_rows(cost)
    if cloud:
        st.subheader("Cloud service cost per processor")
        df = pd.DataFrame(cloud)
        fig = px.bar(df, x="processor", y="total_cost_usd", color="service", barmode="group")
        fig.update_layout(yaxis_title="USD per analyzed volume")
        st.plotly_chart(fig, width="stretch")

    infra = dl.infrastructure_rows(cost)
    if infra:
        st.subheader("Self-hosted infrastructure options")
        st.plotly_chart(
            px.bar(pd.DataFrame(infra), x="option", y="total_cost_usd", text="total_cost_usd"),
            width="stretch",
        )


# --------------------------------------------------------------------------- #
# Drift
# --------------------------------------------------------------------------- #
def render_drift() -> None:
    st.title("Distribution Drift")
    drift = dl.load_drift()
    if not drift:
        st.warning("No drift analysis found.")
        return
    st.caption("Distributions of extracted-text and table shapes across analyzed pages.")

    fields = [
        ("text_analysis", "word_counts", "Words per chunk"),
        ("text_analysis", "sentence_counts", "Sentences per chunk"),
        ("text_analysis", "numeric_token_ratios", "Numeric-token ratio"),
    ]
    cols = st.columns(len(fields))
    for col, (section, field, label) in zip(cols, fields):
        series = dl.drift_series(drift, section, field)
        with col:
            st.subheader(label)
            if series:
                st.plotly_chart(
                    px.histogram(pd.DataFrame({label: series}), x=label, nbins=10),
                    width="stretch",
                )
                st.caption(f"n={len(series)}")
            else:
                st.info("No data")


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
def render_reports() -> None:
    st.title("Analysis Reports")
    reports = dl.list_reports()
    if not reports:
        st.warning("No reports found.")
        return
    names = [p.stem.replace("_", " ").title() for p in reports]
    choice = st.selectbox("Report", options=list(range(len(reports))),
                          format_func=lambda i: names[i])
    st.markdown(dl.read_report(reports[choice]))


PAGES = {
    "Overview": render_overview,
    "Benchmarks": render_benchmarks,
    "Cost (Build vs Buy)": render_cost,
    "Distribution Drift": render_drift,
    "Reports": render_reports,
}
PAGES[page]()
