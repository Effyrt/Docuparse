#!/usr/bin/env python3
"""
Dynamic test script for text extraction pipeline validation.

This script dynamically discovers and validates any folder structure present in data/parsed/text.
It validates the following checkpoints:
1. Per-page .txt files exist for each PDF
2. A log records pages that needed OCR
3. Word bounding boxes are persisted using page.extract_words()
4. Structured directory layout is correct
5. Metadata files contain expected information
6. Full document files are generated
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextExtractionValidator:
    """Dynamic validator for text extraction pipeline results."""
    
    def __init__(self, base_dir: Path = Path("data/parsed/text"), 
                 expected_structure: Dict = None):
        self.base_dir = Path(base_dir)
        self.expected_structure = expected_structure or {
            'required_file_patterns': ['*_page_*.txt', '*_words.json', '*_meta.json'],
            'required_files': ['full_document.txt', 'full_document.md', 'metadata.json'],
            'min_pages_per_doc': 1,
            'min_file_size': 1000,
            'financial_keywords': ['revenue', 'income', 'assets', 'liabilities', 'stock', 'shares']
        }
        self.results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': [],
            'discovered_directories': []
        }
    
    def discover_all_testable_directories(self) -> List[Path]:
        """Dynamically discover all directories that should be tested."""
        testable_dirs = []
        
        if not self.base_dir.exists():
            logger.error(f"Base directory does not exist: {self.base_dir}")
            return testable_dirs
        
        # Look for document type directories (10-K, 10-Q, etc.)
        for doc_type_dir in self.base_dir.iterdir():
            if doc_type_dir.is_dir():
                logger.info(f"Found document type directory: {doc_type_dir.name}")
                
                # Look for company directories within each doc type
                for company_dir in doc_type_dir.iterdir():
                    if company_dir.is_dir():
                        # Check if this directory has the expected structure
                        if self.has_expected_structure(company_dir):
                            relative_path = company_dir.relative_to(self.base_dir)
                            testable_dirs.append(relative_path)
                            logger.info(f"  - Found testable directory: {relative_path}")
                        else:
                            logger.warning(f"  - Skipping directory (missing expected structure): {company_dir.name}")
        
        self.results['discovered_directories'] = [str(d) for d in testable_dirs]
        logger.info(f"Total testable directories discovered: {len(testable_dirs)}")
        return testable_dirs
    
    def has_expected_structure(self, company_dir: Path) -> bool:
        """Check if a directory has the expected structure for testing."""
        required_items = [
            company_dir / "pages",
            company_dir / "metadata.json",
            company_dir / "full_document.txt"
        ]
        
        return all(item.exists() for item in required_items)
    
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and record results."""
        self.results['total_tests'] += 1
        try:
            result = test_func()
            if result:
                self.results['passed_tests'] += 1
                self.results['test_details'].append({
                    'test': test_name,
                    'status': 'PASSED',
                    'message': 'Test passed successfully'
                })
                logger.info(f"✅ {test_name}: PASSED")
                return True
            else:
                self.results['failed_tests'] += 1
                self.results['test_details'].append({
                    'test': test_name,
                    'status': 'FAILED',
                    'message': 'Test failed'
                })
                logger.error(f"❌ {test_name}: FAILED")
                return False
        except Exception as e:
            self.results['failed_tests'] += 1
            self.results['test_details'].append({
                'test': test_name,
                'status': 'ERROR',
                'message': f"Test error: {str(e)}"
            })
            logger.error(f"❌ {test_name}: ERROR - {str(e)}")
            return False
    
    def test_directory_structure_exists(self) -> bool:
        """Test 1: Verify that the base directory structure exists."""
        if not self.base_dir.exists():
            logger.error(f"Base directory does not exist: {self.base_dir}")
            return False
        
        # Check for any document type directories
        doc_type_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]
        if not doc_type_dirs:
            logger.error("No document type directories found")
            return False
        
        logger.info(f"Found document type directories: {[d.name for d in doc_type_dirs]}")
        return True
    
    def test_company_directories_exist(self) -> bool:
        """Test 2: Verify that company-specific directories exist and are discoverable."""
        company_dirs = self.discover_all_testable_directories()
        
        if not company_dirs:
            logger.error("No testable company directories found")
            return False
        
        logger.info(f"Found {len(company_dirs)} testable company directories")
        return True
    
    def test_per_page_txt_files_exist(self) -> bool:
        """Test 3: Verify per-page .txt files exist for each PDF."""
        company_dirs = self.discover_all_testable_directories()
        
        if not company_dirs:
            logger.error("No company directories found")
            return False
        
        for company_dir in company_dirs:
            pages_dir = self.base_dir / company_dir / "pages"
            if not pages_dir.exists():
                logger.error(f"Missing pages directory: {pages_dir}")
                return False
            
            # Check for page text files
            txt_files = list(pages_dir.glob("*_page_*.txt"))
            if not txt_files:
                logger.error(f"No page text files found in: {pages_dir}")
                return False
            
            logger.info(f"Found {len(txt_files)} page text files in {company_dir}")
        
        return True
    
    def test_ocr_log_exists(self) -> bool:
        """Test 4: Verify OCR logs exist and contain OCR page information."""
        company_dirs = self.discover_all_testable_directories()
        
        if not company_dirs:
            logger.error("No company directories found")
            return False
        
        for company_dir in company_dirs:
            pages_dir = self.base_dir / company_dir / "pages"
            log_files = list(pages_dir.glob("*_extraction_log.json"))
            
            if not log_files:
                logger.error(f"No extraction log found in: {pages_dir}")
                return False
            
            # Check the most recent log file
            log_file = max(log_files, key=lambda x: x.stat().st_mtime)
            
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                
                # Verify OCR information exists
                if 'ocr_pages' not in log_data:
                    logger.error(f"Missing 'ocr_pages' in log: {log_file}")
                    return False
                
                ocr_pages = log_data['ocr_pages']
                logger.info(f"OCR pages in {company_dir}: {len(ocr_pages)} pages")
                
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {str(e)}")
                return False
        
        return True
    
    def test_word_bounding_boxes_exist(self) -> bool:
        """Test 5: Verify word bounding boxes are persisted."""
        company_dirs = self.discover_all_testable_directories()
        
        if not company_dirs:
            logger.error("No company directories found")
            return False
        
        for company_dir in company_dirs:
            pages_dir = self.base_dir / company_dir / "pages"
            word_files = list(pages_dir.glob("*_words.json"))
            
            if not word_files:
                logger.error(f"No word bounding box files found in: {pages_dir}")
                return False
            
            # Check at least one word file has valid data
            valid_word_file = False
            for word_file in word_files[:3]:  # Check first 3 files
                try:
                    with open(word_file, 'r', encoding='utf-8') as f:
                        word_data = json.load(f)
                    
                    if isinstance(word_data, list) and len(word_data) > 0:
                        # Check if it has expected word structure (pdfplumber uses x0,x1,y0,y1)
                        if 'text' in word_data[0] and 'x0' in word_data[0]:
                            valid_word_file = True
                            break
                
                except Exception as e:
                    logger.warning(f"Error reading word file {word_file}: {str(e)}")
                    continue
            
            if not valid_word_file:
                logger.error(f"No valid word bounding box data found in: {pages_dir}")
                return False
            
            logger.info(f"Found {len(word_files)} word bounding box files in {company_dir}")
        
        return True
    
    def test_metadata_files_exist(self) -> bool:
        """Test 6: Verify metadata files exist and contain expected information."""
        company_dirs = self.discover_all_testable_directories()
        
        if not company_dirs:
            logger.error("No company directories found")
            return False
        
        for company_dir in company_dirs:
            metadata_file = self.base_dir / company_dir / "metadata.json"
            
            if not metadata_file.exists():
                logger.error(f"Missing metadata file: {metadata_file}")
                return False
            
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Check required fields
                required_fields = ['document_info', 'extraction_stats', 'file_paths', 'page_details']
                for field in required_fields:
                    if field not in metadata:
                        logger.error(f"Missing field '{field}' in metadata: {metadata_file}")
                        return False
                
                # Check document_info structure
                doc_info = metadata['document_info']
                if 'type' not in doc_info or 'year' not in doc_info:
                    logger.error(f"Invalid document_info structure in: {metadata_file}")
                    return False
                
                logger.info(f"Metadata file valid for {company_dir}")
                
            except Exception as e:
                logger.error(f"Error reading metadata file {metadata_file}: {str(e)}")
                return False
        
        return True
    
    def test_full_document_files_exist(self) -> bool:
        """Test 7: Verify full document files exist."""
        company_dirs = self.discover_all_testable_directories()
        
        if not company_dirs:
            logger.error("No company directories found")
            return False
        
        for company_dir in company_dirs:
            company_path = self.base_dir / company_dir
            
            # Check for full document files
            txt_file = company_path / "full_document.txt"
            md_file = company_path / "full_document.md"
            
            if not txt_file.exists():
                logger.error(f"Missing full_document.txt: {txt_file}")
                return False
            
            if not md_file.exists():
                logger.error(f"Missing full_document.md: {md_file}")
                return False
            
            # Check file sizes are reasonable
            if txt_file.stat().st_size < self.expected_structure['min_file_size']:
                logger.error(f"Full document too small: {txt_file}")
                return False
            
            logger.info(f"Full document files exist for {company_dir}")
        
        return True
    
    def test_page_metadata_files_exist(self) -> bool:
        """Test 8: Verify page metadata files exist."""
        company_dirs = self.discover_all_testable_directories()
        
        if not company_dirs:
            logger.error("No company directories found")
            return False
        
        for company_dir in company_dirs:
            pages_dir = self.base_dir / company_dir / "pages"
            meta_files = list(pages_dir.glob("*_meta.json"))
            
            if not meta_files:
                logger.error(f"No page metadata files found in: {pages_dir}")
                return False
            
            # Check at least one metadata file has valid structure
            valid_meta_file = False
            for meta_file in meta_files[:3]:  # Check first 3 files
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta_data = json.load(f)
                    
                    if 'page_num' in meta_data and 'word_count' in meta_data:
                        valid_meta_file = True
                        break
                
                except Exception as e:
                    logger.warning(f"Error reading metadata file {meta_file}: {str(e)}")
                    continue
            
            if not valid_meta_file:
                logger.error(f"No valid page metadata found in: {pages_dir}")
                return False
            
            logger.info(f"Found {len(meta_files)} page metadata files in {company_dir}")
        
        return True
    
    def test_processing_log_exists(self) -> bool:
        """Test 9: Verify main processing log exists."""
        log_file = self.base_dir / "processing_log.json"
        
        if not log_file.exists():
            logger.error(f"Missing main processing log: {log_file}")
            return False
        
        # Check if file exists and has reasonable size (not empty)
        if log_file.stat().st_size < self.expected_structure['min_file_size']:
            logger.error(f"Processing log too small: {log_file}")
            return False
        
        logger.info(f"Processing log exists with size: {log_file.stat().st_size} bytes")
        return True
    
    def test_text_content_quality(self) -> bool:
        """Test 10: Verify text content quality."""
        company_dirs = self.discover_all_testable_directories()
        
        if not company_dirs:
            logger.error("No company directories found")
            return False
        
        for company_dir in company_dirs:
            company_path = self.base_dir / company_dir
            txt_file = company_path / "full_document.txt"
            
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check content quality
                if len(content.strip()) < self.expected_structure['min_file_size']:
                    logger.error(f"Text content too short in: {txt_file}")
                    return False
                
                # Check for common financial document keywords
                financial_keywords = self.expected_structure['financial_keywords']
                content_lower = content.lower()
                found_keywords = sum(1 for keyword in financial_keywords if keyword in content_lower)
                
                if found_keywords < 3:  # At least 3 financial keywords
                    logger.warning(f"Low financial keyword count in: {txt_file}")
                
                logger.info(f"Text content quality good for {company_dir}")
                
            except Exception as e:
                logger.error(f"Error reading text file {txt_file}: {str(e)}")
                return False
        
        return True
    
    def run_all_tests(self) -> Dict:
        """Run all validation tests."""
        logger.info("🚀 Starting dynamic text extraction pipeline validation...")
        logger.info("=" * 60)
        
        # First discover all directories
        company_dirs = self.discover_all_testable_directories()
        if not company_dirs:
            logger.error("No testable directories found. Exiting.")
            return self.results
        
        logger.info(f"Testing {len(company_dirs)} directories: {[str(d) for d in company_dirs]}")
        logger.info("=" * 60)
        
        # Define all tests
        tests = [
            ("Directory Structure Exists", self.test_directory_structure_exists),
            ("Company Directories Exist", self.test_company_directories_exist),
            ("Per-page TXT Files Exist", self.test_per_page_txt_files_exist),
            ("OCR Log Exists", self.test_ocr_log_exists),
            ("Word Bounding Boxes Exist", self.test_word_bounding_boxes_exist),
            ("Metadata Files Exist", self.test_metadata_files_exist),
            ("Full Document Files Exist", self.test_full_document_files_exist),
            ("Page Metadata Files Exist", self.test_page_metadata_files_exist),
            ("Processing Log Exists", self.test_processing_log_exists),
            ("Text Content Quality", self.test_text_content_quality)
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Print summary
        self.print_summary()
        return self.results
    
    def print_summary(self):
        """Print test summary."""
        logger.info("=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {self.results['total_tests']}")
        logger.info(f"Passed: {self.results['passed_tests']}")
        logger.info(f"Failed: {self.results['failed_tests']}")
        logger.info(f"Success Rate: {(self.results['passed_tests'] / self.results['total_tests'] * 100):.1f}%")
        
        if self.results['discovered_directories']:
            logger.info(f"\n📁 Discovered Directories ({len(self.results['discovered_directories'])}):")
            for dir_path in self.results['discovered_directories']:
                logger.info(f"  - {dir_path}")
        
        if self.results['failed_tests'] > 0:
            logger.info("\n❌ FAILED TESTS:")
            for test in self.results['test_details']:
                if test['status'] in ['FAILED', 'ERROR']:
                    logger.info(f"  - {test['test']}: {test['message']}")
        else:
            logger.info("\n🎉 ALL TESTS PASSED! Text extraction pipeline is working correctly.")


def main():
    """Main function to run the validation tests."""
    validator = TextExtractionValidator()
    results = validator.run_all_tests()
    
    # Exit with appropriate code
    if results['failed_tests'] > 0:
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    main()
