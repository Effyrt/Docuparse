#!/usr/bin/env bash
set -euo pipefail  # stop on error, unset vars, and failed pipes

echo "🚀 Running DVC smoke test..."

# 1. Run the full pipeline. We do NOT pass --pull because no DVC remote is
#    configured (.dvc/config is empty); --pull would fail trying to reach a
#    remote that does not exist. The pipeline regenerates its outputs locally.
dvc repro --force || { echo "❌ DVC pipeline failed"; exit 1; }

# 2. Validate the pipeline produced Docling output. The docling stage writes to
#    data/parsed/docling/<stem>_docling.json (see dvc.yaml: extract_docling).
ls data/parsed/docling/*_docling.json >/dev/null 2>&1 || {
    echo "❌ No parsed Docling outputs found in data/parsed/docling/"
    exit 1
}

echo "✅ Smoke test passed"
