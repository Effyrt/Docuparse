# DocuParse

**Intelligent document parser for financial filings** - Extracts text, tables, and validates data from SEC 10-K/10-Q documents using multiple AI models and cross-verification.

## What This Does

DocuParse is a complete pipeline that:
- 📄 **Downloads** SEC filings (10-K, 10-Q) automatically
- 🔍 **Extracts** text using OCR + native PDF parsing
- 📊 **Finds tables** using multiple detection methods
- 🏗️ **Detects layout** with dual AI models (Detectron2 + LayoutLMv3)
- 🤖 **Processes with Docling** (IBM's document AI)
- ✅ **Validates data** against official XBRL filings
- 📈 **Benchmarks performance** and estimates costs

## 🎥 Demo Video

Watch the complete pipeline in action: [**DocuParse Pipeline Demo**](https://drive.google.com/file/d/1w8RPBch1nPV8BpZIw0tFLPD1BmK0rkfN/view?usp=sharing)

## 📚 Interactive Tutorial

Follow the complete implementation guide: [**DocuParse CodeLabs**](https://codelabs-preview.appspot.com/?file_id=1eoeyKHeNX_qYq6m8oL37XLQMEoLCK7Xv02sBSGAGbwg#0)

## Quick Start

```bash
# 1. Setup
git clone <repository-url>
cd DocuParse
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Run the complete pipeline
dvc repro

# 3. Check results
ls data/exports/
```

## Project Structure

```
DocuParse/
├── 📁 src/                    # Source code
│   ├── extractors/           # Text, table, layout extraction
│   ├── downloaders/          # SEC filing downloads
│   ├── validation/           # XBRL cross-verification
│   └── benchmarking/         # Performance measurement
│
├── 📁 data/                   # Data files (DVC managed)
│   ├── raw/                  # Downloaded PDFs
│   ├── parsed/               # Extracted data
│   └── exports/              # Final outputs
│
├── 📁 reports/               # Analysis & findings
├── 📁 evaluation/            # Quality metrics & testing
├── 📁 notebooks/             # Development & demos
│
├── ⚙️ dvc.yaml               # Pipeline configuration
├── ⚙️ params.yaml            # Parameters
└── 📄 requirements.txt       # Dependencies
```

## Key Features

### 🔧 **Extraction Pipeline**
- **Text Extraction**: Native PDF parsing + OCR fallback
- **Table Detection**: Camelot + pdfplumber hybrid approach
- **Layout Analysis**: Detectron2 + LayoutLMv3 dual models
- **Docling Integration**: IBM's enterprise document AI

### ✅ **Quality Assurance**
- **XBRL Validation**: Cross-check against authoritative financial data
- **Accuracy Metrics**: Word Error Rate, table precision/recall
- **Regression Testing**: Automated quality threshold validation
- **Distribution Monitoring**: Detect data drift and anomalies

### 📊 **Performance Analysis**
- **Real Benchmarks**: Actual runtime and memory measurements
- **Cost Estimation**: Cloud API pricing vs open-source infrastructure
- **Bottleneck Analysis**: Identify slowest pipeline stages
- **Scaling Recommendations**: Hardware and concurrency guidance

### 🏢 **Build vs Buy Analysis**
Comprehensive comparison against major cloud document AI services:
- **Google Document AI**: $1.50-$50 per 1,000 pages
- **AWS Textract**: $1.50-$50 per 1,000 pages  
- **Azure Form Recognizer**: $10-$50 per 1,000 pages
- **Our Solution**: $1.05 per 1,000 pages (**30-98% cost savings**)

**Additional Benefits**: Complete data privacy, no API rate limits, custom financial document optimization

## Pipeline Stages

1. **Download** → SEC filings from EDGAR
2. **Text** → Extract text with OCR fallback
3. **Tables** → Detect and extract financial tables
4. **Layout** → Identify document structure
5. **Docling** → AI-powered document understanding
6. **Export** → Consolidate results in multiple formats

## Results

The pipeline processes **676 pages in ~3 minutes** with:
- ✅ **99.56%** native text extraction (minimal OCR needed)
- ✅ **187 tables** extracted from financial statements
- ✅ **2,954 XBRL concepts** validated against authoritative data
- ✅ **Multiple formats**: JSON, Markdown, CSV outputs

## Key Reports

- `reports/benchmarks.md` - Performance analysis and cost estimates
- `reports/text_analysis.md` - Text extraction deep dive
- `reports/docling_vs_custom_comparison.md` - AI vs traditional methods
- `reports/xbrl_cross_verification_report.md` - Financial data validation
- `benchmarks/results/cost_analysis_20250926_135135.json` - Cloud API cost comparison

## Configuration

Edit `params.yaml` to customize:
- Companies and filing years to process
- OCR and extraction thresholds
- Layout detection parameters
- Export formats and options

## Dependencies

- **Python 3.9+** with DVC for pipeline management
- **Computer Vision**: Detectron2, LayoutLMv3 for layout detection
- **Document AI**: Docling, pdfplumber, Camelot for extraction
- **Validation**: SEC EDGAR API, XBRL parsing libraries

## 👥 Team Contributions

This project was developed by a collaborative team with the following contributions:

- **Hemanth Rayudu** - 45%
- **Peiying Chen** - 45%  
- **Om Sailesh Raut** - 10%

---

**Built for**: Financial document analysis, regulatory compliance, and automated data extraction from SEC filings.