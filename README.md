# Docuparse
Intelligent document parser with adaptive extraction, layout detection, and automated validation for financial filings.

## 🚀 How to Reproduce the Pipeline

This repository uses **DVC (Data Version Control)** to ensure that both code and data pipelines are reproducible.  
Follow the steps below to reproduce the results from raw PDFs all the way to exported outputs.

### 1. Clone the repository
```bash
git clone <REPO_URL>
cd <REPO_NAME>

pip install -r requirements.txt
pip install dvc[all]

dvc pull

dvc repro

