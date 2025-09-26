# src/extractors/table_extractor.py

import camelot
import pdfplumber
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import logging
import json
from datetime import datetime
from dataclasses import dataclass, asdict
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TableExtraction:
    """Data class for table extraction results"""
    page_num: int
    table_num: int
    method: str
    table_data: pd.DataFrame
    confidence: float
    rows: int
    cols: int
    extraction_time: float
    error: Optional[str] = None

@dataclass
class PageTableExtraction:
    """Data class for page-level table extraction results"""
    page_num: int
    tables: List[TableExtraction]
    total_tables: int
    extraction_time: float
    error: Optional[str] = None
    comparison_data: Optional[Dict] = None

class TableExtractor:
    """
    Extract tables from PDF files using multiple methods with structured storage.
    Implements table extraction part of the pipeline with comprehensive metadata handling.
    """
    
    def __init__(
        self,
        output_dir: Optional[Path] = None,
        confidence_threshold: float = 0.5,
        min_table_size: Tuple[int, int] = (3, 3),  # Increased minimum size
        min_rows: int = 3,
        min_cols: int = 3
    ):
        """
        Initialize the table extractor.
        
        Args:
            output_dir: Directory to save extracted tables
            confidence_threshold: Minimum confidence score for table acceptance
            min_table_size: Minimum (rows, cols) for a valid table
            min_rows: Minimum number of rows for a valid table
            min_cols: Minimum number of columns for a valid table
        """
        # Check for Ghostscript availability
        self._check_ghostscript()
        
        # Initialize methods based on availability - only Camelot methods for financial docs
        self.methods = ['camelot-stream']  # Start with stream method
        if self.ghostscript_available:
            self.methods.insert(0, 'camelot-lattice')  # Add lattice if available
        
        # Log available methods
        logger.info(f"Available extraction methods: {self.methods}")
        
        self.output_dir = Path(output_dir) if output_dir else Path("data/parsed/tables")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.confidence_threshold = confidence_threshold
        self.min_table_size = min_table_size
        self.min_rows = min_rows
        self.min_cols = min_cols
        
        # Track statistics
        self.stats = {
            'total_pages': 0,
            'total_tables': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'total_time': 0
        }
    
    def extract_with_camelot(self, pdf_path: str, page_num: int, mode: str = 'lattice') -> List[TableExtraction]:
        """
        Extract tables using Camelot.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to extract from
            mode: Camelot extraction mode ('lattice' or 'stream')
            
        Returns:
            List of TableExtraction objects
        """
        start_time = time.time()
        tables = []
        
        # Check if lattice mode is requested but Ghostscript is not available
        if mode == 'lattice' and not self.ghostscript_available:
            logger.debug(f"Skipping Camelot lattice - Ghostscript not available")
            return tables
        
        try:
            # Configure Camelot with Ghostscript path if available
            if mode == 'lattice' and self.ghostscript_available:
                import os
                if 'GS_PATH' not in os.environ:
                    os.environ['GS_PATH'] = '/opt/homebrew/bin/gs'
            
            camelot_tables = camelot.read_pdf(
                str(pdf_path), 
            pages=str(page_num),
            flavor=mode,
            strip_text='\n'
        )
            
            for i, table in enumerate(camelot_tables):
                extraction_time = time.time() - start_time
                
                # Validate table before adding
                if self._is_valid_table(table.df):
                    table_extraction = TableExtraction(
                        page_num=page_num,
                        table_num=i + 1,
                        method=f'camelot-{mode}',
                        table_data=table.df,
                        confidence=table.accuracy,
                        rows=len(table.df),
                        cols=len(table.df.columns),
                        extraction_time=extraction_time
                    )
                    tables.append(table_extraction)
                
        except Exception as e:
            logger.error(f"Error extracting tables with Camelot {mode} on page {page_num}: {str(e)}")
            # Return empty list on error, not a failed extraction object
        
        return tables
    
    def extract_with_pdfplumber(self, pdf_path: str, page_num: int) -> List[TableExtraction]:
        """
        Extract tables using pdfplumber.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to extract from
            
        Returns:
            List of TableExtraction objects
        """
        start_time = time.time()
        tables = []
        
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                page = pdf.pages[page_num - 1]
                raw_tables = page.extract_tables()
                
                for i, table in enumerate(raw_tables):
                    if not table or len(table) < self.min_table_size[0]:
                        continue
                        
                    # Convert to DataFrame
                    if len(table) > 1:
                        df = pd.DataFrame(table[1:], columns=table[0])
                    else:
                        df = pd.DataFrame(table)
                    
                    # Check minimum size
                    if len(df) < self.min_table_size[0] or len(df.columns) < self.min_table_size[1]:
                        continue
                    
                    # Validate table before adding
                    if not self._is_valid_table(df):
                        continue
                    
                    extraction_time = time.time() - start_time
                    
                    table_extraction = TableExtraction(
                        page_num=page_num,
                        table_num=i + 1,
                        method='pdfplumber',
                        table_data=df,
                        confidence=1.0,  # pdfplumber doesn't provide confidence scores
                        rows=len(df),
                        cols=len(df.columns),
                        extraction_time=extraction_time
                    )
                    tables.append(table_extraction)
                    
        except Exception as e:
            logger.error(f"Error extracting tables with pdfplumber on page {page_num}: {str(e)}")
        
        return tables
    
    def _check_ghostscript(self):
        """Check if Ghostscript is available for Camelot lattice method."""
        try:
            import subprocess
            result = subprocess.run(['gs', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            self.ghostscript_available = result.returncode == 0
            
            if self.ghostscript_available:
                logger.info("✅ Ghostscript detected - Camelot lattice method available")
                # Set Ghostscript path for Camelot
                import os
                os.environ['GS_PATH'] = '/opt/homebrew/bin/gs'  # Homebrew path on macOS
                logger.info("🔧 Configured Ghostscript path for Camelot")
            else:
                logger.warning("❌ Ghostscript not found. Camelot lattice method will be skipped.")
                logger.info("To install Ghostscript: brew install ghostscript")
                
        except Exception as e:
            self.ghostscript_available = False
            logger.warning(f"❌ Ghostscript check failed: {e}. Camelot lattice method will be skipped.")
            logger.info("To install Ghostscript: brew install ghostscript")
        
        # Log the final status
        if self.ghostscript_available:
            logger.info("✅ Ghostscript available - Camelot lattice method enabled")
        else:
            logger.info("❌ Ghostscript not available - Camelot lattice method disabled")
    
    def _is_valid_table(self, df: pd.DataFrame) -> bool:
        """
        Check if a DataFrame represents a valid table (not header text or other content).
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if the DataFrame represents a valid table
        """
        if df.empty or len(df) < self.min_rows or len(df.columns) < self.min_cols:
            return False
        
        # Check if it's likely header text (single column with mostly text)
        if len(df.columns) == 1:
            # Single column tables are likely headers or lists, not data tables
            return False
        
        # Check for common header patterns
        first_row = df.iloc[0].astype(str).str.lower().str.strip()
        header_keywords = [
            'united states', 'securities', 'exchange', 'commission', 'washington',
            'form 10-k', 'form 10-q', 'annual report', 'quarterly report',
            'pursuant to section', 'fiscal year', 'transition report'
        ]
        
        if any(keyword in ' '.join(first_row) for keyword in header_keywords):
            return False
        
        # Check if table has meaningful data (not just repeated values)
        if len(df) > 1:
            # Check for diversity in data
            unique_values = df.nunique().sum()
            total_cells = len(df) * len(df.columns)
            if unique_values / total_cells < 0.3:  # Less than 30% unique values
                return False
        
        return True
    
    def score_tables(self, results: Dict[str, List[TableExtraction]]) -> str:
        """
        Score table extraction results and select the best method.
        
        Args:
            results: Dictionary mapping method names to list of TableExtraction objects
            
        Returns:
            Name of the best extraction method
        """
        if not results:
            return 'camelot-stream'  # Default fallback
        
        scores = {}
        
        for method, tables in results.items():
            if not tables:
                scores[method] = 0
                continue
            
            # Calculate composite score based on multiple factors
            total_confidence = sum(t.confidence for t in tables)
            avg_confidence = total_confidence / len(tables) if tables else 0
            
            # Penalize very small tables
            size_penalty = sum(1 for t in tables if t.rows < self.min_rows or t.cols < self.min_cols)
            size_score = max(0, len(tables) - size_penalty)
            
            # Prefer methods with more tables (but not too many)
            table_count_score = min(len(tables), 10)  # Cap at 10 tables
            
            # Bonus for tables with good data diversity
            diversity_bonus = 0
            for t in tables:
                unique_ratio = t.table_data.nunique().sum() / (t.rows * t.cols)
                if unique_ratio > 0.5:  # More than 50% unique values
                    diversity_bonus += 1
            
            # Combine scores
            composite_score = (
                avg_confidence * 0.3 +  # 30% weight on confidence
                size_score * 0.3 +      # 30% weight on table size
                table_count_score * 0.2 +  # 20% weight on table count
                diversity_bonus * 0.2   # 20% weight on data diversity
            )
            
            scores[method] = composite_score
        
        # Return method with highest score
        best_method = max(scores.items(), key=lambda x: x[1])[0]
        logger.info(f"Selected best method: {best_method} (score: {scores[best_method]:.3f})")
        
        return best_method
    
    def _analyze_page_heuristics(self, pdf_path: str, page_num: int) -> Dict[str, Any]:
        """
        Analyze page characteristics to determine optimal extraction method.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to analyze
            
        Returns:
            Dictionary with heuristic analysis results
        """
        heuristics = {
            'has_ruling_lines': False,
            'table_density': 0.0,
            'content_type': 'unknown',
            'recommended_method': 'camelot-stream',
            'confidence': 0.5,
            'ruling_line_ratio': 0.0,
            'financial_score': 0
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[page_num - 1]
                
                # Extract text and analyze structure
                text = page.extract_text() or ""
                
                # Heuristic 1: Check for ruling lines (improved)
                lines = page.lines
                
                # Filter lines by length and quality
                min_line_length = 20  # Minimum line length to be considered
                horizontal_lines = []
                vertical_lines = []
                
                for line in lines:
                    width = abs(line['x1'] - line['x0'])
                    height = abs(line['y1'] - line['y0'])
                    
                    # Horizontal lines: height < 2 and width > min_length
                    if height < 2 and width > min_line_length:
                        horizontal_lines.append(line)
                    # Vertical lines: width < 2 and height > min_length  
                    elif width < 2 and height > min_line_length:
                        vertical_lines.append(line)
                
                # Calculate ruling line metrics
                total_ruling_lines = len(horizontal_lines) + len(vertical_lines)
                ruling_line_ratio = total_ruling_lines / max(len(lines), 1) if lines else 0
                
                # Check for table-like line patterns (grid formation)
                has_table_grid = self._detect_table_grid(horizontal_lines, vertical_lines)
                
                heuristics['ruling_line_ratio'] = ruling_line_ratio
                heuristics['has_ruling_lines'] = ruling_line_ratio > 0.05 or has_table_grid  # Lower threshold, add grid detection
                heuristics['horizontal_lines'] = len(horizontal_lines)
                heuristics['vertical_lines'] = len(vertical_lines)
                
                # Heuristic 2: Analyze table density (improved)
                tables = page.find_tables()
                if tables:
                    total_cells = 0
                    total_table_area = 0
                    valid_tables = 0
                    
                    for table in tables:
                        if not table.rows or len(table.rows) == 0:
                            continue
                            
                        table_cells = 0
                        # Count cells more accurately
                        for row in table.rows:
                            if hasattr(row, '__len__'):
                                # Row is a list
                                table_cells += len(row)
                            elif hasattr(row, 'cells'):
                                # Row is a Row object with cells
                                table_cells += len(row.cells)
                            else:
                                # Try to extract text and count words as proxy for cells
                                try:
                                    row_text = str(row)
                                    # Estimate cells based on text content
                                    words = row_text.split()
                                    table_cells += max(len(words) // 2, 1)  # Rough estimate
                                except:
                                    table_cells += 2  # Conservative fallback
                        
                        # Calculate table area with validation
                        if table.bbox and len(table.bbox) == 4:
                            x0, y0, x1, y1 = table.bbox
                            if x1 > x0 and y1 > y0:  # Valid bbox
                                table_width = x1 - x0
                                table_height = y1 - y0
                                table_area = table_width * table_height
                                
                                if table_area > 100:  # Minimum table area threshold
                                    total_cells += table_cells
                                    total_table_area += table_area
                                    valid_tables += 1
                    
                    # Calculate density as cells per square unit
                    if total_table_area > 0 and valid_tables > 0:
                        heuristics['table_density'] = total_cells / total_table_area
                        heuristics['avg_cells_per_table'] = total_cells / valid_tables
                        heuristics['valid_tables'] = valid_tables
                    else:
                        heuristics['table_density'] = 0
                        heuristics['avg_cells_per_table'] = 0
                        heuristics['valid_tables'] = 0
                else:
                    heuristics['table_density'] = 0
                    heuristics['avg_cells_per_table'] = 0
                    heuristics['valid_tables'] = 0
                
                # Heuristic 3: Content type analysis
                financial_keywords = [
                    'revenue', 'income', 'expense', 'assets', 'liabilities', 'equity',
                    'balance sheet', 'income statement', 'cash flow', 'financial',
                    'quarterly', 'annual', 'fiscal year', 'earnings', 'profit'
                ]
                
                text_lower = text.lower()
                financial_score = sum(1 for keyword in financial_keywords if keyword in text_lower)
                heuristics['financial_score'] = financial_score
                heuristics['content_type'] = 'financial' if financial_score > 3 else 'data'
                
                # Calculate method scores based on heuristics - only Camelot methods
                lattice_score = 0
                stream_score = 0
                
                # Lattice method scoring - best for tables with clear ruling lines
                if heuristics['has_ruling_lines']:
                    lattice_score += 5  # Strong indicator for lattice
                if heuristics['table_density'] > 0.0001:  # Any table density helps lattice
                    lattice_score += min(heuristics['table_density'] * 10000, 4)  # Scale density, cap at 4
                if heuristics['content_type'] == 'financial' and heuristics['has_ruling_lines']:
                    lattice_score += 3  # Financial tables with borders favor lattice
                if heuristics['ruling_line_ratio'] > 0.1:  # High ruling line ratio
                    lattice_score += 2
                
                # Stream method scoring - best for borderless tables and financial content
                if heuristics['content_type'] == 'financial':
                    stream_score += 4  # Strong indicator for stream
                if heuristics['table_density'] > 0.00005:  # Any table density helps stream
                    stream_score += min(heuristics['table_density'] * 8000, 4)  # Scale density, cap at 4
                if not heuristics['has_ruling_lines']:  # No ruling lines favor stream
                    stream_score += 3
                if heuristics['financial_score'] > 5:  # High financial content
                    stream_score += 2
                
                # Select method with highest score
                method_scores = {
                    'camelot-lattice': lattice_score,
                    'camelot-stream': stream_score
                }
                
                # Only consider available methods
                available_scores = {k: v for k, v in method_scores.items() if k in self.methods}
                best_method = max(available_scores.items(), key=lambda x: x[1])[0]
                best_score = available_scores[best_method]
                
                # Calculate confidence based on score dominance
                total_score = sum(available_scores.values())
                confidence = best_score / total_score if total_score > 0 else 0.5
                
                heuristics['recommended_method'] = best_method
                heuristics['confidence'] = confidence
                heuristics['method_scores'] = method_scores
                    
        except Exception as e:
            logger.warning(f"Heuristic analysis failed for page {page_num}: {e}")
            # Default to stream method
            heuristics['recommended_method'] = 'camelot-stream'
            heuristics['confidence'] = 0.5
            
        return heuristics

    def _detect_table_grid(self, horizontal_lines: List, vertical_lines: List) -> bool:
        """
        Detect if lines form a table-like grid pattern.
        
        Args:
            horizontal_lines: List of horizontal line objects
            vertical_lines: List of vertical line objects
            
        Returns:
            True if lines form a table grid pattern
        """
        if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
            return False
        
        # Check for parallel horizontal lines (at least 2)
        h_y_positions = [line['y0'] for line in horizontal_lines]
        h_y_positions.sort()
        
        # Check for parallel vertical lines (at least 2)  
        v_x_positions = [line['x0'] for line in vertical_lines]
        v_x_positions.sort()
        
        # Simple grid detection: multiple parallel lines
        has_h_grid = len(set(round(y, 1) for y in h_y_positions)) >= 2
        has_v_grid = len(set(round(x, 1) for x in v_x_positions)) >= 2
        
        return has_h_grid and has_v_grid

    def hybrid_extract(self, pdf_path: str, page_num: int) -> PageTableExtraction:
        """
        Use heuristics to choose the best extraction method and extract tables.
        Implements intelligent method selection based on page characteristics.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to extract from
            
        Returns:
            PageTableExtraction object with results
        """
        start_time = time.time()
        
        # Analyze page heuristics
        heuristics = self._analyze_page_heuristics(pdf_path, page_num)
        recommended_method = heuristics['recommended_method']
        
        logger.debug(f"Page {page_num} heuristics: {heuristics}")
        
        # Create detailed reasoning based on actual scores
        method_scores = heuristics.get('method_scores', {})
        reasoning_parts = []
        
        # Show why this method was selected
        if recommended_method == 'camelot-lattice':
            if heuristics['has_ruling_lines']:
                reasoning_parts.append(f"ruling lines (ratio: {heuristics.get('ruling_line_ratio', 0):.3f})")
            if heuristics['table_density'] > 0.05:
                reasoning_parts.append(f"high density ({heuristics['table_density']:.3f})")
            if heuristics['content_type'] == 'data':
                reasoning_parts.append("non-financial content")
        elif recommended_method == 'camelot-stream':
            if heuristics['content_type'] == 'financial':
                reasoning_parts.append(f"financial content (score: {heuristics.get('financial_score', 0)})")
            if heuristics['table_density'] > 0.02:
                reasoning_parts.append(f"medium density ({heuristics['table_density']:.3f})")
            if not heuristics['has_ruling_lines']:
                reasoning_parts.append("no ruling lines")
        else:  # fallback
            reasoning_parts.append("fallback method")
        
        reasoning_str = ", ".join(reasoning_parts) if reasoning_parts else "default selection"
        
        # Show all method scores for transparency
        scores_str = " | ".join([f"{method}: {score:.1f}" for method, score in method_scores.items()])
        logger.info(f"Page {page_num}: Using {recommended_method} (confidence: {heuristics['confidence']:.2f}) - {reasoning_str}")
        logger.debug(f"All scores: {scores_str}")
        
        # Use only the heuristically selected method (no fallback)
        results = {}
        method_details = {}
        
        # Extract with recommended method only
        try:
            if 'camelot' in recommended_method:
                mode = recommended_method.split('-')[1]
                if mode == 'lattice' and not self.ghostscript_available:
                    logger.warning(f"Lattice method requested but Ghostscript not available, using stream instead")
                    mode = 'stream'
                    recommended_method = 'camelot-stream'
                
                tables = self.extract_with_camelot(str(pdf_path), page_num, mode)
                method_details[recommended_method] = {
                    'status': 'success',
                    'tables_found': len(tables),
                    'avg_confidence': np.mean([t.confidence for t in tables]) if tables else 0,
                    'total_rows': sum(t.rows for t in tables),
                    'total_cols': sum(t.cols for t in tables),
                    'avg_table_size': np.mean([t.rows * t.cols for t in tables]) if tables else 0,
                    'method_type': f'Camelot {mode}',
                    'description': f'Camelot {mode} mode - {"relies on ruling lines" if mode == "lattice" else "infers columns by grouping text spans"}',
                    'heuristic_selected': True
                }
            else:
                # Fallback to stream method if unknown method (should not happen with only Camelot methods)
                logger.warning(f"Unknown method {recommended_method}, falling back to camelot-stream")
                tables = self.extract_with_camelot(str(pdf_path), page_num, mode='stream')
                method_details['camelot-stream'] = {
                    'status': 'success',
                    'tables_found': len(tables),
                    'avg_confidence': np.mean([t.confidence for t in tables]) if tables else 0,
                    'total_rows': sum(t.rows for t in tables),
                    'total_cols': sum(t.cols for t in tables),
                    'avg_table_size': np.mean([t.rows * t.cols for t in tables]) if tables else 0,
                    'method_type': 'Camelot stream',
                    'description': 'Camelot stream mode - fallback for unknown recommendation',
                    'heuristic_selected': False
                }
                recommended_method = 'camelot-stream'
            
            results[recommended_method] = tables
            
        except Exception as e:
            logger.error(f"Method {recommended_method} failed on page {page_num}: {str(e)}")
            results[recommended_method] = []
            method_details[recommended_method] = {
                'status': 'failed', 
                'error': str(e),
                'heuristic_selected': True
            }
        
        # Use only the heuristically selected method
        best_method = recommended_method
        best_tables = results.get(recommended_method, [])
        
        # Filter tables by confidence threshold
        filtered_tables = [
            t for t in best_tables 
            if t.confidence >= self.confidence_threshold
        ]
        
        extraction_time = time.time() - start_time
        
        # Create comprehensive comparison data
        comparison_data = {
            'page_num': page_num,
            'heuristics': heuristics,
            'methods_compared': method_details,
            'best_method': best_method,
            'best_method_details': method_details.get(best_method, {}),
            'all_results': {method: len(tables) for method, tables in results.items()},
            'extraction_time': extraction_time,
            'heuristic_accuracy': 'success'  # Always success since we only use heuristically selected method
        }
        
        return PageTableExtraction(
            page_num=page_num,
            tables=filtered_tables,
            total_tables=len(filtered_tables),
            extraction_time=extraction_time,
            comparison_data=comparison_data
        )
    
    def process_pdf(
        self, 
        pdf_path: Path, 
        page_range: Optional[Tuple[int, int]] = None,
        save_individual_tables: bool = True
    ) -> Dict:
        """
        Process entire PDF document for table extraction.
        
        Args:
            pdf_path: Path to PDF file
            page_range: Optional tuple of (start_page, end_page)
            save_individual_tables: Save each table as separate file
            
        Returns:
            Dictionary with extraction results and statistics
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        logger.info(f"Processing PDF for tables: {pdf_path.name}")
        
        results = []
        doc_id = pdf_path.stem
        
        with pdfplumber.open(pdf_path) as pdf:
            # Determine pages to process
            if page_range:
                start, end = page_range
                pages_to_process = range(start - 1, min(end, len(pdf.pages)))
            else:
                pages_to_process = range(len(pdf.pages))
            
        # Process each page
        for i in pages_to_process:
            page_num = i + 1
            logger.info(f"Processing {pdf_path.name} - page {page_num}/{len(pdf.pages)} for tables")
            
            page_result = self.hybrid_extract(pdf_path, page_num)
            results.append(page_result)
            
            # Update statistics
            self.stats['total_pages'] += 1
            self.stats['total_tables'] += page_result.total_tables
            if page_result.total_tables > 0:
                self.stats['successful_extractions'] += 1
            if page_result.error:
                self.stats['failed_extractions'] += 1
            self.stats['total_time'] += page_result.extraction_time
            
            # Save individual tables if requested
            if save_individual_tables and page_result.tables:
                self._save_page_tables(doc_id, page_num, page_result)
        
        # Save extraction log
        self._save_extraction_log(doc_id, results)
        
        return {
            'doc_id': doc_id,
            'pdf_path': str(pdf_path),
            'total_pages': len(results),
            'pages_extracted': results,
            'statistics': self.stats.copy(),
            'output_dir': str(self.output_dir)
        }
    
    def _save_page_tables(self, doc_id: str, page_num: int, page_result: PageTableExtraction):
        """Save individual page tables and metadata."""
        for table in page_result.tables:
            # Save table as CSV
            table_filename = f"{doc_id}_page_{page_num:04d}_table_{table.table_num:02d}.csv"
            table_path = self.output_dir / table_filename
            table.table_data.to_csv(table_path, index=False, encoding='utf-8')
            
            # Save table metadata
            meta_filename = f"{doc_id}_page_{page_num:04d}_table_{table.table_num:02d}_meta.json"
            meta_path = self.output_dir / meta_filename
            
            metadata = {
                'page_num': table.page_num,
                'table_num': table.table_num,
                'method': table.method,
                'confidence': table.confidence,
                'rows': table.rows,
                'cols': table.cols,
                'extraction_time': table.extraction_time,
                'timestamp': datetime.utcnow().isoformat(),
                'error': table.error,
                'file_path': str(table_path)
            }
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        
        # Save method comparison data if available
        if page_result.comparison_data:
            comparison_filename = f"{doc_id}_page_{page_num:04d}_method_comparison.json"
            comparison_path = self.output_dir / comparison_filename
            
            with open(comparison_path, 'w', encoding='utf-8') as f:
                json.dump(page_result.comparison_data, f, indent=2)
    
    def _save_extraction_log(self, doc_id: str, results: List[PageTableExtraction]):
        """Save extraction log with statistics."""
        log_path = self.output_dir / f"{doc_id}_table_extraction_log.json"
        
        # Calculate method comparison statistics
        method_stats = {}
        for result in results:
            if result.comparison_data:
                for method, details in result.comparison_data['methods_compared'].items():
                    if method not in method_stats:
                        method_stats[method] = {
                            'total_tables_found': 0,
                            'pages_with_tables': 0,
                            'avg_confidence': [],
                            'total_rows': 0,
                            'total_cols': 0,
                            'success_count': 0,
                            'fail_count': 0
                        }
                    
                    if details['status'] == 'success':
                        method_stats[method]['total_tables_found'] += details['tables_found']
                        method_stats[method]['pages_with_tables'] += 1 if details['tables_found'] > 0 else 0
                        method_stats[method]['avg_confidence'].append(details['avg_confidence'])
                        method_stats[method]['total_rows'] += details['total_rows']
                        method_stats[method]['total_cols'] += details['total_cols']
                        method_stats[method]['success_count'] += 1
                    else:
                        method_stats[method]['fail_count'] += 1
        
        # Calculate averages
        for method in method_stats:
            if method_stats[method]['avg_confidence']:
                method_stats[method]['avg_confidence'] = np.mean(method_stats[method]['avg_confidence'])
            else:
                method_stats[method]['avg_confidence'] = 0
        
        log_data = {
            'doc_id': doc_id,
            'timestamp': datetime.utcnow().isoformat(),
            'total_pages': len(results),
            'total_tables': sum(r.total_tables for r in results),
            'statistics': {
                'total_extraction_time': sum(r.extraction_time for r in results),
                'avg_extraction_time': np.mean([r.extraction_time for r in results]) if results else 0,
                'avg_tables_per_page': np.mean([r.total_tables for r in results]) if results else 0,
                'successful_pages': sum(1 for r in results if r.total_tables > 0),
                'failed_pages': sum(1 for r in results if r.error)
            },
            'method_comparison': method_stats,
            'page_details': [
                {
                    'page': r.page_num,
                    'tables': r.total_tables,
                    'time': r.extraction_time,
                    'error': r.error,
                    'best_method': r.comparison_data['best_method'] if r.comparison_data else None
                }
                for r in results
            ]
        }
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"Table extraction log saved to {log_path}")
    
    def get_statistics(self) -> Dict:
        """Get extraction statistics."""
        return {
            **self.stats,
            'avg_tables_per_page': self.stats['total_tables'] / self.stats['total_pages']
                if self.stats['total_pages'] > 0 else 0,
            'avg_time_per_page': self.stats['total_time'] / self.stats['total_pages']
                if self.stats['total_pages'] > 0 else 0
        }
    
    def reset_statistics(self):
        """Reset extraction statistics."""
        self.stats = {
            'total_pages': 0,
            'total_tables': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'total_time': 0
        }


def create_structured_table_output(
    pdf_file: Path,
    base_output_dir: Path = Path("data/parsed/tables")
) -> Dict[str, Path]:
    """
    Create structured directory layout for table extraction output.
    Dynamically extracts company, document type, year, and quarter from filename.
    
    Args:
        pdf_file: Path to the PDF file
        base_output_dir: Base output directory
        
    Returns:
        Dictionary with path mappings for different output types
    """
    # Extract information from filename dynamically
    filename = pdf_file.stem
    parent_dir = pdf_file.parent.name
    
    # Extract document type from parent directory
    doc_type = parent_dir
    
    # Extract company, year, and quarter from filename
    # Expected patterns:
    # - 2023_meta.pdf -> company: meta, year: 2023
    # - 2024_1_meta.pdf -> company: meta, year: 2024, quarter: 1
    # - 2024_2_meta.pdf -> company: meta, year: 2024, quarter: 2
    
    parts = filename.split('_')
    if len(parts) >= 2:
        year = parts[0]
        company = parts[-1].lower()  # Last part is company name
        
        # Check if there's a quarter (middle part)
        quarter = None
        if len(parts) == 3 and parts[1].isdigit():
            quarter = parts[1]
    else:
        # Fallback parsing
        year = "unknown"
        company = filename.lower()
        quarter = None
    
    # Create document folder name
    if quarter:
        doc_folder = f"{company}_{year}_Q{quarter}"
    else:
        doc_folder = f"{company}_{year}"
    
    # Create directory structure
    doc_type_dir = base_output_dir / doc_type
    company_dir = doc_type_dir / doc_folder
    
    # Create directories (tables will be stored directly in company_dir)
    for directory in [doc_type_dir, company_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    return {
        'metadata': company_dir / "metadata.json",
        'tables_summary': company_dir / "tables_summary.json",
        'tables_dir': company_dir,  # Store tables directly in company_dir
        'company_dir': company_dir,
        'extracted_info': {
            'company': company,
            'year': year,
            'quarter': quarter,
            'doc_type': doc_type,
            'filename': pdf_file.name
        }
    }


def process_multiple_pdfs_for_tables(
    raw_data_dir: Path = Path("data/raw"),
    output_dir: Path = Path("data/parsed/tables"),
    confidence_threshold: float = 0.3,
    min_table_size: Tuple[int, int] = (3, 3)
) -> Dict:
    """
    Process all PDF files in the raw data directory structure for table extraction.
    
    Args:
        raw_data_dir: Directory containing PDF files organized by type
        output_dir: Base directory to save structured table output
        confidence_threshold: Minimum confidence score for table acceptance
        min_table_size: Minimum (rows, cols) for a valid table
        
    Returns:
        Dictionary with processing results for all files
    """
    
    all_results = {}
    total_stats = {
        'total_files': 0,
        'successful_files': 0,
        'failed_files': 0,
        'total_pages': 0,
        'total_tables': 0,
        'total_processing_time': 0,
        'avg_tables_per_page': 0,
        'avg_time_per_page': 0
    }
    
    def process_single_pdf(pdf_file: Path) -> Dict:
        """Process a single PDF file for table extraction with structured output."""
        try:
            # Create structured directory layout dynamically
            paths = create_structured_table_output(
                pdf_file=pdf_file,
                base_output_dir=output_dir
            )
            
            # Extract info from the dynamic parsing
            extracted_info = paths['extracted_info']
            company = extracted_info['company']
            year = extracted_info['year']
            quarter = extracted_info['quarter']
            doc_type = extracted_info['doc_type']
            
            # Initialize extractor with structured output
            extractor = TableExtractor(
                output_dir=paths['tables_dir'],
                confidence_threshold=confidence_threshold,
                min_table_size=min_table_size
            )
            
            # Process PDF
            results = extractor.process_pdf(
                pdf_file,
                page_range=None,
                save_individual_tables=True
            )
            
            # Create comprehensive metadata
            metadata = {
                'document_info': {
                    'type': doc_type,
                    'year': year,
                    'quarter': quarter,
                    'company': company,
                    'source_file': pdf_file.name,
                    'processed_at': datetime.utcnow().isoformat()
                },
                'extraction_stats': results['statistics'],
                'file_paths': {
                    'tables_directory': str(paths['tables_dir']),
                    'tables_summary': str(paths['tables_summary']),
                    'document_directory': str(paths['company_dir'])
                },
                'page_details': [
                    {
                        'page_num': r.page_num,
                        'total_tables': r.total_tables,
                        'extraction_time': r.extraction_time,
                        'error': r.error,
                        'tables': [
                            {
                                'table_num': t.table_num,
                                'method': t.method,
                                'confidence': t.confidence,
                                'rows': t.rows,
                                'cols': t.cols,
                                'extraction_time': t.extraction_time,
                                'error': t.error
                            }
                            for t in r.tables
                        ]
                    }
                    for r in results['pages_extracted']
                ]
            }
            
            # Create tables summary
            tables_summary = {
                'document_info': metadata['document_info'],
                'total_tables': results['statistics']['total_tables'],
                'total_pages': results['statistics']['total_pages'],
                'avg_tables_per_page': results['statistics']['total_tables'] / results['statistics']['total_pages'] if results['statistics']['total_pages'] > 0 else 0,
                'extraction_methods_used': list(set(t.method for r in results['pages_extracted'] for t in r.tables)),
                'confidence_scores': [t.confidence for r in results['pages_extracted'] for t in r.tables],
                'table_sizes': [(t.rows, t.cols) for r in results['pages_extracted'] for t in r.tables],
                'pages_with_tables': [r.page_num for r in results['pages_extracted'] if r.total_tables > 0],
                'processing_time': results['statistics']['total_time']
            }
            
            # Save metadata and summary
            with open(paths['metadata'], 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            with open(paths['tables_summary'], 'w', encoding='utf-8') as f:
                json.dump(tables_summary, f, indent=2)
            
            logger.info(f"✅ Successfully processed {pdf_file.name} for tables")
            logger.info(f"   📁 Saved to: {paths['company_dir']}")
            logger.info(f"   📊 Found {results['statistics']['total_tables']} tables")
            
            return {
                'success': True,
                'results': {
                    'statistics': results['statistics'],
                    'pages_extracted': [
                        {
                            'page_num': r.page_num,
                            'total_tables': r.total_tables,
                            'extraction_time': r.extraction_time,
                            'error': r.error,
                            'tables': [
                                {
                                    'table_num': t.table_num,
                                    'method': t.method,
                                    'confidence': t.confidence,
                                    'rows': t.rows,
                                    'cols': t.cols,
                                    'extraction_time': t.extraction_time,
                                    'error': t.error
                                }
                                for t in r.tables
                            ]
                        }
                        for r in results['pages_extracted']
                    ]
                },
                'paths': {k: str(v) for k, v in paths.items()},
                'metadata': metadata,
                'tables_summary': tables_summary
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process {pdf_file.name} for tables: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Process all PDF files dynamically
    logger.info(f"Processing all PDF files for tables from {raw_data_dir}")
    
    # Find all PDF files in any subdirectory
    pdf_files = list(raw_data_dir.rglob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {raw_data_dir}")
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'total_statistics': total_stats,
            'file_results': all_results,
            'output_directory': str(output_dir)
        }
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    for pdf_file in pdf_files:
        # Get relative path for better organization
        relative_path = pdf_file.relative_to(raw_data_dir)
        logger.info(f"Processing for tables: {relative_path}")
        
        result = process_single_pdf(pdf_file)
        
        # Create a unique key for the result
        result_key = str(relative_path).replace('/', '_').replace('.pdf', '')
        all_results[result_key] = result
        total_stats['total_files'] += 1
        
        if result['success']:
            total_stats['successful_files'] += 1
            total_stats['total_pages'] += result['results']['statistics']['total_pages']
            total_stats['total_tables'] += result['results']['statistics']['total_tables']
            total_stats['total_processing_time'] += result['results']['statistics']['total_time']
        else:
            total_stats['failed_files'] += 1
    
    # Calculate final statistics
    total_stats['avg_tables_per_page'] = total_stats['total_tables'] / total_stats['total_pages'] if total_stats['total_pages'] > 0 else 0
    total_stats['avg_time_per_page'] = total_stats['total_processing_time'] / total_stats['total_pages'] if total_stats['total_pages'] > 0 else 0
    
    # Save comprehensive processing log
    processing_log = {
        'timestamp': datetime.utcnow().isoformat(),
        'total_statistics': total_stats,
        'file_results': all_results,
        'output_directory': str(output_dir)
    }
    
    log_path = output_dir / "table_processing_log.json"
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(processing_log, f, indent=2)
    
    logger.info(f"📊 Table processing complete! Log saved to {log_path}")
    return processing_log


# Example usage
if __name__ == "__main__":
    # Quick test with all pages of first PDF
    logger.info("🚀 Starting table extraction test (all pages of first PDF)...")
    
    # Process all PDFs directly
    logger.info("🚀 Starting FULL table extraction for all PDFs...")
    results = process_multiple_pdfs_for_tables(
        raw_data_dir=Path("data/raw"),
        output_dir=Path("data/parsed/tables"),
        confidence_threshold=0.3,  # Lower threshold for better detection
        min_table_size=(3, 3)      # Higher minimum size to avoid headers
    )
    
    # Print comprehensive summary statistics
    if 'results' in locals():
        total_stats = results['total_statistics']
        print(f"\n{'='*80}")
        print(f"📊 COMPREHENSIVE TABLE EXTRACTION SUMMARY")
        print(f"{'='*80}")
        print(f"📁 Files processed: {total_stats['total_files']}")
        print(f"✅ Successful files: {total_stats['successful_files']}")
        print(f"❌ Failed files: {total_stats['failed_files']}")
        print(f"📄 Total pages: {total_stats['total_pages']}")
        print(f"📊 Total tables found: {total_stats['total_tables']}")
        print(f"⏱️  Total processing time: {total_stats['total_processing_time']:.2f} seconds")
        print(f"📈 Average tables per page: {total_stats['avg_tables_per_page']:.3f}")
        print(f"⚡ Average time per page: {total_stats['avg_time_per_page']:.3f} seconds")
        print(f"📂 Output directory: data/parsed/tables")
        
        