set -e  # when error then stop

echo "🚀 Running DVC smoke test..."

# 1. run pipeline
dvc repro --pull --force || { echo "❌ DVC pipeline failed"; exit 1; }

# 2. validate pipeline (at least one *_docling.json exist)
ls data/parsed/docling_or_fallback/*_docling.json >/dev/null 2>&1 || { echo "❌ No parsed outputs found"; exit 1; }

echo "✅ Smoke test passed"
