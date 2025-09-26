#!/usr/bin/env python3
"""
DVC Metrics Tracker for Extraction Quality

This module integrates with DVC to track extraction metrics over time
and detect regressions when code changes degrade performance.
"""

import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from .text_accuracy import TextAccuracyEvaluator
from .table_accuracy import TableAccuracyEvaluator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DVCMetricsTracker:
    """Tracks extraction metrics for DVC integration and regression detection."""
    
    def __init__(self, metrics_dir: str = "evaluation/metrics"):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # DVC metrics file paths
        self.dvc_metrics_file = Path("metrics.json")
        self.history_file = self.metrics_dir / "metrics_history.json"
        
    def run_full_evaluation(self) -> Dict[str, Any]:
        """Run complete evaluation and generate metrics for DVC tracking."""
        logger.info("Running full extraction accuracy evaluation...")
        
        # Initialize evaluators
        text_evaluator = TextAccuracyEvaluator()
        table_evaluator = TableAccuracyEvaluator()
        
        # Run evaluations
        text_results = text_evaluator.evaluate_extraction_results()
        table_results = table_evaluator.evaluate_extraction_results()
        
        # Combine results
        combined_metrics = self._combine_evaluation_results(text_results, table_results)
        
        # Save for DVC
        self._save_dvc_metrics(combined_metrics)
        
        # Update history
        self._update_metrics_history(combined_metrics)
        
        logger.info("Evaluation complete. Metrics saved for DVC tracking.")
        return combined_metrics
    
    def _combine_evaluation_results(self, text_results: Dict[str, Any], table_results: Dict[str, Any]) -> Dict[str, Any]:
        """Combine text and table evaluation results into DVC-compatible format."""
        timestamp = datetime.now().isoformat()
        
        combined = {
            "timestamp": timestamp,
            "text_extraction": {
                "avg_wer": text_results['summary']['avg_wer'],
                "avg_cer": text_results['summary']['avg_cer'],
                "files_evaluated": text_results['summary']['total_files'],
                "files_passed": text_results['summary']['files_passed'],
                "pass_rate": text_results['summary']['files_passed'] / max(text_results['summary']['total_files'], 1)
            },
            "table_extraction": {
                "avg_precision": table_results['summary']['avg_precision'],
                "avg_recall": table_results['summary']['avg_recall'],
                "avg_f1": table_results['summary']['avg_f1'],
                "avg_cell_accuracy": table_results['summary']['avg_cell_accuracy'],
                "tables_evaluated": table_results['summary']['total_tables'],
                "tables_passed": table_results['summary']['tables_passed'],
                "pass_rate": table_results['summary']['tables_passed'] / max(table_results['summary']['total_tables'], 1)
            },
            "overall": {
                "total_evaluations": text_results['summary']['total_files'] + table_results['summary']['total_tables'],
                "total_passed": text_results['summary']['files_passed'] + table_results['summary']['tables_passed'],
                "overall_pass_rate": (text_results['summary']['files_passed'] + table_results['summary']['tables_passed']) / 
                                   max(text_results['summary']['total_files'] + table_results['summary']['total_tables'], 1)
            },
            "detailed_results": {
                "text_evaluations": text_results['evaluations'],
                "table_evaluations": table_results['evaluations']
            }
        }
        
        return combined
    
    def _save_dvc_metrics(self, metrics: Dict[str, Any]) -> None:
        """Save metrics in DVC-compatible format for tracking."""
        # Create DVC metrics format (flat structure for easier plotting)
        dvc_metrics = {
            # Text metrics
            "text_avg_wer": metrics['text_extraction']['avg_wer'],
            "text_avg_cer": metrics['text_extraction']['avg_cer'],
            "text_pass_rate": metrics['text_extraction']['pass_rate'],
            
            # Table metrics  
            "table_avg_precision": metrics['table_extraction']['avg_precision'],
            "table_avg_recall": metrics['table_extraction']['avg_recall'],
            "table_avg_f1": metrics['table_extraction']['avg_f1'],
            "table_pass_rate": metrics['table_extraction']['pass_rate'],
            
            # Overall metrics
            "overall_pass_rate": metrics['overall']['overall_pass_rate'],
            "total_evaluations": metrics['overall']['total_evaluations'],
            
            # Thresholds for reference
            "thresholds": {
                "wer_threshold": 0.05,
                "cer_threshold": 0.02,
                "precision_threshold": 0.90,
                "recall_threshold": 0.85,
                "f1_threshold": 0.87
            }
        }
        
        with open(self.dvc_metrics_file, 'w') as f:
            json.dump(dvc_metrics, f, indent=2)
            
        logger.info(f"DVC metrics saved to {self.dvc_metrics_file}")
    
    def _update_metrics_history(self, metrics: Dict[str, Any]) -> None:
        """Update historical metrics for regression detection."""
        history = []
        
        # Load existing history
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        
        # Add current metrics
        history.append({
            "timestamp": metrics['timestamp'],
            "text_avg_wer": metrics['text_extraction']['avg_wer'],
            "text_avg_cer": metrics['text_extraction']['avg_cer'],
            "text_pass_rate": metrics['text_extraction']['pass_rate'],
            "table_avg_precision": metrics['table_extraction']['avg_precision'],
            "table_avg_recall": metrics['table_extraction']['avg_recall'],
            "table_avg_f1": metrics['table_extraction']['avg_f1'],
            "table_pass_rate": metrics['table_extraction']['pass_rate'],
            "overall_pass_rate": metrics['overall']['overall_pass_rate']
        })
        
        # Keep only last 100 entries to avoid file growth
        history = history[-100:]
        
        # Save updated history
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
            
        logger.info(f"Metrics history updated: {len(history)} entries")
    
    def detect_regression(self, tolerance: float = 0.05) -> Dict[str, Any]:
        """
        Detect metric regressions by comparing current metrics to historical baseline.
        
        Args:
            tolerance: Acceptable degradation threshold (e.g., 0.05 = 5% degradation)
            
        Returns:
            Dictionary with regression detection results
        """
        if not self.history_file.exists() or not self.dvc_metrics_file.exists():
            return {"status": "insufficient_data", "message": "Need historical data for regression detection"}
        
        # Load current and historical metrics
        with open(self.dvc_metrics_file, 'r') as f:
            current_metrics = json.load(f)
            
        with open(self.history_file, 'r') as f:
            history = json.load(f)
            
        if len(history) < 2:
            return {"status": "insufficient_history", "message": "Need at least 2 historical points"}
        
        # Calculate baseline (average of last 5 runs, excluding current)
        baseline_entries = history[-6:-1] if len(history) >= 6 else history[:-1]
        
        def avg_metric(metric_name):
            values = [entry[metric_name] for entry in baseline_entries if metric_name in entry]
            return sum(values) / len(values) if values else 0
        
        baseline = {
            "text_avg_wer": avg_metric("text_avg_wer"),
            "text_avg_cer": avg_metric("text_avg_cer"),
            "text_pass_rate": avg_metric("text_pass_rate"),
            "table_avg_precision": avg_metric("table_avg_precision"),
            "table_avg_recall": avg_metric("table_avg_recall"),
            "table_avg_f1": avg_metric("table_avg_f1"),
            "table_pass_rate": avg_metric("table_pass_rate"),
            "overall_pass_rate": avg_metric("overall_pass_rate")
        }
        
        # Detect regressions
        regressions = []
        warnings = []
        
        # For error rates (WER, CER), higher is worse
        if current_metrics["text_avg_wer"] > baseline["text_avg_wer"] * (1 + tolerance):
            regressions.append({
                "metric": "text_avg_wer",
                "current": current_metrics["text_avg_wer"],
                "baseline": baseline["text_avg_wer"],
                "degradation": ((current_metrics["text_avg_wer"] / baseline["text_avg_wer"]) - 1) * 100
            })
        
        if current_metrics["text_avg_cer"] > baseline["text_avg_cer"] * (1 + tolerance):
            regressions.append({
                "metric": "text_avg_cer", 
                "current": current_metrics["text_avg_cer"],
                "baseline": baseline["text_avg_cer"],
                "degradation": ((current_metrics["text_avg_cer"] / baseline["text_avg_cer"]) - 1) * 100
            })
        
        # For quality metrics (precision, recall, F1, pass rates), lower is worse
        quality_metrics = ["table_avg_precision", "table_avg_recall", "table_avg_f1", "text_pass_rate", "table_pass_rate", "overall_pass_rate"]
        
        for metric in quality_metrics:
            if current_metrics[metric] < baseline[metric] * (1 - tolerance):
                regressions.append({
                    "metric": metric,
                    "current": current_metrics[metric],
                    "baseline": baseline[metric],
                    "degradation": ((baseline[metric] / current_metrics[metric]) - 1) * 100
                })
        
        # Generate smaller warnings for changes within tolerance
        warning_tolerance = tolerance / 2  # Half the regression tolerance
        
        for metric in ["text_avg_wer", "text_avg_cer"]:
            if (current_metrics[metric] > baseline[metric] * (1 + warning_tolerance) and 
                current_metrics[metric] <= baseline[metric] * (1 + tolerance)):
                warnings.append(f"{metric} increased by {((current_metrics[metric] / baseline[metric]) - 1) * 100:.1f}%")
        
        for metric in quality_metrics:
            if (current_metrics[metric] < baseline[metric] * (1 - warning_tolerance) and
                current_metrics[metric] >= baseline[metric] * (1 - tolerance)):
                warnings.append(f"{metric} decreased by {((baseline[metric] / current_metrics[metric]) - 1) * 100:.1f}%")
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "status": "regression_detected" if regressions else "no_regression",
            "regressions": regressions,
            "warnings": warnings,
            "baseline": baseline,
            "current": {k: v for k, v in current_metrics.items() if not k == "thresholds"},
            "tolerance": tolerance * 100,  # Convert to percentage
            "summary": {
                "total_regressions": len(regressions),
                "total_warnings": len(warnings),
                "baseline_runs": len(baseline_entries)
            }
        }
        
        return result
    
    def update_dvc_config(self) -> None:
        """Update dvc.yaml with evaluation stage and metrics configuration."""
        dvc_config_path = Path("dvc.yaml")
        
        if not dvc_config_path.exists():
            logger.error("dvc.yaml not found")
            return
            
        with open(dvc_config_path, 'r') as f:
            dvc_config = yaml.safe_load(f)
        
        # Add evaluation stage
        if 'stages' not in dvc_config:
            dvc_config['stages'] = {}
            
        dvc_config['stages']['evaluate'] = {
            'cmd': 'python evaluation/metrics/dvc_metrics_tracker.py',
            'deps': [
                'evaluation/ground_truth/',
                'evaluation/metrics/text_accuracy.py',
                'evaluation/metrics/table_accuracy.py',
                'evaluation/metrics/dvc_metrics_tracker.py',
                'data/parsed/text/',
                'data/parsed/tables/'
            ],
            'metrics': [
                'metrics.json'
            ],
            'outs': [
                'evaluation/metrics/text_accuracy_results.json',
                'evaluation/metrics/table_accuracy_results.json',
                'evaluation/metrics/metrics_history.json'
            ]
        }
        
        # Add metrics for plotting
        if 'metrics' not in dvc_config:
            dvc_config['metrics'] = []
            
        dvc_config['metrics'].append('metrics.json')
        
        # Add plots for metrics visualization
        if 'plots' not in dvc_config:
            dvc_config['plots'] = []
            
        dvc_config['plots'].extend([
            {
                'metrics.json': {
                    'x': 'timestamp',
                    'y': ['text_avg_wer', 'text_avg_cer'],
                    'title': 'Text Extraction Error Rates Over Time'
                }
            },
            {
                'metrics.json': {
                    'x': 'timestamp', 
                    'y': ['table_avg_precision', 'table_avg_recall', 'table_avg_f1'],
                    'title': 'Table Extraction Quality Metrics Over Time'
                }
            },
            {
                'metrics.json': {
                    'x': 'timestamp',
                    'y': ['overall_pass_rate'],
                    'title': 'Overall Extraction Pass Rate Over Time'
                }
            }
        ])
        
        # Save updated config
        with open(dvc_config_path, 'w') as f:
            yaml.dump(dvc_config, f, default_flow_style=False, sort_keys=False)
            
        logger.info("DVC configuration updated with evaluation stage and metrics")


if __name__ == "__main__":
    tracker = DVCMetricsTracker()
    
    # Run evaluation and save metrics
    results = tracker.run_full_evaluation()
    
    # Check for regressions
    regression_check = tracker.detect_regression()
    
    print("📊 Evaluation Complete!")
    print(f"Overall pass rate: {results['overall']['overall_pass_rate']:.2%}")
    print(f"Text WER: {results['text_extraction']['avg_wer']:.4f}")
    print(f"Table F1: {results['table_extraction']['avg_f1']:.4f}")
    
    if regression_check['status'] == 'regression_detected':
        print(f"\n⚠️  REGRESSION DETECTED: {len(regression_check['regressions'])} metrics degraded")
        for reg in regression_check['regressions']:
            print(f"  - {reg['metric']}: {reg['degradation']:.1f}% worse")
    elif regression_check['status'] == 'no_regression':
        print(f"\n✅ No regressions detected")
        if regression_check['warnings']:
            print(f"⚠️  {len(regression_check['warnings'])} warnings:")
            for warning in regression_check['warnings']:
                print(f"  - {warning}")
    else:
        print(f"\n📊 {regression_check['message']}")
        
    # Update DVC config
    tracker.update_dvc_config()
    print("\n🔧 DVC configuration updated with evaluation stage")
