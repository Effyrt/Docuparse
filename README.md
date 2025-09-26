# Docuparse
Intelligent document parser with adaptive extraction, layout detection, and automated validation for financial filings.

## 🚀 How to Reproduce the Pipeline

This repository uses **DVC (Data Version Control)** to ensure that both code and data pipelines are reproducible.  
Follow the steps below to reproduce the results from raw PDFs all the way to exported outputs.

## Setup and Reproduction Steps

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Docuparse
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Selection of Test Cases

Users or evaluators choose a financial report (10-K / 10-Q filing).

### 5. Parsing Extraction Results

Extracted text and tables (via pdfplumber, Camelot, OCR (Tesseract), LayoutParser, Docling, or Document AI) from the reports.

🔍 Fallback 機制

🔄 Correct-after-steps: values mismatched but corrected after refinement.

### For Clone the repository
```bash
git clone <REPO_URL>
cd <REPO_NAME>

pip install -r requirements.txt
pip install dvc[all]

dvc pull

dvc repro

```
### Project Structure

Docuparse/
├── data/
│   ├── raw/             # Raw SEC filings 
│   └── parsed/          # Processed and extracted outputs
│
├── src/                 # Source code modules
│   ├── parsers/         # Parsing scripts 
│   └── representations/ # Data representation, formatting, and export utilities
│
├── notebooks/           # Jupyter notebooks for experiments & exploration
├── tests/               # Unit and regression tests
├── reports/             # Evaluation reports, benchmark results, visualizations
│
├── requirements.txt     # Python dependencies
├── dvc.yaml             # DVC pipeline definition 
├── dvc.lock             # DVC pipeline lock file 
└── README.md            # Project documentation
 
```


