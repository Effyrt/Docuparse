#!/usr/bin/env python3
"""
Comprehensive Extraction Evaluation Runner

This script runs the complete evaluation suite and generates a comprehensive
accuracy report with all metrics, visualizations, and regression analysis.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add evaluation modules to path
sys.path.append(str(Path(__file__).parent))

from metrics.text_accuracy import TextAccuracyEvaluator
from metrics.table_accuracy import TableAccuracyEvaluator
from metrics.dvc_metrics_tracker import DVCMetricsTracker
from visualizations.distribution_drift import DistributionDriftAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComprehensiveEvaluationRunner:
    """Runs complete evaluation suite and generates accuracy report."""
    
    def __init__(self, output_dir: str = "evaluation"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def run_complete_evaluation(self) -> Dict[str, Any]:
        """Run the complete evaluation suite."""
        logger.info("🚀 Starting comprehensive extraction evaluation...")
        
        results = {
            'evaluation_info': {
                'timestamp': datetime.now().isoformat(),
                'evaluation_id': f"eval_{self.timestamp}",
                'version': "1.0.0"
            },
            'text_accuracy': {},
            'table_accuracy': {},
            'distribution_analysis': {},
            'dvc_metrics': {},
            'regression_analysis': {},
            'summary': {}
        }
        
        try:
            # 1. Text Accuracy Evaluation
            logger.info("📝 Running text accuracy evaluation...")
            text_evaluator = TextAccuracyEvaluator()
            results['text_accuracy'] = text_evaluator.evaluate_extraction_results()
            logger.info(f"✅ Text evaluation complete: {results['text_accuracy']['summary']['total_files']} files analyzed")
            
            # 2. Table Accuracy Evaluation
            logger.info("📊 Running table accuracy evaluation...")
            table_evaluator = TableAccuracyEvaluator()
            results['table_accuracy'] = table_evaluator.evaluate_extraction_results()
            logger.info(f"✅ Table evaluation complete: {results['table_accuracy']['summary']['total_tables']} tables analyzed")
            
            # 3. Distribution Drift Analysis
            logger.info("📈 Running distribution drift analysis...")
            drift_analyzer = DistributionDriftAnalyzer()
            text_distributions = drift_analyzer.analyze_text_distributions()
            table_distributions = drift_analyzer.analyze_table_distributions()
            
            # Create visualizations
            drift_analyzer.visualize_distributions(text_distributions, table_distributions)
            drift_analyzer.save_drift_analysis(text_distributions, table_distributions)
            
            results['distribution_analysis'] = {
                'text_distributions': text_distributions,
                'table_distributions': table_distributions
            }
            logger.info("✅ Distribution analysis complete with visualizations")
            
            # 4. DVC Metrics Tracking
            logger.info("📋 Running DVC metrics tracking...")
            dvc_tracker = DVCMetricsTracker()
            dvc_metrics = dvc_tracker.run_full_evaluation()
            results['dvc_metrics'] = dvc_metrics
            
            # 5. Regression Detection
            logger.info("🔍 Running regression detection...")
            regression_results = dvc_tracker.detect_regression()
            results['regression_analysis'] = regression_results
            logger.info(f"✅ Regression analysis complete: {regression_results['status']}")
            
            # 6. Generate Summary
            logger.info("📑 Generating evaluation summary...")
            results['summary'] = self._generate_summary(results)
            
        except Exception as e:
            logger.error(f"❌ Evaluation failed: {e}")
            results['error'] = str(e)
            # Create minimal summary for error case
            results['summary'] = {
                'overall_status': 'error',
                'error_message': str(e),
                'quality_assessment': {'overall_quality': 'unknown'},
                'metrics_summary': {'combined_metrics': {'overall_pass_rate': 0}},
                'recommendations': ['Fix evaluation error before proceeding'],
                'alerts': [{'type': 'system', 'severity': 'critical', 'message': f'Evaluation failed: {e}'}]
            }
            
        return results
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive evaluation summary."""
        summary = {
            'overall_status': 'success',
            'evaluation_timestamp': results['evaluation_info']['timestamp'],
            'metrics_summary': {},
            'quality_assessment': {},
            'recommendations': [],
            'alerts': []
        }
        
        try:
            # Extract key metrics
            text_summary = results['text_accuracy']['summary']
            table_summary = results['table_accuracy']['summary']
            regression = results['regression_analysis']
            
            # Overall metrics
            summary['metrics_summary'] = {
                'text_metrics': {
                    'avg_wer': text_summary['avg_wer'],
                    'avg_cer': text_summary['avg_cer'],
                    'files_passed': text_summary['files_passed'],
                    'total_files': text_summary['total_files'],
                    'pass_rate': text_summary['files_passed'] / max(text_summary['total_files'], 1)
                },
                'table_metrics': {
                    'avg_precision': table_summary['avg_precision'],
                    'avg_recall': table_summary['avg_recall'],
                    'avg_f1': table_summary['avg_f1'],
                    'tables_passed': table_summary['tables_passed'],
                    'total_tables': table_summary['total_tables'],
                    'pass_rate': table_summary['tables_passed'] / max(table_summary['total_tables'], 1)
                },
                'combined_metrics': {
                    'total_evaluations': text_summary['total_files'] + table_summary['total_tables'],
                    'total_passed': text_summary['files_passed'] + table_summary['tables_passed'],
                    'overall_pass_rate': (text_summary['files_passed'] + table_summary['tables_passed']) / 
                                       max(text_summary['total_files'] + table_summary['total_tables'], 1)
                }
            }
            
            # Quality assessment
            overall_pass_rate = summary['metrics_summary']['combined_metrics']['overall_pass_rate']
            avg_wer = text_summary['avg_wer']
            avg_f1 = table_summary['avg_f1']
            
            if overall_pass_rate >= 0.9 and avg_wer <= 0.03 and avg_f1 >= 0.9:
                quality_level = "excellent"
            elif overall_pass_rate >= 0.8 and avg_wer <= 0.05 and avg_f1 >= 0.85:
                quality_level = "good"
            elif overall_pass_rate >= 0.7 and avg_wer <= 0.08 and avg_f1 >= 0.8:
                quality_level = "fair"
            else:
                quality_level = "poor"
                
            summary['quality_assessment'] = {
                'overall_quality': quality_level,
                'text_quality': 'good' if avg_wer <= 0.05 else 'needs_improvement',
                'table_quality': 'good' if avg_f1 >= 0.87 else 'needs_improvement',
                'stability': 'stable' if regression['status'] == 'no_regression' else 'unstable'
            }
            
            # Generate recommendations
            if avg_wer > 0.05:
                summary['recommendations'].append("Consider improving OCR quality or text preprocessing")
            
            if avg_f1 < 0.87:
                summary['recommendations'].append("Table extraction accuracy needs improvement - review table detection algorithms")
                
            if overall_pass_rate < 0.8:
                summary['recommendations'].append("Overall extraction quality is below target - comprehensive pipeline review needed")
                
            if regression['status'] == 'regression_detected':
                summary['recommendations'].append("Performance regression detected - investigate recent code changes")
                
            # Generate alerts
            if regression['status'] == 'regression_detected':
                summary['alerts'].append({
                    'type': 'regression',
                    'severity': 'high',
                    'message': f"Performance regression detected in {len(regression['regressions'])} metrics"
                })
                
            if avg_wer > 0.1:
                summary['alerts'].append({
                    'type': 'quality',
                    'severity': 'critical',
                    'message': f"Text extraction WER ({avg_wer:.3f}) exceeds critical threshold"
                })
                
            if avg_f1 < 0.7:
                summary['alerts'].append({
                    'type': 'quality',
                    'severity': 'critical',
                    'message': f"Table extraction F1 ({avg_f1:.3f}) below critical threshold"
                })
                
            if overall_pass_rate < 0.5:
                summary['alerts'].append({
                    'type': 'system',
                    'severity': 'critical',
                    'message': f"Overall pass rate ({overall_pass_rate:.1%}) indicates system failure"
                })
                
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            summary['overall_status'] = 'error'
            summary['error'] = str(e)
            
        return summary
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive markdown report."""
        report_content = f"""# Extraction Accuracy Evaluation Report

**Generated:** {results['evaluation_info']['timestamp']}  
**Evaluation ID:** {results['evaluation_info']['evaluation_id']}  
**Version:** {results['evaluation_info']['version']}

## 🎯 Executive Summary

**Overall Quality:** {results['summary']['quality_assessment']['overall_quality'].title()}  
**Overall Pass Rate:** {results['summary']['metrics_summary']['combined_metrics']['overall_pass_rate']:.1%}  
**System Status:** {results['summary']['quality_assessment']['stability'].title()}

### Key Metrics
- **Text WER:** {results['summary']['metrics_summary']['text_metrics']['avg_wer']:.4f} (target: < 0.05)
- **Text CER:** {results['summary']['metrics_summary']['text_metrics']['avg_cer']:.4f} (target: < 0.02)
- **Table Precision:** {results['summary']['metrics_summary']['table_metrics']['avg_precision']:.4f} (target: > 0.90)
- **Table Recall:** {results['summary']['metrics_summary']['table_metrics']['avg_recall']:.4f} (target: > 0.85)
- **Table F1:** {results['summary']['metrics_summary']['table_metrics']['avg_f1']:.4f} (target: > 0.87)

## 📊 Detailed Results

### Text Extraction Analysis
- **Files Evaluated:** {results['text_accuracy']['summary']['total_files']}
- **Files Passed:** {results['text_accuracy']['summary']['files_passed']}
- **Pass Rate:** {results['summary']['metrics_summary']['text_metrics']['pass_rate']:.1%}

#### Individual File Results:
"""
        
        # Add text evaluation details
        for eval_result in results['text_accuracy']['evaluations']:
            status = "✅ PASS" if eval_result['thresholds']['wer_passed'] and eval_result['thresholds']['cer_passed'] else "❌ FAIL"
            report_content += f"""
- **{eval_result['file']}** (Page {eval_result['page']}) - {status}
  - WER: {eval_result['metrics']['wer']:.4f}
  - CER: {eval_result['metrics']['cer']:.4f}
  - Words: {eval_result['metrics']['word_count']}
"""
        
        report_content += """
### Table Extraction Analysis
"""
        report_content += f"- **Tables Evaluated:** {results['table_accuracy']['summary']['total_tables']}\n"
        report_content += f"- **Tables Passed:** {results['table_accuracy']['summary']['tables_passed']}\n"
        report_content += f"- **Pass Rate:** {results['summary']['metrics_summary']['table_metrics']['pass_rate']:.1%}\n\n"
        
        report_content += "#### Individual Table Results:\n"
        
        # Add table evaluation details
        for eval_result in results['table_accuracy']['evaluations']:
            status = "✅ PASS" if all(eval_result['thresholds'].values()) else "❌ FAIL"
            report_content += f"""
- **{eval_result['file']}** (Page {eval_result['page']}) - {status}
  - Precision: {eval_result['metrics']['precision']:.4f}
  - Recall: {eval_result['metrics']['recall']:.4f}
  - F1: {eval_result['metrics']['f1_score']:.4f}
  - Cells: {eval_result['metrics']['total_cells']}
"""
        
        # Add regression analysis
        regression = results['regression_analysis']
        report_content += f"""
## 🔍 Regression Analysis

**Status:** {regression['status'].replace('_', ' ').title()}  
**Baseline Runs:** {regression['summary']['baseline_runs']}  
**Tolerance:** {regression['tolerance']:.1f}%

"""
        
        if regression['regressions']:
            report_content += "### ⚠️ Regressions Detected:\n"
            for reg in regression['regressions']:
                report_content += f"- **{reg['metric']}:** {reg['degradation']:.1f}% worse (current: {reg['current']:.4f}, baseline: {reg['baseline']:.4f})\n"
        else:
            report_content += "### ✅ No Regressions Detected\n"
            
        if regression['warnings']:
            report_content += "\n### ⚠️ Warnings:\n"
            for warning in regression['warnings']:
                report_content += f"- {warning}\n"
        
        # Add recommendations and alerts
        if results['summary']['recommendations']:
            report_content += "\n## 💡 Recommendations\n"
            for rec in results['summary']['recommendations']:
                report_content += f"- {rec}\n"
                
        if results['summary']['alerts']:
            report_content += "\n## 🚨 Alerts\n"
            for alert in results['summary']['alerts']:
                severity_icon = "🔴" if alert['severity'] == 'critical' else "🟡"
                report_content += f"- {severity_icon} **{alert['type'].title()}:** {alert['message']}\n"
        
        report_content += f"""
## 📈 Distribution Analysis

Distribution drift analysis has been completed with visualizations saved to `evaluation/visualizations/`.

### Key Distribution Metrics:
- **Text Chunks Analyzed:** {len(results['distribution_analysis']['text_distributions']['raw_data']['chunk_lengths'])}
- **Tables Analyzed:** {len(results['distribution_analysis']['table_distributions']['raw_data']['table_cell_counts'])}

### Drift Indicators:
- **Text Length CV:** {results['distribution_analysis']['text_distributions']['statistics']['chunk_lengths']['std'] / results['distribution_analysis']['text_distributions']['statistics']['chunk_lengths']['mean']:.3f}
- **Table Size CV:** {results['distribution_analysis']['table_distributions']['statistics']['table_cell_counts']['std'] / results['distribution_analysis']['table_distributions']['statistics']['table_cell_counts']['mean']:.3f}

## 🔧 Technical Details

### Evaluation Configuration
- **Ground Truth Files:** 4 (2 text, 2 tables)
- **Evaluation Method:** WER/CER for text, Precision/Recall/F1 for tables
- **DVC Metrics Tracking:** Enabled
- **Regression Detection:** Enabled (5% tolerance)

### File Locations
- **Ground Truth:** `evaluation/ground_truth/`
- **Metrics Results:** `evaluation/metrics/`
- **Visualizations:** `evaluation/visualizations/`
- **DVC Metrics:** `metrics.json`

---
*Report generated automatically by the Docuparse evaluation system.*
"""
        
        return report_content
    
    def save_results(self, results: Dict[str, Any]) -> None:
        """Save evaluation results and generate report."""
        # Save full results as JSON
        results_file = self.output_dir / f"evaluation_results_{self.timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"📄 Full results saved to {results_file}")
        
        # Generate and save markdown report
        report_content = self.generate_report(results)
        report_file = self.output_dir / f"accuracy_report_{self.timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        logger.info(f"📋 Report saved to {report_file}")
        
        # Save summary for quick reference
        summary_file = self.output_dir / "latest_evaluation_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(results['summary'], f, indent=2)
        logger.info(f"📊 Summary saved to {summary_file}")


if __name__ == "__main__":
    runner = ComprehensiveEvaluationRunner()
    
    # Run complete evaluation
    results = runner.run_complete_evaluation()
    
    # Save results and generate report
    runner.save_results(results)
    
    # Print summary
    summary = results['summary']
    print("\n" + "="*60)
    print("📊 EXTRACTION ACCURACY EVALUATION COMPLETE")
    print("="*60)
    print(f"Overall Quality: {summary['quality_assessment']['overall_quality'].upper()}")
    print(f"Overall Pass Rate: {summary['metrics_summary']['combined_metrics']['overall_pass_rate']:.1%}")
    print(f"Text WER: {summary['metrics_summary']['text_metrics']['avg_wer']:.4f}")
    print(f"Table F1: {summary['metrics_summary']['table_metrics']['avg_f1']:.4f}")
    
    if summary['alerts']:
        print(f"\n🚨 {len(summary['alerts'])} Alert(s):")
        for alert in summary['alerts']:
            print(f"  - {alert['message']}")
    
    if summary['recommendations']:
        print(f"\n💡 {len(summary['recommendations'])} Recommendation(s):")
        for rec in summary['recommendations'][:3]:  # Show top 3
            print(f"  - {rec}")
    
    print(f"\n📋 Detailed report: evaluation/accuracy_report_{runner.timestamp}.md")
    print("="*60)
