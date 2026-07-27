"""Static consistency checks that guard against regressions of fixed bugs.

None of these import the heavy extraction stack, so they run anywhere. They act
as executable documentation of the invariants the pipeline relies on:

  * no machine-specific absolute paths committed to source;
  * the smoke test validates the path the pipeline actually writes;
  * the DVC download stage declares the directories the extractors read;
  * no deprecated ``datetime.utcnow()`` calls.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"


def _python_sources():
    return list(SRC.rglob("*.py"))


def test_no_hardcoded_absolute_user_paths():
    offenders = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        if "/Users/" in text or "C:\\Users\\" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"Hardcoded absolute user paths found in: {offenders}"


def test_no_deprecated_utcnow():
    offenders = []
    for path in _python_sources():
        if "datetime.utcnow(" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"Deprecated datetime.utcnow() found in: {offenders}"


def test_smoke_test_checks_real_docling_output_path():
    smoke = (REPO_ROOT / "tests" / "smoke.sh").read_text(encoding="utf-8")
    # The pipeline writes to data/parsed/docling/, not docling_or_fallback/.
    assert "data/parsed/docling/" in smoke
    assert "docling_or_fallback" not in smoke


def test_smoke_test_does_not_pull_from_missing_remote():
    smoke = (REPO_ROOT / "tests" / "smoke.sh").read_text(encoding="utf-8")
    # Only inspect actual dvc invocations, not explanatory comments.
    dvc_commands = [
        line for line in smoke.splitlines()
        if line.strip().startswith("dvc ")
    ]
    assert dvc_commands, "smoke test should still invoke dvc"
    assert all("--pull" not in cmd for cmd in dvc_commands), (
        "No DVC remote is configured; dvc --pull would fail"
    )


def test_dvc_download_outs_match_extractor_inputs():
    dvc = yaml.safe_load((REPO_ROOT / "dvc.yaml").read_text(encoding="utf-8"))
    outs = dvc["stages"]["download"]["outs"]
    # Extractors read from data/raw/10-K/ and data/raw/10-Q/; the download stage
    # must declare those as its outputs.
    assert "data/raw/10-K/" in outs
    assert "data/raw/10-Q/" in outs


def test_docling_stage_output_matches_smoke_check():
    dvc = yaml.safe_load((REPO_ROOT / "dvc.yaml").read_text(encoding="utf-8"))
    docling_outs = dvc["stages"]["extract_docling"]["outs"]
    assert "data/parsed/docling/" in docling_outs
