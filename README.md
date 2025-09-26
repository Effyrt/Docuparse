# PROJECT LANTERN - AI-Powered PDF Parsing System

## Attestation
WE ATTEST THAT WE HAVEN'T USED ANY OTHER STUDENTS' WORK IN OUR ASSIGNMENT AND ABIDE BY THE POLICIES LISTED IN THE STUDENT HANDBOOK

**Contributions:**
- Member 1 (Om Raut): 33.3%
- Member 2 (Rayudu Hemanth): 33.3%
- Member 3: 33.3%

## Demo Video
[10-minute demo video link]

## Project Structure
- `src/` - Source code for all components
- `data/raw/` - Downloaded SEC filings
- `data/parsed/` - Extracted and processed data
- `reports/` - Metrics and benchmarks

## Setup & Running
1. Install dependencies: `pip install -r requirements.txt`
2. Run pipeline: `python run_pipeline.py`
3. Or specific company: `python run_pipeline.py --batch AAPL`

## Components Implemented
1. **SEC Downloader** - Downloads filings from EDGAR
2. **Text Extraction** - pdfplumber with OCR fallback
3. **Table Extraction** - Camelot (lattice/stream modes)
4. **Layout Detection** - LayoutParser
5. **Docling Parser** - Advanced PDF understanding
6. **XBRL Validation** - Cross-validates extracted data
7. **Metrics & Benchmarking** - Performance evaluation

## DVC Pipeline
Run `dvc repro` to execute the complete pipeline