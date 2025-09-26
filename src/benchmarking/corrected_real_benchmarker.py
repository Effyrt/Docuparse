#!/usr/bin/env python3
"""
Corrected REAL Pipeline Benchmarker - Uses correct API methods

This runs the real extractors with their actual method signatures.
"""

import time
import psutil
import json
import logging
import tracemalloc
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorrectedRealBenchmarker:
    """Benchmarks using correct API methods."""
    
    def __init__(self, max_pages_per_stage: int = 10):
        self.max_pages = max_pages_per_stage
        self.results = {
            'benchmark_info': {
                'timestamp': datetime.now().isoformat(),
                'system_info': self._get_system_info(),
                'note': 'REAL measurements using correct API methods',
                'max_pages_per_stage': max_pages_per_stage
            },
            'stage_benchmarks': {},
            'failures': [],
            'summary': {}
        }
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Get actual system information."""
        memory = psutil.virtual_memory()
        cpu_freq = psutil.cpu_freq()
        
        return {
            'cpu_count_physical': psutil.cpu_count(logical=False),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'cpu_freq_current_mhz': cpu_freq.current if cpu_freq else 'unknown',
            'total_memory_gb': round(memory.total / (1024**3), 2),
            'available_memory_gb': round(memory.available / (1024**3), 2),
            'memory_usage_percent': memory.percent,
            'platform': sys.platform,
            'python_version': sys.version.split()[0]
        }
    
    def benchmark_real_text_extraction(self) -> Dict[str, Any]:
        """Benchmark REAL text extraction using correct API."""
        logger.info("🔍 Benchmarking REAL text extraction...")
        
        stage_results = {
            'stage_name': 'text_extraction_REAL',
            'method': 'TextExtractor.process_pdf()',
            'pages_processed': 0,
            'pages_failed': 0,
            'total_runtime_seconds': 0,
            'memory_usage': {},
            'per_page_timings': [],
            'failures': [],
            'extraction_stats': {}
        }
        
        try:
            from extractors.text_extractor import TextExtractor
            import pdfplumber
            
            tracemalloc.start()
            process = psutil.Process()
            start_memory = process.memory_info().rss
            peak_memory = start_memory
            
            start_time = time.time()
            
            # Initialize the real text extractor
            output_dir = Path("../../benchmarks/temp_text_output")
            output_dir.mkdir(exist_ok=True)
            
            extractor = TextExtractor(
                ocr_threshold=50,
                ocr_resolution=300,
                save_word_boxes=True,
                output_dir=output_dir
            )
            
            # Get PDF files and limit pages
            pdf_files = list(Path("../../data/raw").rglob("*.pdf"))
            pages_processed = 0
            
            for pdf_path in pdf_files[:1]:  # Only process one file for speed
                if pages_processed >= self.max_pages:
                    break
                    
                try:
                    logger.info(f"Processing {pdf_path.name} with REAL text extractor...")
                    
                    file_start_time = time.time()
                    
                    # Use actual API: process_pdf with page range limit
                    results = extractor.process_pdf(
                        pdf_path,
                        page_range=range(1, min(self.max_pages + 1, 11)),  # Max 10 pages
                        save_individual_pages=False  # Don't save for benchmark
                    )
                    
                    file_end_time = time.time()
                    file_processing_time = file_end_time - file_start_time
                    
                    # Process results
                    if results and 'pages' in results:
                        pages_in_result = len(results['pages'])
                        avg_time_per_page = file_processing_time / max(pages_in_result, 1)
                        
                        for page_result in results['pages']:
                            stage_results['per_page_timings'].append({
                                'page': page_result.page_num,
                                'file': pdf_path.name,
                                'time_seconds': avg_time_per_page,
                                'text_length': page_result.char_count,
                                'word_count': page_result.word_count,
                                'ocr_used': page_result.ocr_used,
                                'success': page_result.error is None
                            })
                            
                            pages_processed += 1
                        
                        stage_results['extraction_stats'] = {
                            'total_pages': pages_in_result,
                            'ocr_usage': sum(1 for p in results['pages'] if p.ocr_used),
                            'total_words': sum(p.word_count for p in results['pages']),
                            'total_chars': sum(p.char_count for p in results['pages']),
                            'avg_words_per_page': sum(p.word_count for p in results['pages']) / max(pages_in_result, 1)
                        }
                    
                    # Monitor memory
                    current_memory = process.memory_info().rss
                    peak_memory = max(peak_memory, current_memory)
                    
                    logger.info(f"Processed {pdf_path.name}: {pages_processed} pages in {file_processing_time:.2f}s")
                    
                except Exception as file_error:
                    failure = {
                        'file': pdf_path.name,
                        'error': str(file_error),
                        'timestamp': datetime.now().isoformat(),
                        'type': 'file_level'
                    }
                    stage_results['failures'].append(failure)
                    logger.error(f"File {pdf_path.name} failed: {file_error}")
            
            end_time = time.time()
            
            current_memory, peak_traced_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            memory_delta = peak_memory - start_memory
            
            stage_results.update({
                'pages_processed': pages_processed,
                'total_runtime_seconds': end_time - start_time,
                'avg_time_per_page': (end_time - start_time) / max(pages_processed, 1),
                'memory_usage': {
                    'peak_memory_mb': round(peak_memory / (1024*1024), 2),
                    'memory_delta_mb': round(memory_delta / (1024*1024), 2),
                    'peak_traced_memory_mb': round(peak_traced_memory / (1024*1024), 2)
                }
            })
            
        except ImportError as e:
            stage_results['failures'].append({
                'error': f"Could not import TextExtractor: {e}",
                'timestamp': datetime.now().isoformat(),
                'type': 'import_error'
            })
            logger.error(f"Could not import TextExtractor: {e}")
        
        return stage_results
    
    def benchmark_real_table_extraction(self) -> Dict[str, Any]:
        """Benchmark REAL table extraction using correct API."""
        logger.info("🔍 Benchmarking REAL table extraction...")
        
        stage_results = {
            'stage_name': 'table_extraction_REAL',
            'method': 'TableExtractor.hybrid_extract()',
            'pages_processed': 0,
            'tables_found': 0,
            'pages_failed': 0,
            'total_runtime_seconds': 0,
            'memory_usage': {},
            'per_page_timings': [],
            'failures': []
        }
        
        try:
            from extractors.table_extractor import TableExtractor
            
            tracemalloc.start()
            process = psutil.Process()
            start_memory = process.memory_info().rss
            peak_memory = start_memory
            
            start_time = time.time()
            
            # Initialize the real table extractor
            extractor = TableExtractor()
            
            # Get PDF files and limit pages
            pdf_files = list(Path("../../data/raw").rglob("*.pdf"))
            pages_processed = 0
            total_tables = 0
            
            for pdf_path in pdf_files[:1]:  # Only process one file
                if pages_processed >= self.max_pages:
                    break
                    
                # Process limited pages
                for page_num in range(1, min(self.max_pages + 1, 6)):  # Max 5 pages
                    try:
                        logger.info(f"Processing page {page_num} of {pdf_path.name}...")
                        
                        page_start_time = time.time()
                        
                        # Use actual API: hybrid_extract for single page
                        page_result = extractor.hybrid_extract(str(pdf_path), page_num)
                        
                        page_end_time = time.time()
                        page_processing_time = page_end_time - page_start_time
                        
                        # Process results
                        tables_on_page = len(page_result.tables) if page_result.tables else 0
                        total_tables += tables_on_page
                        
                        stage_results['per_page_timings'].append({
                            'page': page_num,
                            'file': pdf_path.name,
                            'time_seconds': page_processing_time,
                            'tables_found': tables_on_page,
                            'success': page_result.error is None
                        })
                        
                        pages_processed += 1
                        
                        # Monitor memory
                        current_memory = process.memory_info().rss
                        peak_memory = max(peak_memory, current_memory)
                        
                        if pages_processed >= self.max_pages:
                            break
                        
                    except Exception as page_error:
                        stage_results['pages_failed'] += 1
                        failure = {
                            'file': pdf_path.name,
                            'page': page_num,
                            'error': str(page_error),
                            'timestamp': datetime.now().isoformat()
                        }
                        stage_results['failures'].append(failure)
                        logger.error(f"Page {page_num} failed: {page_error}")
            
            end_time = time.time()
            
            current_memory, peak_traced_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            memory_delta = peak_memory - start_memory
            
            stage_results.update({
                'pages_processed': pages_processed,
                'tables_found': total_tables,
                'total_runtime_seconds': end_time - start_time,
                'avg_time_per_page': (end_time - start_time) / max(pages_processed, 1),
                'memory_usage': {
                    'peak_memory_mb': round(peak_memory / (1024*1024), 2),
                    'memory_delta_mb': round(memory_delta / (1024*1024), 2),
                    'peak_traced_memory_mb': round(peak_traced_memory / (1024*1024), 2)
                }
            })
            
        except ImportError as e:
            stage_results['failures'].append({
                'error': f"Could not import TableExtractor: {e}",
                'timestamp': datetime.now().isoformat(),
                'type': 'import_error'
            })
            logger.error(f"Could not import TableExtractor: {e}")
        
        return stage_results
    
    def benchmark_simplified_docling(self) -> Dict[str, Any]:
        """Benchmark REAL Docling processing (simplified version)."""
        logger.info("🔍 Benchmarking REAL Docling processing...")
        
        stage_results = {
            'stage_name': 'docling_REAL',
            'method': 'docling.DocumentConverter()',
            'pages_processed': 0,
            'pages_failed': 0,
            'total_runtime_seconds': 0,
            'memory_usage': {},
            'per_page_timings': [],
            'failures': [],
            'docling_stats': {}
        }
        
        try:
            # Try to import and use docling
            from docling.document_converter import DocumentConverter
            
            tracemalloc.start()
            process = psutil.Process()
            start_memory = process.memory_info().rss
            peak_memory = start_memory
            
            start_time = time.time()
            
            # Initialize Docling converter
            converter = DocumentConverter()
            
            # Get one small PDF file
            pdf_files = list(Path("../../data/raw").rglob("*.pdf"))
            pages_processed = 0
            
            for pdf_path in pdf_files[:1]:  # Only one file
                try:
                    logger.info(f"Processing {pdf_path.name} with REAL Docling (may take 2-3 minutes)...")
                    
                    file_start_time = time.time()
                    
                    # Use actual Docling processing
                    result = converter.convert(str(pdf_path))
                    
                    file_end_time = time.time()
                    file_processing_time = file_end_time - file_start_time
                    
                    # Process results
                    if result and hasattr(result, 'document'):
                        # Get document pages
                        doc = result.document
                        pages_in_result = len(doc.pages) if hasattr(doc, 'pages') else 1
                        
                        # Calculate per-page timing
                        avg_time_per_page = file_processing_time / max(pages_in_result, 1)
                        
                        # Record limited pages for benchmark
                        pages_to_record = min(pages_in_result, 5)  # Max 5 for reporting
                        
                        for i in range(pages_to_record):
                            stage_results['per_page_timings'].append({
                                'page': i + 1,
                                'file': pdf_path.name,
                                'time_seconds': avg_time_per_page,
                                'success': True
                            })
                            
                            pages_processed += 1
                        
                        stage_results['docling_stats'] = {
                            'total_pages_in_document': pages_in_result,
                            'processing_time_per_page': avg_time_per_page,
                            'document_type': str(type(doc)),
                            'conversion_successful': True
                        }
                    
                    # Monitor memory
                    current_memory = process.memory_info().rss
                    peak_memory = max(peak_memory, current_memory)
                    
                    logger.info(f"Processed {pdf_path.name}: {pages_in_result} pages in {file_processing_time:.2f}s")
                    break  # Only process one file
                    
                except Exception as file_error:
                    failure = {
                        'file': pdf_path.name,
                        'error': str(file_error),
                        'timestamp': datetime.now().isoformat(),
                        'type': 'file_level'
                    }
                    stage_results['failures'].append(failure)
                    logger.error(f"Docling processing for {pdf_path.name} failed: {file_error}")
            
            end_time = time.time()
            
            current_memory, peak_traced_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            memory_delta = peak_memory - start_memory
            
            stage_results.update({
                'pages_processed': pages_processed,
                'total_runtime_seconds': end_time - start_time,
                'avg_time_per_page': (end_time - start_time) / max(pages_processed, 1),
                'memory_usage': {
                    'peak_memory_mb': round(peak_memory / (1024*1024), 2),
                    'memory_delta_mb': round(memory_delta / (1024*1024), 2),
                    'peak_traced_memory_mb': round(peak_traced_memory / (1024*1024), 2)
                }
            })
            
        except ImportError as e:
            stage_results['failures'].append({
                'error': f"Could not import docling: {e}",
                'timestamp': datetime.now().isoformat(),
                'type': 'import_error'
            })
            logger.error(f"Could not import docling: {e}")
        
        return stage_results
    
    def run_corrected_benchmark(self) -> Dict[str, Any]:
        """Run corrected benchmark using proper API methods."""
        logger.info("🚀 Starting CORRECTED pipeline benchmark...")
        
        stages = [
            ('text_extraction', self.benchmark_real_text_extraction),
            ('table_extraction', self.benchmark_real_table_extraction),
            ('docling', self.benchmark_simplified_docling)
        ]
        
        total_start_time = time.time()
        
        for stage_name, benchmark_func in stages:
            try:
                logger.info(f"🔄 Running CORRECTED {stage_name} benchmark...")
                stage_results = benchmark_func()
                self.results['stage_benchmarks'][stage_name] = stage_results
                
                # Collect failures
                if stage_results.get('failures'):
                    self.results['failures'].extend(stage_results['failures'])
                    
            except Exception as e:
                logger.error(f"CORRECTED stage {stage_name} benchmark failed: {e}")
                self.results['failures'].append({
                    'stage': stage_name,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        total_end_time = time.time()
        
        # Generate summary
        self.results['summary'] = self._generate_corrected_summary(total_end_time - total_start_time)
        
        return self.results
    
    def _generate_corrected_summary(self, total_runtime: float) -> Dict[str, Any]:
        """Generate summary of corrected benchmark results."""
        summary = {
            'total_runtime_seconds': round(total_runtime, 2),
            'total_pages_processed': 0,
            'total_failures': len(self.results['failures']),
            'corrected_performance_by_stage': {},
            'real_bottlenecks': {},
            'validated_recommendations': []
        }
        
        # Analyze each stage
        stage_times = {}
        successful_stages = []
        
        for stage_name, stage_data in self.results['stage_benchmarks'].items():
            pages = stage_data.get('pages_processed', 0)
            runtime = stage_data.get('total_runtime_seconds', 0)
            avg_time_per_page = stage_data.get('avg_time_per_page', 0)
            
            summary['total_pages_processed'] += pages
            
            success = pages > 0 and len(stage_data.get('failures', [])) == 0
            if success:
                successful_stages.append(stage_name)
            
            summary['corrected_performance_by_stage'][stage_name] = {
                'pages_processed': pages,
                'total_runtime_seconds': round(runtime, 2),
                'avg_time_per_page_seconds': round(avg_time_per_page, 3),
                'throughput_pages_per_minute': round(60 / avg_time_per_page, 1) if avg_time_per_page > 0 else 0,
                'memory_peak_mb': stage_data.get('memory_usage', {}).get('peak_memory_mb', 0),
                'success': success,
                'failure_count': len(stage_data.get('failures', []))
            }
            
            if avg_time_per_page > 0 and success:
                stage_times[stage_name] = avg_time_per_page
        
        # Find real bottlenecks from successful stages
        if stage_times:
            slowest_stage = max(stage_times.keys(), key=lambda k: stage_times[k])
            fastest_stage = min(stage_times.keys(), key=lambda k: stage_times[k])
            
            summary['real_bottlenecks'] = {
                'slowest_stage': slowest_stage,
                'fastest_stage': fastest_stage,
                'slowest_time_per_page': round(stage_times[slowest_stage], 3),
                'fastest_time_per_page': round(stage_times[fastest_stage], 3),
                'bottleneck_factor': round(stage_times[slowest_stage] / stage_times[fastest_stage], 1)
            }
        
        # Validated recommendations based on actual results
        failed_stages = [stage for stage, data in summary['corrected_performance_by_stage'].items() if not data['success']]
        
        if successful_stages:
            summary['validated_recommendations'].append(f"Successfully benchmarked stages: {', '.join(successful_stages)}")
        
        if failed_stages:
            summary['validated_recommendations'].append(f"Stages needing attention: {', '.join(failed_stages)}")
        
        if 'real_bottlenecks' in summary:
            bottleneck = summary['real_bottlenecks']
            summary['validated_recommendations'].append(f"Confirmed bottleneck: {bottleneck['slowest_stage']} is {bottleneck['bottleneck_factor']}x slower than {bottleneck['fastest_stage']}")
        
        # Specific performance insights
        for stage_name, perf in summary['corrected_performance_by_stage'].items():
            if perf['success']:
                if perf['avg_time_per_page_seconds'] > 30:  # > 30 seconds per page
                    summary['validated_recommendations'].append(f"{stage_name} is very slow ({perf['avg_time_per_page_seconds']}s/page) - needs optimization")
                elif perf['avg_time_per_page_seconds'] < 1:  # < 1 second per page
                    summary['validated_recommendations'].append(f"{stage_name} is efficient ({perf['avg_time_per_page_seconds']}s/page) - good performance")
        
        return summary
    
    def save_corrected_results(self) -> Path:
        """Save corrected benchmark results."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = Path(f"../../benchmarks/results/CORRECTED_pipeline_benchmark_{timestamp}.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
            
        logger.info(f"CORRECTED benchmark results saved to {output_file}")
        return output_file


if __name__ == "__main__":
    benchmarker = CorrectedRealBenchmarker(max_pages_per_stage=10)
    
    print("🚀 Starting CORRECTED REAL Pipeline Performance Benchmark")
    print("=" * 60)
    print("⚠️  This uses correct API methods and may take 5-10 minutes...")
    
    results = benchmarker.run_corrected_benchmark()
    output_file = benchmarker.save_corrected_results()
    
    print("\n📊 CORRECTED REAL BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total pages processed: {results['summary']['total_pages_processed']}")
    print(f"Total runtime: {results['summary']['total_runtime_seconds']} seconds")
    print(f"Total failures: {results['summary']['total_failures']}")
    
    if 'real_bottlenecks' in results['summary']:
        bottleneck = results['summary']['real_bottlenecks']
        print(f"\\nConfirmed Bottleneck: {bottleneck['slowest_stage']} ({bottleneck['slowest_time_per_page']}s per page)")
        print(f"Bottleneck factor: {bottleneck['bottleneck_factor']}x slower than {bottleneck['fastest_stage']}")
    
    print(f"\\n🔄 Stage Performance:")
    for stage, perf in results['summary']['corrected_performance_by_stage'].items():
        status = "✅" if perf['success'] else "❌"
        print(f"  {status} {stage}: {perf['pages_processed']} pages, {perf['avg_time_per_page_seconds']}s/page, {perf['throughput_pages_per_minute']} pages/min")
    
    if results['summary']['validated_recommendations']:
        print(f"\\n💡 Validated Recommendations:")
        for rec in results['summary']['validated_recommendations']:
            print(f"  - {rec}")
    
    print(f"\\n📄 Detailed results saved to: {output_file}")
