# src/extractors/text_extractor.py

import pdfplumber
import pytesseract
from PIL import Image
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import json
from datetime import datetime, timezone
import numpy as np
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PageExtraction:
    """Data class for page extraction results"""
    page_num: int
    text: str
    ocr_used: bool
    word_count: int
    char_count: int
    words: List[Dict]
    extraction_time: float
    error: Optional[str] = None

class TextExtractor:
    """
    Extract text from PDF files with OCR fallback for scanned pages.
    Implements Part 1 of the pipeline.
    """
    
    def __init__(
        self, 
        ocr_threshold: float = 50,  # Minimum chars to consider page has text
        ocr_resolution: int = 300,
        save_word_boxes: bool = True,
        output_dir: Optional[Path] = None,
        max_pages: int = None
    ):
        """
        Initialize the text extractor.
        
        Args:
            ocr_threshold: Minimum character count to skip OCR
            ocr_resolution: DPI for OCR conversion
            save_word_boxes: Whether to extract and save word bounding boxes
            output_dir: Directory to save extracted text
        """
        self.ocr_threshold = ocr_threshold
        self.ocr_resolution = ocr_resolution
        self.save_word_boxes = save_word_boxes
        self.output_dir = Path(output_dir) if output_dir else Path("data/parsed/text")
        self.max_pages = max_pages
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Track statistics
        self.stats = {
            'total_pages': 0,
            'ocr_pages': 0,
            'failed_pages': 0,
            'total_time': 0
        }
    
    def extract_page(self, page, page_num: int) -> PageExtraction:
        """
        Extract text from a single page with OCR fallback.
        
        Args:
            page: pdfplumber page object
            page_num: Page number
            
        Returns:
            PageExtraction object with results
        """
        import time
        start_time = time.time()
        
        try:
            # Try standard text extraction first
            text = page.extract_text() or ""
            words = []
            
            # Check if we need OCR
            if len(text.strip()) < self.ocr_threshold:
                logger.info(f"Page {page_num}: Text too short ({len(text)} chars), using OCR")
                text = self._extract_with_ocr(page)
                ocr_used = True
            else:
                ocr_used = False
                # Extract word bounding boxes if requested
                if self.save_word_boxes:
                    words = page.extract_words() or []
            
            extraction_time = time.time() - start_time
            
            return PageExtraction(
                page_num=page_num,
                text=text,
                ocr_used=ocr_used,
                word_count=len(text.split()),
                char_count=len(text),
                words=words,
                extraction_time=extraction_time
            )
            
        except Exception as e:
            logger.error(f"Error extracting page {page_num}: {str(e)}")
            return PageExtraction(
                page_num=page_num,
                text="",
                ocr_used=False,
                word_count=0,
                char_count=0,
                words=[],
                extraction_time=time.time() - start_time,
                error=str(e)
            )
    
    def _extract_with_ocr(self, page) -> str:
        """
        Extract text using OCR (Tesseract).
        
        Args:
            page: pdfplumber page object
            
        Returns:
            Extracted text string
        """
        try:
            # Convert page to image
            pil_image = page.to_image(resolution=self.ocr_resolution).original
            
            # Apply OCR
            text = pytesseract.image_to_string(
                pil_image,
                config='--oem 3 --psm 3'  # Use LSTM OCR engine with automatic page segmentation
            )
            
            return text
            
        except Exception as e:
            logger.error(f"OCR failed: {str(e)}")
            return ""
    
    def process_pdf(
        self, 
        pdf_path: Path, 
        page_range: Optional[Tuple[int, int]] = None,
        save_individual_pages: bool = True
    ) -> Dict:
        """
        Process entire PDF document.
        
        Args:
            pdf_path: Path to PDF file
            page_range: Optional tuple of (start_page, end_page)
            save_individual_pages: Save each page as separate text file
            
        Returns:
            Dictionary with extraction results and statistics
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        logger.info(f"Processing PDF: {pdf_path.name}")
        
        results = []
        doc_id = pdf_path.stem
        
        with pdfplumber.open(pdf_path) as pdf:
            # Determine pages to process
            if page_range:
                start, end = page_range
                pages_to_process = range(start - 1, min(end, len(pdf.pages)))
            else:
                # Use max_pages if specified, otherwise process all pages
                if self.max_pages:
                    pages_to_process = range(min(self.max_pages, len(pdf.pages)))
                    logger.info(f"🔧 Limiting processing to first {self.max_pages} pages")
                else:
                    pages_to_process = range(len(pdf.pages))
            
            # Process each page
            for i in pages_to_process:
                page_num = i + 1
                logger.info(f"Processing page {page_num}/{len(pdf.pages)}")
                
                page_result = self.extract_page(pdf.pages[i], page_num)
                results.append(page_result)
                
                # Update statistics
                self.stats['total_pages'] += 1
                if page_result.ocr_used:
                    self.stats['ocr_pages'] += 1
                if page_result.error:
                    self.stats['failed_pages'] += 1
                self.stats['total_time'] += page_result.extraction_time
                
                # Save individual page if requested
                if save_individual_pages and page_result.text:
                    self._save_page_text(doc_id, page_num, page_result)
        
        # Save extraction log
        self._save_extraction_log(doc_id, results)
        
        # Compile full document text
        full_text = "\n\n".join([r.text for r in results if r.text])
        
        # Save full document
        full_doc_path = self.output_dir / f"{doc_id}_full.txt"
        full_doc_path.write_text(full_text, encoding='utf-8')
        
        return {
            'doc_id': doc_id,
            'pdf_path': str(pdf_path),
            'total_pages': len(results),
            'pages_extracted': results,
            'statistics': self.stats.copy(),
            'output_dir': str(self.output_dir),
            'full_text_path': str(full_doc_path)
        }
    
    def _save_page_text(self, doc_id: str, page_num: int, page_result: PageExtraction):
        """Save individual page text and metadata."""
        # Save text
        text_path = self.output_dir / f"{doc_id}_page_{page_num:04d}.txt"
        text_path.write_text(page_result.text, encoding='utf-8')
        
        # Save metadata
        meta_path = self.output_dir / f"{doc_id}_page_{page_num:04d}_meta.json"
        metadata = {
            'page_num': page_result.page_num,
            'ocr_used': page_result.ocr_used,
            'word_count': page_result.word_count,
            'char_count': page_result.char_count,
            'extraction_time': page_result.extraction_time,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': page_result.error
        }
        
        # Save word bounding boxes if available
        if page_result.words:
            metadata['word_boxes'] = page_result.words[:100]  # Save first 100 for reference
            
            # Save complete word boxes separately
            words_path = self.output_dir / f"{doc_id}_page_{page_num:04d}_words.json"
            with open(words_path, 'w', encoding='utf-8') as f:
                json.dump(page_result.words, f, indent=2)
        
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    def _save_extraction_log(self, doc_id: str, results: List[PageExtraction]):
        """Save extraction log with OCR usage and statistics."""
        log_path = self.output_dir / f"{doc_id}_extraction_log.json"
        
        log_data = {
            'doc_id': doc_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_pages': len(results),
            'ocr_pages': [r.page_num for r in results if r.ocr_used],
            'failed_pages': [r.page_num for r in results if r.error],
            'statistics': {
                'total_extraction_time': sum(r.extraction_time for r in results),
                'avg_extraction_time': np.mean([r.extraction_time for r in results]),
                'total_words': sum(r.word_count for r in results),
                'total_chars': sum(r.char_count for r in results),
                'ocr_percentage': (sum(1 for r in results if r.ocr_used) / len(results) * 100) if results else 0
            },
            'page_details': [
                {
                    'page': r.page_num,
                    'ocr': r.ocr_used,
                    'words': r.word_count,
                    'chars': r.char_count,
                    'time': r.extraction_time,
                    'error': r.error
                }
                for r in results
            ]
        }
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"Extraction log saved to {log_path}")
    
    def get_statistics(self) -> Dict:
        """Get extraction statistics."""
        return {
            **self.stats,
            'ocr_percentage': (self.stats['ocr_pages'] / self.stats['total_pages'] * 100) 
                if self.stats['total_pages'] > 0 else 0,
            'avg_time_per_page': self.stats['total_time'] / self.stats['total_pages']
                if self.stats['total_pages'] > 0 else 0
        }
    
    def reset_statistics(self):
        """Reset extraction statistics."""
        self.stats = {
            'total_pages': 0,
            'ocr_pages': 0,
            'failed_pages': 0,
            'total_time': 0
        }


def create_structured_output(
    doc_type: str,
    year: str,
    quarter: str = None,
    company: str = "META",
    base_output_dir: Path = Path("data/parsed/text")
) -> Dict[str, Path]:
    """
    Create structured directory layout for document output.
    
    Args:
        doc_type: Document type (10-K, 10-Q)
        year: Year of the document
        quarter: Quarter for 10-Q documents
        company: Company name (default: META)
        base_output_dir: Base output directory
        
    Returns:
        Dictionary with path mappings for different output types
    """
    # Create base paths
    if quarter:
        doc_folder = f"{company}_{year}_Q{quarter}"
    else:
        doc_folder = f"{company}_{year}"
    
    doc_type_dir = base_output_dir / doc_type
    company_dir = doc_type_dir / doc_folder
    
    # Create subdirectories
    pages_dir = company_dir / "pages"
    
    # Create directories
    for directory in [doc_type_dir, company_dir, pages_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    return {
        'metadata': company_dir / "metadata.json",
        'full_document_txt': company_dir / "full_document.txt",
        'full_document_md': company_dir / "full_document.md",
        'pages_dir': pages_dir,
        'company_dir': company_dir
    }


def process_multiple_pdfs(
    raw_data_dir: Path = Path("data/raw"),
    output_dir: Path = Path("data/parsed/text"),
    ocr_threshold: float = 50,
    ocr_resolution: int = 300,
    max_pages: int = None
) -> Dict:
    """
    Process all PDF files in the raw data directory structure.
    
    Args:
        raw_data_dir: Directory containing PDF files organized by type
        output_dir: Base directory to save structured output
        ocr_threshold: Minimum character count to skip OCR
        ocr_resolution: DPI for OCR conversion
        
    Returns:
        Dictionary with processing results for all files
    """
    
    all_results = {}
    total_stats = {
        'total_files': 0,
        'successful_files': 0,
        'failed_files': 0,
        'total_pages': 0,
        'total_ocr_pages': 0,
        'total_processing_time': 0
    }
    
    def process_single_pdf(pdf_file: Path, doc_type: str, year: str, quarter: str = None) -> Dict:
        """Process a single PDF file with structured output."""
        try:
            # Create structured directory layout
            paths = create_structured_output(
                doc_type=doc_type,
                year=year,
                quarter=quarter,
                company="META",
                base_output_dir=output_dir
            )
            
            # Initialize extractor with structured output
            extractor = TextExtractor(
                ocr_threshold=ocr_threshold,
                ocr_resolution=ocr_resolution,
                save_word_boxes=True,
                output_dir=paths['pages_dir'],  # Save individual pages in pages directory
                max_pages=max_pages
            )
            
            # Process PDF
            results = extractor.process_pdf(
                pdf_file,
                page_range=None,
                save_individual_pages=True
            )
            
            # Save full document as text
            full_text = "\n\n".join([r.text for r in results['pages_extracted'] if r.text])
            paths['full_document_txt'].write_text(full_text, encoding='utf-8')
            
            # Create markdown version
            markdown_content = f"# {doc_type} - META {year}"
            if quarter:
                markdown_content += f" Q{quarter}"
            markdown_content += f"\n\n**Source:** {pdf_file.name}\n\n"
            markdown_content += f"**Total Pages:** {results['statistics']['total_pages']}\n"
            markdown_content += f"**OCR Pages:** {results['statistics']['ocr_pages']}\n"
            markdown_content += f"**Processing Time:** {results['statistics']['total_time']:.2f}s\n\n"
            markdown_content += "---\n\n"
            markdown_content += full_text
            
            paths['full_document_md'].write_text(markdown_content, encoding='utf-8')
            
            # Create comprehensive metadata
            metadata = {
                'document_info': {
                    'type': doc_type,
                    'year': year,
                    'quarter': quarter,
                    'company': 'META',
                    'source_file': pdf_file.name,
                    'processed_at': datetime.now(timezone.utc).isoformat()
                },
                'extraction_stats': results['statistics'],
                'file_paths': {
                    'full_document_txt': str(paths['full_document_txt']),
                    'full_document_md': str(paths['full_document_md']),
                    'pages_directory': str(paths['pages_dir'])
                },
                'page_details': [
                    {
                        'page_num': r.page_num,
                        'ocr_used': r.ocr_used,
                        'word_count': r.word_count,
                        'char_count': r.char_count,
                        'extraction_time': r.extraction_time,
                        'error': r.error
                    }
                    for r in results['pages_extracted']
                ]
            }
            
            # Save metadata
            with open(paths['metadata'], 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"✅ Successfully processed {pdf_file.name}")
            logger.info(f"   📁 Saved to: {paths['company_dir']}")
            
            return {
                'success': True,
                'results': results,
                'paths': {k: str(v) for k, v in paths.items()},  # Convert Path objects to strings
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process {pdf_file.name}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Process 10-K files
    k10_dir = raw_data_dir / "10-K"
    if k10_dir.exists():
        logger.info(f"Processing 10-K files from {k10_dir}")
        # Process only the specific 10-K file for testing
        target_pdf = k10_dir / "2024_meta_10-k.pdf"
        if target_pdf.exists():
            logger.info(f"Processing 10-K: {target_pdf.name}")
            
            year = target_pdf.stem.split('_')[0] if '_' in target_pdf.stem else "unknown"
            result = process_single_pdf(target_pdf, "10-K", year)
            
            all_results[f"10-K_{year}_{target_pdf.stem}"] = result
            total_stats['total_files'] += 1
            
            if result['success']:
                total_stats['successful_files'] += 1
                total_stats['total_pages'] += result['results']['statistics']['total_pages']
                total_stats['total_ocr_pages'] += result['results']['statistics']['ocr_pages']
                total_stats['total_processing_time'] += result['results']['statistics']['total_time']
            else:
                total_stats['failed_files'] += 1
        else:
            logger.warning(f"Target PDF not found: {target_pdf}")
    
    # Process 10-Q files (SKIPPED for testing - only processing 10-K)
    # q10_dir = raw_data_dir / "10-Q"
    # if q10_dir.exists():
    #     logger.info(f"Processing 10-Q files from {q10_dir}")
    #     for pdf_file in q10_dir.glob("*.pdf"):
    #         logger.info(f"Processing 10-Q: {pdf_file.name}")
    #         
    #         parts = pdf_file.stem.split('_')
    #         year = parts[0] if len(parts) > 0 else "unknown"
    #         quarter = parts[1] if len(parts) > 1 else "unknown"
    #         
    #         result = process_single_pdf(pdf_file, "10-Q", year, quarter)
    #         
    #         all_results[f"10-Q_{year}_{quarter}_{pdf_file.stem}"] = result
    #         total_stats['total_files'] += 1
    #         
    #         if result['success']:
    #             total_stats['successful_files'] += 1
    #             total_stats['total_pages'] += result['results']['statistics']['total_pages']
    #             total_stats['total_ocr_pages'] += result['results']['statistics']['ocr_pages']
    #             total_stats['total_processing_time'] += result['results']['statistics']['total_time']
    #         else:
    #             total_stats['failed_files'] += 1
    
    # Calculate final statistics
    total_stats['ocr_percentage'] = (total_stats['total_ocr_pages'] / total_stats['total_pages'] * 100) if total_stats['total_pages'] > 0 else 0
    total_stats['avg_time_per_page'] = total_stats['total_processing_time'] / total_stats['total_pages'] if total_stats['total_pages'] > 0 else 0
    
    # Save comprehensive processing log (convert PageExtraction objects to dicts)
    serializable_results = {}
    for key, result in all_results.items():
        if result.get('success', False):
            # Convert PageExtraction objects to dictionaries
            serializable_result = result.copy()
            if 'results' in serializable_result and 'pages_extracted' in serializable_result['results']:
                serializable_result['results']['pages_extracted'] = [
                    asdict(page) for page in serializable_result['results']['pages_extracted']
                ]
            serializable_results[key] = serializable_result
        else:
            serializable_results[key] = result
    
    processing_log = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'total_statistics': total_stats,
        'file_results': serializable_results,
        'output_directory': str(output_dir)
    }
    
    log_path = output_dir / "processing_log.json"
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(processing_log, f, indent=2)
    
    logger.info(f"📊 Processing complete! Log saved to {log_path}")
    return processing_log


# Example usage
if __name__ == "__main__":
    import yaml
    
    # Load parameters from params.yaml
    try:
        with open("params.yaml", 'r') as f:
            params = yaml.safe_load(f)
        
        # Get page limit from layout_detection config
        pages_to_process = params.get('layout_detection', {}).get('pages_to_process', 'all')
        if pages_to_process != 'all' and isinstance(pages_to_process, int):
            max_pages = pages_to_process
        else:
            max_pages = None
            
        print(f"🔧 Processing with page limit: {max_pages if max_pages else 'all pages'}")
    except FileNotFoundError:
        print("⚠️  params.yaml not found, processing all pages")
        max_pages = None
    
    # Process all PDF files in the structured directory
    results = process_multiple_pdfs(
        raw_data_dir=Path("data/raw"),
        output_dir=Path("data/parsed/text"),
        ocr_threshold=50,
        ocr_resolution=300,
        max_pages=max_pages
    )
    
    # Print summary statistics
    stats = results['total_statistics']
    print(f"\n{'='*60}")
    print(f"📄 DOCUMENT PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"Total files processed: {stats['total_files']}")
    print(f"Successful: {stats['successful_files']}")
    print(f"Failed: {stats['failed_files']}")
    print(f"Total pages: {stats['total_pages']}")
    print(f"OCR pages: {stats['total_ocr_pages']}")
    print(f"OCR percentage: {stats['ocr_percentage']:.1f}%")
    print(f"Total processing time: {stats['total_processing_time']:.2f} seconds")
    print(f"Average time per page: {stats['avg_time_per_page']:.3f} seconds")
    print(f"Output directory: {results['output_directory']}")
    print(f"{'='*60}")