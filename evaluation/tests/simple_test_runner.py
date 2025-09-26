#!/usr/bin/env python3
"""
Simple Test Runner for Extraction Accuracy (without pytest dependency)

This script runs basic threshold tests to verify the evaluation system works.
"""

import sys
from pathlib import Path

# Add evaluation modules to path
sys.path.append(str(Path(__file__).parent.parent))

from metrics.text_accuracy import TextAccuracyEvaluator
from metrics.table_accuracy import TableAccuracyEvaluator


def test_text_thresholds():
    """Test that text metrics meet thresholds."""
    print("🧪 Testing text extraction thresholds...")
    
    evaluator = TextAccuracyEvaluator()
    results = evaluator.evaluate_extraction_results()
    
    WER_THRESHOLD = 0.05
    CER_THRESHOLD = 0.02
    
    avg_wer = results['summary']['avg_wer']
    avg_cer = results['summary']['avg_cer']
    
    print(f"   Average WER: {avg_wer:.4f} (threshold: {WER_THRESHOLD})")
    print(f"   Average CER: {avg_cer:.4f} (threshold: {CER_THRESHOLD})")
    
    wer_pass = avg_wer <= WER_THRESHOLD
    cer_pass = avg_cer <= CER_THRESHOLD
    
    print(f"   WER Test: {'✅ PASS' if wer_pass else '❌ FAIL'}")
    print(f"   CER Test: {'✅ PASS' if cer_pass else '❌ FAIL'}")
    
    return wer_pass and cer_pass


def test_table_thresholds():
    """Test that table metrics meet thresholds."""
    print("🧪 Testing table extraction thresholds...")
    
    evaluator = TableAccuracyEvaluator()
    results = evaluator.evaluate_extraction_results()
    
    PRECISION_THRESHOLD = 0.90
    RECALL_THRESHOLD = 0.85
    F1_THRESHOLD = 0.87
    
    avg_precision = results['summary']['avg_precision']
    avg_recall = results['summary']['avg_recall']
    avg_f1 = results['summary']['avg_f1']
    
    print(f"   Average Precision: {avg_precision:.4f} (threshold: {PRECISION_THRESHOLD})")
    print(f"   Average Recall: {avg_recall:.4f} (threshold: {RECALL_THRESHOLD})")
    print(f"   Average F1: {avg_f1:.4f} (threshold: {F1_THRESHOLD})")
    
    precision_pass = avg_precision >= PRECISION_THRESHOLD
    recall_pass = avg_recall >= RECALL_THRESHOLD
    f1_pass = avg_f1 >= F1_THRESHOLD
    
    print(f"   Precision Test: {'✅ PASS' if precision_pass else '❌ FAIL'}")
    print(f"   Recall Test: {'✅ PASS' if recall_pass else '❌ FAIL'}")
    print(f"   F1 Test: {'✅ PASS' if f1_pass else '❌ FAIL'}")
    
    return precision_pass and recall_pass and f1_pass


def test_regression_detection():
    """Test basic regression detection functionality."""
    print("🧪 Testing regression detection...")
    
    try:
        # Import and run DVC tracker
        from metrics.dvc_metrics_tracker import DVCMetricsTracker
        tracker = DVCMetricsTracker()
        
        # Run evaluation
        tracker.run_full_evaluation()
        
        # Check regression detection
        regression_results = tracker.detect_regression()
        
        print(f"   Regression Status: {regression_results['status']}")
        print(f"   Baseline Runs: {regression_results['summary']['baseline_runs']}")
        
        # Test passes if no errors occurred
        return True
        
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Running Extraction Accuracy Tests")
    print("=" * 50)
    
    test_results = {
        'text_thresholds': test_text_thresholds(),
        'table_thresholds': test_table_thresholds(),
        'regression_detection': test_regression_detection()
    }
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Extraction quality meets thresholds.")
        return 0
    else:
        print("⚠️  Some tests failed. Check extraction quality.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
