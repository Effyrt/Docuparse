#!/usr/bin/env python3
"""
Unit Tests for Extraction Accuracy

This module contains unit tests that assert extraction metrics stay above defined thresholds
and can detect regressions when extraction quality degrades.
"""

import pytest
import json
import sys
from pathlib import Path

# Add evaluation modules to path
sys.path.append(str(Path(__file__).parent.parent))

from metrics.text_accuracy import TextAccuracyEvaluator, TextMetrics
from metrics.table_accuracy import TableAccuracyEvaluator, TableMetrics


class TestTextExtractionAccuracy:
    """Test cases for text extraction accuracy metrics."""
    
    @pytest.fixture
    def text_evaluator(self):
        """Create text accuracy evaluator instance."""
        return TextAccuracyEvaluator()
    
    @pytest.fixture
    def sample_text_results(self, text_evaluator):
        """Get sample text evaluation results."""
        return text_evaluator.evaluate_extraction_results()
    
    def test_wer_threshold(self, sample_text_results):
        """Test that Word Error Rate stays below 5% threshold."""
        avg_wer = sample_text_results['summary']['avg_wer']
        WER_THRESHOLD = 0.05  # 5%
        
        assert avg_wer <= WER_THRESHOLD, f"Average WER {avg_wer:.4f} exceeds threshold {WER_THRESHOLD}"
        
        # Check individual files
        for evaluation in sample_text_results['evaluations']:
            wer = evaluation['metrics']['wer']
            file_name = evaluation['file']
            assert wer <= WER_THRESHOLD, f"WER {wer:.4f} in {file_name} exceeds threshold {WER_THRESHOLD}"
    
    def test_cer_threshold(self, sample_text_results):
        """Test that Character Error Rate stays below 2% threshold."""
        avg_cer = sample_text_results['summary']['avg_cer']
        CER_THRESHOLD = 0.02  # 2%
        
        assert avg_cer <= CER_THRESHOLD, f"Average CER {avg_cer:.4f} exceeds threshold {CER_THRESHOLD}"
        
        # Check individual files
        for evaluation in sample_text_results['evaluations']:
            cer = evaluation['metrics']['cer']
            file_name = evaluation['file']
            assert cer <= CER_THRESHOLD, f"CER {cer:.4f} in {file_name} exceeds threshold {CER_THRESHOLD}"
    
    def test_text_extraction_coverage(self, sample_text_results):
        """Test that we have evaluation results for expected files."""
        MIN_FILES = 2  # Should have at least 2 text files evaluated
        actual_files = len(sample_text_results['evaluations'])
        
        assert actual_files >= MIN_FILES, f"Only {actual_files} text files evaluated, expected >= {MIN_FILES}"
    
    def test_text_metrics_range(self, sample_text_results):
        """Test that all metrics are within valid ranges."""
        for evaluation in sample_text_results['evaluations']:
            metrics = evaluation['metrics']
            file_name = evaluation['file']
            
            # WER and CER should be between 0 and 1
            assert 0.0 <= metrics['wer'] <= 1.0, f"WER out of range in {file_name}"
            assert 0.0 <= metrics['cer'] <= 1.0, f"CER out of range in {file_name}"
            
            # Counts should be non-negative integers
            assert metrics['word_count'] >= 0, f"Negative word count in {file_name}"
            assert metrics['char_count'] >= 0, f"Negative char count in {file_name}"
            assert metrics['substitutions'] >= 0, f"Negative substitutions in {file_name}"
            assert metrics['deletions'] >= 0, f"Negative deletions in {file_name}"
            assert metrics['insertions'] >= 0, f"Negative insertions in {file_name}"
    
    def test_text_quality_regression(self, text_evaluator):
        """Test that intentionally degraded text is detected as poor quality."""
        # Load ground truth
        gt_file = "meta_2024_10k_page_10_text.txt"
        with open(f"evaluation/ground_truth/{gt_file}", 'r') as f:
            ground_truth = f.read()
        
        # Create degraded version with intentional errors
        degraded_text = ground_truth.replace("Meta", "Melta").replace("Facebook", "Facebok").replace("Instagram", "Instgram")
        
        metrics = text_evaluator.evaluate_text_file(gt_file, degraded_text)
        
        # Should detect significant degradation
        assert metrics.wer > 0.01, f"Failed to detect WER degradation: {metrics.wer}"
        assert metrics.cer > 0.005, f"Failed to detect CER degradation: {metrics.cer}"
        assert not metrics.exact_match, "Should not be exact match for degraded text"


class TestTableExtractionAccuracy:
    """Test cases for table extraction accuracy metrics."""
    
    @pytest.fixture
    def table_evaluator(self):
        """Create table accuracy evaluator instance."""
        return TableAccuracyEvaluator()
    
    @pytest.fixture
    def sample_table_results(self, table_evaluator):
        """Get sample table evaluation results."""
        return table_evaluator.evaluate_extraction_results()
    
    def test_precision_threshold(self, sample_table_results):
        """Test that table precision stays above 90% threshold."""
        avg_precision = sample_table_results['summary']['avg_precision']
        PRECISION_THRESHOLD = 0.90  # 90%
        
        assert avg_precision >= PRECISION_THRESHOLD, f"Average precision {avg_precision:.4f} below threshold {PRECISION_THRESHOLD}"
        
        # Check individual tables
        for evaluation in sample_table_results['evaluations']:
            precision = evaluation['metrics']['precision']
            file_name = evaluation['file']
            assert precision >= PRECISION_THRESHOLD, f"Precision {precision:.4f} in {file_name} below threshold {PRECISION_THRESHOLD}"
    
    def test_recall_threshold(self, sample_table_results):
        """Test that table recall stays above 85% threshold."""
        avg_recall = sample_table_results['summary']['avg_recall']
        RECALL_THRESHOLD = 0.85  # 85%
        
        assert avg_recall >= RECALL_THRESHOLD, f"Average recall {avg_recall:.4f} below threshold {RECALL_THRESHOLD}"
        
        # Check individual tables
        for evaluation in sample_table_results['evaluations']:
            recall = evaluation['metrics']['recall']
            file_name = evaluation['file']
            assert recall >= RECALL_THRESHOLD, f"Recall {recall:.4f} in {file_name} below threshold {RECALL_THRESHOLD}"
    
    def test_f1_threshold(self, sample_table_results):
        """Test that table F1 score stays above 87% threshold."""
        avg_f1 = sample_table_results['summary']['avg_f1']
        F1_THRESHOLD = 0.87  # 87%
        
        assert avg_f1 >= F1_THRESHOLD, f"Average F1 {avg_f1:.4f} below threshold {F1_THRESHOLD}"
        
        # Check individual tables
        for evaluation in sample_table_results['evaluations']:
            f1 = evaluation['metrics']['f1_score']
            file_name = evaluation['file']
            assert f1 >= F1_THRESHOLD, f"F1 {f1:.4f} in {file_name} below threshold {F1_THRESHOLD}"
    
    def test_table_extraction_coverage(self, sample_table_results):
        """Test that we have evaluation results for expected tables."""
        MIN_TABLES = 2  # Should have at least 2 tables evaluated
        actual_tables = len(sample_table_results['evaluations'])
        
        assert actual_tables >= MIN_TABLES, f"Only {actual_tables} tables evaluated, expected >= {MIN_TABLES}"
    
    def test_table_metrics_range(self, sample_table_results):
        """Test that all table metrics are within valid ranges."""
        for evaluation in sample_table_results['evaluations']:
            metrics = evaluation['metrics']
            file_name = evaluation['file']
            
            # Precision, recall, F1 should be between 0 and 1
            assert 0.0 <= metrics['precision'] <= 1.0, f"Precision out of range in {file_name}"
            assert 0.0 <= metrics['recall'] <= 1.0, f"Recall out of range in {file_name}"
            assert 0.0 <= metrics['f1_score'] <= 1.0, f"F1 score out of range in {file_name}"
            assert 0.0 <= metrics['cell_accuracy'] <= 1.0, f"Cell accuracy out of range in {file_name}"
            assert 0.0 <= metrics['structure_accuracy'] <= 1.0, f"Structure accuracy out of range in {file_name}"
            
            # Counts should be non-negative integers
            assert metrics['true_positives'] >= 0, f"Negative TP in {file_name}"
            assert metrics['false_positives'] >= 0, f"Negative FP in {file_name}"
            assert metrics['false_negatives'] >= 0, f"Negative FN in {file_name}"
            assert metrics['total_cells'] >= 0, f"Negative total cells in {file_name}"
    
    def test_table_quality_regression(self, table_evaluator):
        """Test that intentionally degraded table is detected as poor quality."""
        # Create degraded table data with missing cells and wrong values
        degraded_table = """Category,2023,2022,2021
Revenue,134000,116000,117000
Cost of revenue,26000,25000,23000
Research and development,38000,36000,25000
Marketing and sales,7000,7600,7200
General and administrative,5700,6000,6700
Total costs and expenses,81000,75000,61000
Income from operations,52000,42000,57000
Interest income,4500,3000,1700
Income before provision for income taxes,57000,42000,58000
Provision for income taxes,16700,5600,7900
Net income,40000,37000,50000"""
        
        gt_file = "meta_2024_10k_page_35_table.csv"
        metrics = table_evaluator.evaluate_table_file(gt_file, degraded_table)
        
        # Should detect degradation
        assert metrics.precision < 1.0, f"Failed to detect precision degradation: {metrics.precision}"
        assert metrics.recall < 1.0, f"Failed to detect recall degradation: {metrics.recall}"
        assert not metrics.exact_match, "Should not be exact match for degraded table"


class TestCombinedAccuracy:
    """Test cases for combined extraction accuracy."""
    
    def test_overall_extraction_quality(self):
        """Test overall extraction system quality."""
        text_evaluator = TextAccuracyEvaluator()
        table_evaluator = TableAccuracyEvaluator()
        
        text_results = text_evaluator.evaluate_extraction_results()
        table_results = table_evaluator.evaluate_extraction_results()
        
        # Overall quality thresholds
        MIN_PASS_RATE = 0.8  # 80% of files/tables should pass individual thresholds
        
        # Check text pass rate
        text_total = text_results['summary']['total_files']
        text_passed = text_results['summary']['files_passed']
        text_pass_rate = text_passed / text_total if text_total > 0 else 0
        
        assert text_pass_rate >= MIN_PASS_RATE, f"Text pass rate {text_pass_rate:.2f} below {MIN_PASS_RATE}"
        
        # Check table pass rate
        table_total = table_results['summary']['total_tables']
        table_passed = table_results['summary']['tables_passed']
        table_pass_rate = table_passed / table_total if table_total > 0 else 0
        
        assert table_pass_rate >= MIN_PASS_RATE, f"Table pass rate {table_pass_rate:.2f} below {MIN_PASS_RATE}"
    
    def test_no_catastrophic_failures(self):
        """Test that there are no catastrophic failures (metrics near 0)."""
        text_evaluator = TextAccuracyEvaluator()
        table_evaluator = TableAccuracyEvaluator()
        
        text_results = text_evaluator.evaluate_extraction_results()
        table_results = table_evaluator.evaluate_extraction_results()
        
        CATASTROPHIC_THRESHOLD = 0.1  # 10% - anything below this is catastrophic
        
        # Check text metrics
        for evaluation in text_results['evaluations']:
            metrics = evaluation['metrics']
            file_name = evaluation['file']
            
            # WER above 90% means almost no correct words
            assert metrics['wer'] < 0.9, f"Catastrophic WER {metrics['wer']} in {file_name}"
            
            # CER above 90% means almost no correct characters  
            assert metrics['cer'] < 0.9, f"Catastrophic CER {metrics['cer']} in {file_name}"
        
        # Check table metrics
        for evaluation in table_results['evaluations']:
            metrics = evaluation['metrics']
            file_name = evaluation['file']
            
            # Precision/recall below 10% indicates catastrophic failure
            assert metrics['precision'] > CATASTROPHIC_THRESHOLD, f"Catastrophic precision {metrics['precision']} in {file_name}"
            assert metrics['recall'] > CATASTROPHIC_THRESHOLD, f"Catastrophic recall {metrics['recall']} in {file_name}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
