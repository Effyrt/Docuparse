# Docuparse
Intelligent document parser with adaptive extraction, layout detection, and automated validation for financial filings.

## 🚀 How to Reproduce the Pipeline

This repository uses **DVC (Data Version Control)** to ensure that both code and data pipelines are reproducible.  
Follow the steps below to reproduce the results from raw PDFs all the way to exported outputs.

✅ Step 1: Selection of Test Cases

Users or evaluators choose a financial report (10-K / 10-Q filing).

📑 Step 2: Parsing Extraction Results

Extracted text and tables (via pdfplumber, Camelot, OCR (Tesseract), LayoutParser, Docling, or Document AI) from the reports.

🔍 Step 3: Fallback 機制

🔄 Correct-after-steps: values mismatched but corrected after refinement.

### For Clone the repository
```bash
git clone <REPO_URL>
cd <REPO_NAME>

pip install -r requirements.txt
pip install dvc[all]

dvc pull

dvc repro

