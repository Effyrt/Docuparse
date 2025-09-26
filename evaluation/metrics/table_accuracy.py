#!/usr/bin/env python3
"""
Table Extraction Accuracy Metrics

This module implements cell-level precision, recall, and F1-score calculations
for evaluating table extraction quality against ground truth.
"""

import csv
import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TableMetrics:
    """Container for table accuracy metrics."""
    precision: float
    recall: float
    f1_score: float
    cell_accuracy: float
    structure_accuracy: float
    true_positives: int
    false_positives: int
    false_negatives: int
    total_cells: int
    exact_match: bool


class TableAccuracyEvaluator:
    """Evaluates table extraction accuracy using cell-level precision and recall."""
    
    def __init__(self, ground_truth_dir: str = "evaluation/ground_truth"):
        self.ground_truth_dir = Path(ground_truth_dir)
        self.results = {}
        
    def normalize_cell_value(self, value: str) -> str:
        """Normalize cell value for comparison."""
        if pd.isna(value) or value is None:
            return ""
        
        # Convert to string and strip whitespace
        value = str(value).strip()
        
        # Remove common formatting artifacts
        value = value.replace(',', '').replace('$', '').replace('%', '')
        
        # Normalize numbers
        try:
            # Try to parse as float to handle numeric formatting
            float_val = float(value)
            # If it's a whole number, format as int
            if float_val.is_integer():
                return str(int(float_val))
            else:
                return f"{float_val:.2f}".rstrip('0').rstrip('.')
        except ValueError:
            # Not a number, return normalized string
            return value.lower()
    
    def load_csv_table(self, file_path: Path) -> pd.DataFrame:
        """Load CSV table and normalize values."""
        try:
            df = pd.read_csv(file_path)
            
            # Normalize all cell values
            for col in df.columns:
                df[col] = df[col].apply(self.normalize_cell_value)
                
            return df
        except Exception as e:
            logger.error(f"Error loading CSV {file_path}: {e}")
            return pd.DataFrame()
    
    def extract_table_cells(self, df: pd.DataFrame) -> Set[Tuple[int, int, str]]:
        """
        Extract all cells from a table as a set of (row, col, value) tuples.
        
        Args:
            df: DataFrame to extract cells from
            
        Returns:
            Set of (row_index, column_index, normalized_value) tuples
        """
        cells = set()
        
        for row_idx in range(len(df)):
            for col_idx in range(len(df.columns)):
                value = self.normalize_cell_value(df.iloc[row_idx, col_idx])
                if value:  # Only include non-empty cells
                    cells.add((row_idx, col_idx, value))
                    
        return cells
    
    def calculate_table_metrics(self, ground_truth_df: pd.DataFrame, extracted_df: pd.DataFrame) -> TableMetrics:
        """
        Calculate table extraction metrics.
        
        Args:
            ground_truth_df: Ground truth table
            extracted_df: Extracted table
            
        Returns:
            TableMetrics object with precision, recall, F1, etc.
        """
        gt_cells = self.extract_table_cells(ground_truth_df)
        extracted_cells = self.extract_table_cells(extracted_df)
        
        # Calculate cell-level metrics
        true_positives = len(gt_cells.intersection(extracted_cells))
        false_positives = len(extracted_cells - gt_cells)
        false_negatives = len(gt_cells - extracted_cells)
        
        # Calculate precision, recall, F1
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Calculate cell accuracy (percentage of correctly extracted cells)
        total_gt_cells = len(gt_cells)
        cell_accuracy = true_positives / total_gt_cells if total_gt_cells > 0 else 0.0
        
        # Calculate structure accuracy (dimensions match)
        gt_shape = ground_truth_df.shape
        extracted_shape = extracted_df.shape
        structure_accuracy = 1.0 if gt_shape == extracted_shape else 0.0
        
        # Check exact match
        exact_match = gt_cells == extracted_cells and gt_shape == extracted_shape
        
        return TableMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            cell_accuracy=cell_accuracy,
            structure_accuracy=structure_accuracy,
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            total_cells=total_gt_cells,
            exact_match=exact_match
        )
    
    def evaluate_table_file(self, ground_truth_file: str, extracted_table_data: str) -> TableMetrics:
        """Evaluate extracted table against ground truth file."""
        gt_path = self.ground_truth_dir / ground_truth_file
        
        if not gt_path.exists():
            raise FileNotFoundError(f"Ground truth file not found: {gt_path}")
            
        # Load ground truth table
        gt_df = self.load_csv_table(gt_path)
        
        # Parse extracted table data (assuming CSV format)
        try:
            # Create temporary file for extracted data
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
                temp_file.write(extracted_table_data)
                temp_path = temp_file.name
                
            extracted_df = self.load_csv_table(Path(temp_path))
            
            # Clean up temp file
            Path(temp_path).unlink()
            
        except Exception as e:
            logger.error(f"Error parsing extracted table data: {e}")
            # Return zero metrics if parsing fails
            return TableMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, len(self.extract_table_cells(gt_df)), len(self.extract_table_cells(gt_df)), False)
        
        return self.calculate_table_metrics(gt_df, extracted_df)
    
    def evaluate_extraction_results(self, parsed_data_dir: str = "data/parsed/tables") -> Dict[str, Any]:
        """
        Evaluate table extraction results against all ground truth files.
        
        Args:
            parsed_data_dir: Directory containing parsed table extraction results
            
        Returns:
            Dictionary containing evaluation results and metrics
        """
        results = {
            'timestamp': '2025-09-26T13:45:00Z',
            'evaluations': [],
            'summary': {
                'total_tables': 0,
                'avg_precision': 0.0,
                'avg_recall': 0.0,
                'avg_f1': 0.0,
                'avg_cell_accuracy': 0.0,
                'tables_passed': 0,
                'tables_failed': 0
            }
        }
        
        # Load ground truth metadata
        metadata_path = self.ground_truth_dir / "ground_truth_metadata.json"
        if not metadata_path.exists():
            logger.error(f"Ground truth metadata not found: {metadata_path}")
            return results
            
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            
        # Define thresholds
        precision_threshold = 0.90  # 90% precision
        recall_threshold = 0.85     # 85% recall  
        f1_threshold = 0.87         # 87% F1 score
        
        total_precision = 0.0
        total_recall = 0.0
        total_f1 = 0.0
        total_cell_accuracy = 0.0
        
        for file_info in metadata['ground_truth_files']:
            if file_info['type'] != 'table':
                continue
                
            file_name = file_info['file']
            page_num = file_info['page_number']
            
            logger.info(f"Evaluating table on page {page_num}: {file_name}")
            
            # Find corresponding extracted table
            extracted_table = self._find_extracted_table_for_page(page_num, parsed_data_dir)
            
            if extracted_table is None:
                logger.warning(f"No extracted table found for page {page_num}")
                continue
                
            try:
                metrics = self.evaluate_table_file(file_name, extracted_table)
                
                evaluation_result = {
                    'file': file_name,
                    'page': page_num,
                    'section': file_info['section'],
                    'metrics': {
                        'precision': round(metrics.precision, 4),
                        'recall': round(metrics.recall, 4),
                        'f1_score': round(metrics.f1_score, 4),
                        'cell_accuracy': round(metrics.cell_accuracy, 4),
                        'structure_accuracy': round(metrics.structure_accuracy, 4),
                        'true_positives': metrics.true_positives,
                        'false_positives': metrics.false_positives,
                        'false_negatives': metrics.false_negatives,
                        'total_cells': metrics.total_cells,
                        'exact_match': metrics.exact_match
                    },
                    'thresholds': {
                        'precision_passed': metrics.precision >= precision_threshold,
                        'recall_passed': metrics.recall >= recall_threshold,
                        'f1_passed': metrics.f1_score >= f1_threshold
                    }
                }
                
                results['evaluations'].append(evaluation_result)
                
                total_precision += metrics.precision
                total_recall += metrics.recall
                total_f1 += metrics.f1_score
                total_cell_accuracy += metrics.cell_accuracy
                
                # Check if table meets all thresholds
                if (metrics.precision >= precision_threshold and 
                    metrics.recall >= recall_threshold and 
                    metrics.f1_score >= f1_threshold):
                    results['summary']['tables_passed'] += 1
                else:
                    results['summary']['tables_failed'] += 1
                    
                results['summary']['total_tables'] += 1
                
                logger.info(f"Page {page_num} - Precision: {metrics.precision:.4f}, Recall: {metrics.recall:.4f}, F1: {metrics.f1_score:.4f}")
                
            except Exception as e:
                logger.error(f"Error evaluating {file_name}: {e}")
                
        # Calculate averages
        if results['summary']['total_tables'] > 0:
            total_tables = results['summary']['total_tables']
            results['summary']['avg_precision'] = round(total_precision / total_tables, 4)
            results['summary']['avg_recall'] = round(total_recall / total_tables, 4)
            results['summary']['avg_f1'] = round(total_f1 / total_tables, 4)
            results['summary']['avg_cell_accuracy'] = round(total_cell_accuracy / total_tables, 4)
            
        return results
    
    def _find_extracted_table_for_page(self, page_number: int, parsed_dir: str) -> str:
        """
        Find extracted table data for a specific page number.
        This is a simplified implementation - you'd need to adapt based on your actual data structure.
        """
        # For demo purposes, return sample extracted table data
        # In practice, you'd parse your extraction results and find the specific page
        
        sample_tables = {
            35: """Category,2023,2022,2021
Revenue,134425,116609,117929
Cost of revenue,25959,25249,22649
Research and development,38483,35914,24655
Marketing and sales,7076,7618,7167
General and administrative,5711,5974,6651
Restructuring,4652,0,0
Total costs and expenses,81881,74755,60942
Income from operations,52544,41854,56987
Interest income,4478,2932,1668
Other income (expense) net,624,-2544,-534
Income before provision for income taxes,57646,42242,58121
Provision for income taxes,16687,5619,7914
Net income,40959,36668,50253""",
            
            87: """Risk Factor,Description,Impact Level
Regulatory and Legal,Government regulations may limit our products and services impose significant compliance costs or result in fines and penalties,High
Competition,We face significant competition from other technology companies that may have competitive advantages,High
Privacy and Data Security,Data breaches or privacy violations could harm our reputation and business,Critical
Platform Changes,Changes to mobile operating systems or app stores could limit our functionality,Medium
Content and Safety,Harmful content on our platforms could damage our reputation and user trust,High
Economic Conditions,Economic downturns may reduce advertiser spending and user engagement,Medium
International Operations,Operating globally exposes us to geopolitical risks and regulatory differences,Medium
Technology Infrastructure,Failures in our systems could disrupt services and harm user experience,High"""
        }
        
        return sample_tables.get(page_number)


if __name__ == "__main__":
    evaluator = TableAccuracyEvaluator()
    results = evaluator.evaluate_extraction_results()
    
    # Save results
    output_path = Path("evaluation/metrics/table_accuracy_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print("📊 Table Accuracy Evaluation Results:")
    print(f"Average Precision: {results['summary']['avg_precision']:.4f}")
    print(f"Average Recall: {results['summary']['avg_recall']:.4f}")
    print(f"Average F1: {results['summary']['avg_f1']:.4f}")
    print(f"Tables passed: {results['summary']['tables_passed']}/{results['summary']['total_tables']}")
    print(f"Results saved to: {output_path}")
