#!/usr/bin/env python3
"""
Project LANTERN Production Pipeline - HTML/PDF Support
"""

import sys
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import traceback

# Add src to path
sys.path.append('src')

# Import all components
from parsers.simple_docling_parser import SimpleDoclingParser
from extractors.simple_text_extractor import SimpleTextExtractor
from extractors.table_extractor import SimpleTableExtractor
from extractors.layout_parser import SimpleLayoutParser
from downloaders.sec_downloader import SECDownloader

# Try importing XBRL validator
try:
    from validators.xbrl_validator import XBRLValidator
    XBRL_AVAILABLE = True
except ImportError:
    XBRL_AVAILABLE = False
    print("Warning: XBRL validator not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PipelineConfig:
    """Pipeline configuration"""
    output_dir: Path = Path("data/pipeline_output")
    enable_layout_detection: bool = True
    enable_xbrl_validation: bool = True and XBRL_AVAILABLE
    filing_limit: int = 1
    convert_html_to_text: bool = True  # New option

@dataclass
class PipelineState:
    """Pipeline execution state"""
    ticker: str
    status: str = "PENDING"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    downloaded_files: List[str] = None
    parsed_files: List[str] = None
    extracted_data: Dict = None
    validation_results: Dict = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.downloaded_files is None:
            self.downloaded_files = []
        if self.parsed_files is None:
            self.parsed_files = []
        if self.extracted_data is None:
            self.extracted_data = {}
        if self.validation_results is None:
            self.validation_results = {}
        if self.errors is None:
            self.errors = []
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data

class LanternPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize pipeline with configuration"""
        
        self.config = config or PipelineConfig()
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Initializing pipeline components...")
        
        # Initialize components WITHOUT output_dir parameter
        self.downloader = SECDownloader(
            output_dir=str(self.config.output_dir / "raw")
        )
        
        # These likely don't take output_dir parameter
        self.parser = SimpleDoclingParser()
        self.text_extractor = SimpleTextExtractor()
        self.table_extractor = SimpleTableExtractor()
        
        if self.config.enable_layout_detection:
            self.layout_detector = SimpleLayoutParser()
        
        if self.config.enable_xbrl_validation and XBRL_AVAILABLE:
            self.xbrl_validator = XBRLValidator(
                output_dir=str(self.config.output_dir / "validation")
            )
        
        logger.info("✅ All components initialized")
    
    def _extract_text_from_html(self, html_path: str) -> str:
        """Extract text from HTML file"""
        from bs4 import BeautifulSoup
        
        with open(html_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def run(self, ticker: str, filing_type: str = "10-K",
            year: Optional[int] = None) -> Dict:
        """Run complete pipeline for a ticker"""
        
        state = PipelineState(ticker=ticker)
        state.status = "RUNNING"
        state.start_time = datetime.now()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 STARTING PIPELINE FOR {ticker}")
        logger.info(f"Filing Type: {filing_type} | Year: {year or 'latest'}")
        logger.info(f"{'='*60}")
        
        try:
            # Step 1: Download SEC filings
            self._step_download(state, ticker, filing_type, year)
            
            # Step 2: Parse documents
            self._step_parse(state)
            
            # Step 3: Extract text (handles both PDF and HTML)
            self._step_extract_text(state)
            
            # Step 4: Layout detection (PDF only)
            if self.config.enable_layout_detection:
                self._step_layout_detection(state)
            
            # Step 5: Extract tables
            self._step_extract_tables(state)
            
            # Step 6: XBRL validation (optional)
            if self.config.enable_xbrl_validation and XBRL_AVAILABLE:
                self._step_validate(state, ticker, filing_type, year)
            
            # Generate final report
            self._generate_report(state)
            
            state.status = "SUCCESS"
            state.end_time = datetime.now()
            
            duration = (state.end_time - state.start_time).total_seconds()
            logger.info(f"\n✅ PIPELINE COMPLETED in {duration:.2f} seconds")
            
        except Exception as e:
            state.status = "FAILED"
            state.errors.append(str(e))
            state.end_time = datetime.now()
            
            logger.error(f"Pipeline failed: {e}")
            logger.debug(traceback.format_exc())
            
            self._generate_error_report(state)
        
        return state.to_dict()
    
    def _step_download(self, state: PipelineState, ticker: str,
                      filing_type: str, year: Optional[int]):
        """Step 1: Download SEC filings"""
        
        logger.info("\n📥 Step 1: Downloading SEC filings...")
        
        try:
            after_date = f"{year}-01-01" if year else None
            before_date = f"{year}-12-31" if year else None
            
            filings = self.downloader.download_filing(
                ticker,
                filing_type,
                limit=self.config.filing_limit,
                after_date=after_date,
                before_date=before_date
            )
            
            if not filings:
                raise ValueError(f"No {filing_type} filings found for {ticker}")
            
            state.downloaded_files = [f.local_path for f in filings if f.local_path]
            
            logger.info(f"  ✅ Downloaded {len(state.downloaded_files)} filing(s)")
            
            for filing in filings:
                logger.info(f"    - {filing.filing_date}: {Path(filing.local_path).name}")
        
        except Exception as e:
            logger.error(f"  ❌ Download failed: {e}")
            raise
    
    def _step_parse(self, state: PipelineState):
        """Step 2: Parse documents"""
        
        logger.info("\n📄 Step 2: Parsing documents...")
        
        try:
            for file_path in state.downloaded_files:
                if file_path.endswith('.html'):
                    # For HTML files, extract text and save as parsed data
                    text = self._extract_text_from_html(file_path)
                    
                    output_path = self.config.output_dir / "parsed" / Path(file_path).name.replace('.html', '_parsed.json')
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    parsed_data = {
                        'source': file_path,
                        'type': 'html',
                        'text': text[:5000],  # First 5000 chars for preview
                        'full_text_length': len(text)
                    }
                    
                    with open(output_path, 'w') as f:
                        json.dump(parsed_data, f, indent=2)
                    
                    state.parsed_files.append(str(output_path))
                    logger.info(f"  ✅ Parsed HTML: {Path(file_path).name}")
                    
                elif file_path.endswith('.pdf'):
                    # PDF parsing
                    output_path = self.config.output_dir / "parsed" / Path(file_path).name.replace('.pdf', '_parsed.json')
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    parsed_data = self.parser.parse(file_path)
                    
                    if parsed_data:
                        with open(output_path, 'w') as f:
                            json.dump(parsed_data, f, indent=2)
                        state.parsed_files.append(str(output_path))
                        logger.info(f"  ✅ Parsed PDF: {Path(file_path).name}")
                else:
                    logger.warning(f"  ⚠️  Unknown file type: {Path(file_path).name}")
        
        except Exception as e:
            logger.error(f"  ❌ Parsing failed: {e}")
            state.errors.append(f"Parsing: {e}")
    
    def _step_extract_text(self, state: PipelineState):
        """Step 3: Extract text from both PDF and HTML"""
        
        logger.info("\n📝 Step 3: Extracting text...")
        
        try:
            all_texts = []
            
            for file_path in state.downloaded_files:
                if file_path.endswith('.pdf'):
                    text_data = self.text_extractor.extract(Path(file_path))
                    if text_data:
                        all_texts.append(text_data)
                        logger.info(f"  ✅ Extracted text from PDF: {Path(file_path).name}")
                        
                elif file_path.endswith('.html'):
                    text = self._extract_text_from_html(file_path)
                    text_data = {
                        'source': file_path,
                        'text': text,
                        'length': len(text)
                    }
                    all_texts.append(text_data)
                    logger.info(f"  ✅ Extracted text from HTML: {Path(file_path).name} ({len(text)} chars)")
            
            state.extracted_data['texts'] = all_texts
        
        except Exception as e:
            logger.error(f"  ❌ Text extraction failed: {e}")
            state.errors.append(f"Text extraction: {e}")
    
    def _step_layout_detection(self, state: PipelineState):
        """Step 4: Layout detection (PDF only)"""
        
        logger.info("\n🔍 Step 4: Detecting layout...")
        
        try:
            layout_results = {}
            pdf_count = 0
            
            for file_path in state.downloaded_files:
                if file_path.endswith('.pdf'):
                    results = self.layout_detector.parse(Path(file_path))
                    layout_results[file_path] = results
                    logger.info(f"  ✅ Detected layout for {Path(file_path).name}")
                    pdf_count += 1
            
            if pdf_count == 0:
                logger.info("  ℹ️  No PDF files to process for layout detection")
            
            state.extracted_data['layout'] = layout_results
        
        except Exception as e:
            logger.error(f"  ❌ Layout detection failed: {e}")
            state.errors.append(f"Layout detection: {e}")
    
    def _step_extract_tables(self, state: PipelineState):
        """Step 5: Extract tables"""
        
        logger.info("\n📊 Step 5: Extracting tables...")
        
        try:
            all_tables = []
            
            for file_path in state.downloaded_files:
                if file_path.endswith('.pdf'):
                    tables = self.table_extractor.extract(Path(file_path))
                    if tables:
                        all_tables.extend(tables)
                        logger.info(f"  ✅ Extracted {len(tables)} tables from PDF")
                elif file_path.endswith('.html'):
                    # Extract tables from HTML
                    from bs4 import BeautifulSoup
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f.read(), 'html.parser')
                    
                    html_tables = soup.find_all('table')
                    if html_tables:
                        logger.info(f"  ✅ Found {len(html_tables)} tables in HTML")
                        for i, table in enumerate(html_tables[:10]):  # Limit to first 10 tables
                            # Extract table text
                            table_data = []
                            for row in table.find_all('tr'):
                                row_data = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                                table_data.append(row_data)
                            all_tables.append({'source': file_path, 'table_index': i, 'data': table_data})
            
            state.extracted_data['tables'] = all_tables
            logger.info(f"  ✅ Total tables extracted: {len(all_tables)}")
        
        except Exception as e:
            logger.error(f"  ❌ Table extraction failed: {e}")
            state.errors.append(f"Table extraction: {e}")
    
    def _step_validate(self, state: PipelineState, ticker: str,
                      filing_type: str, year: Optional[int]):
        """Step 6: XBRL validation"""
        
        logger.info("\n✔️  Step 6: Validating with XBRL...")
        
        try:
            xbrl_year = year or datetime.now().year - 1
            xbrl_path = self.xbrl_validator.fetch_xbrl(
                ticker, filing_type, xbrl_year
            )
            
            if not xbrl_path:
                logger.warning("  ⚠️  XBRL not available for validation")
                return
            
            if state.parsed_files:
                results = self.xbrl_validator.validate_extraction(
                    state.parsed_files[0], xbrl_path
                )
                
                state.validation_results = results
                
                summary = results.get('summary', {})
                score = summary.get('validation_score', 0)
                
                logger.info(f"  ✅ Validation score: {score:.1f}%")
        
        except Exception as e:
            logger.error(f"  ❌ Validation failed: {e}")
            state.errors.append(f"XBRL validation: {e}")
    
    def _generate_report(self, state: PipelineState):
        """Generate pipeline report"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'ticker': state.ticker,
            'status': state.status,
            'summary': {
                'files_downloaded': len(state.downloaded_files),
                'files_parsed': len(state.parsed_files),
                'text_extracted': len(state.extracted_data.get('texts', [])),
                'tables_extracted': len(state.extracted_data.get('tables', [])),
            },
            'errors': state.errors
        }
        
        if state.validation_results:
            report['validation'] = state.validation_results.get('summary', {})
        
        report_path = self.config.output_dir / f"report_{state.ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self._print_summary(report)
        
        logger.info(f"\n📁 Report saved: {report_path}")
    
    def _generate_error_report(self, state: PipelineState):
        """Generate error report"""
        
        error_report = {
            'timestamp': datetime.now().isoformat(),
            'ticker': state.ticker,
            'status': 'FAILED',
            'errors': state.errors,
            'partial_results': {
                'downloaded': len(state.downloaded_files),
                'parsed': len(state.parsed_files)
            }
        }
        
        error_path = self.config.output_dir / f"error_{state.ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(error_path, 'w') as f:
            json.dump(error_report, f, indent=2)
        
        logger.error(f"Error report saved: {error_path}")
    
    def _print_summary(self, report: Dict):
        """Print report summary"""
        
        print("\n" + "="*60)
        print("📋 PIPELINE SUMMARY")
        print("="*60)
        
        summary = report.get('summary', {})
        
        print(f"Ticker: {report.get('ticker')}")
        print(f"Status: {report.get('status')}")
        print(f"\nProcessing Results:")
        print(f"  Files Downloaded: {summary.get('files_downloaded', 0)}")
        print(f"  Files Parsed: {summary.get('files_parsed', 0)}")
        print(f"  Text Extracted: {summary.get('text_extracted', 0)} documents")
        print(f"  Tables Extracted: {summary.get('tables_extracted', 0)}")
        
        if report.get('errors'):
            print(f"\nErrors encountered:")
            for error in report['errors']:
                print(f"  - {error}")

def main():
    """Main entry point for the pipeline"""
    
    parser = argparse.ArgumentParser(
        description="Project LANTERN - SEC Filing Analysis Pipeline"
    )
    
    parser.add_argument(
        'ticker',
        help='Stock ticker symbol (e.g., AAPL, META, GOOGL)'
    )
    
    parser.add_argument(
        '--filing-type',
        default='10-K',
        choices=['10-K', '10-Q', '8-K'],
        help='Type of SEC filing to process'
    )
    
    parser.add_argument(
        '--year',
        type=int,
        help='Specific year for filing'
    )
    
    parser.add_argument(
        '--output',
        default='data/pipeline_output',
        help='Output directory'
    )
    
    parser.add_argument(
        '--no-validation',
        action='store_true',
        help='Skip XBRL validation'
    )
    
    parser.add_argument(
        '--no-layout',
        action='store_true',
        help='Skip layout detection'
    )
    
    args = parser.parse_args()
    
    config = PipelineConfig(
        output_dir=Path(args.output),
        enable_xbrl_validation=not args.no_validation and XBRL_AVAILABLE,
        enable_layout_detection=not args.no_layout
    )
    
    pipeline = LanternPipeline(config)
    
    try:
        result = pipeline.run(
            args.ticker,
            args.filing_type,
            args.year
        )
        
        if result.get('status') == 'SUCCESS':
            print("\n✅ Pipeline completed successfully!")
            return 0
        else:
            print("\n⚠️  Pipeline completed with errors")
            return 1
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())