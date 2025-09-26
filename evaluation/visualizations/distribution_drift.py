#!/usr/bin/env python3
"""
Distribution Drift Analysis and Visualization

This module analyzes and visualizes distribution drift in extraction outputs,
including chunk lengths, numeric token ratios, and content characteristics.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DistributionDriftAnalyzer:
    """Analyzes distribution drift in document extraction outputs."""
    
    def __init__(self, output_dir: str = "evaluation/visualizations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
    def analyze_text_distributions(self, parsed_data_dir: str = "data/parsed/text") -> Dict[str, Any]:
        """
        Analyze text extraction distributions for drift detection.
        
        Args:
            parsed_data_dir: Directory containing parsed text results
            
        Returns:
            Dictionary with distribution statistics and drift metrics
        """
        logger.info("Analyzing text distribution characteristics...")
        
        # Collect text extraction statistics
        stats = {
            'chunk_lengths': [],
            'word_counts': [],
            'char_counts': [],
            'sentence_counts': [],
            'numeric_token_ratios': [],
            'capitalization_ratios': [],
            'punctuation_ratios': [],
            'avg_word_lengths': [],
            'line_counts': [],
            'paragraph_counts': []
        }
        
        # Sample data from ground truth and extracted text
        sample_texts = self._collect_sample_texts(parsed_data_dir)
        
        for text_content in sample_texts:
            if not text_content.strip():
                continue
                
            # Basic statistics
            words = text_content.split()
            chars = text_content
            sentences = re.split(r'[.!?]+', text_content)
            lines = text_content.split('\n')
            paragraphs = re.split(r'\n\s*\n', text_content)
            
            stats['chunk_lengths'].append(len(text_content))
            stats['word_counts'].append(len(words))
            stats['char_counts'].append(len(chars))
            stats['sentence_counts'].append(len([s for s in sentences if s.strip()]))
            stats['line_counts'].append(len(lines))
            stats['paragraph_counts'].append(len([p for p in paragraphs if p.strip()]))
            
            # Numeric token analysis
            if words:
                numeric_tokens = sum(1 for word in words if re.search(r'\d', word))
                stats['numeric_token_ratios'].append(numeric_tokens / len(words))
                
                # Capitalization analysis
                capital_words = sum(1 for word in words if word and word[0].isupper())
                stats['capitalization_ratios'].append(capital_words / len(words))
                
                # Average word length
                avg_word_len = sum(len(word) for word in words) / len(words)
                stats['avg_word_lengths'].append(avg_word_len)
            else:
                stats['numeric_token_ratios'].append(0)
                stats['capitalization_ratios'].append(0)
                stats['avg_word_lengths'].append(0)
                
            # Punctuation analysis
            if chars:
                punctuation_chars = sum(1 for char in chars if not char.isalnum() and not char.isspace())
                stats['punctuation_ratios'].append(punctuation_chars / len(chars))
            else:
                stats['punctuation_ratios'].append(0)
        
        # Convert to numpy arrays for analysis
        for key in stats:
            stats[key] = np.array(stats[key])
            
        # Calculate distribution statistics
        distribution_stats = {}
        for metric, values in stats.items():
            if len(values) > 0:
                distribution_stats[metric] = {
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values)),
                    'median': float(np.median(values)),
                    'q25': float(np.percentile(values, 25)),
                    'q75': float(np.percentile(values, 75)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'count': len(values)
                }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'type': 'text_distributions',
            'raw_data': {k: v.tolist() for k, v in stats.items()},
            'statistics': distribution_stats
        }
    
    def analyze_table_distributions(self, parsed_data_dir: str = "data/parsed/tables") -> Dict[str, Any]:
        """
        Analyze table extraction distributions for drift detection.
        
        Args:
            parsed_data_dir: Directory containing parsed table results
            
        Returns:
            Dictionary with table distribution statistics
        """
        logger.info("Analyzing table distribution characteristics...")
        
        stats = {
            'table_row_counts': [],
            'table_col_counts': [],
            'table_cell_counts': [],
            'numeric_cell_ratios': [],
            'empty_cell_ratios': [],
            'avg_cell_lengths': [],
            'table_densities': [],  # non-empty cells / total cells
            'header_confidence_scores': []
        }
        
        # Sample data from ground truth and extracted tables
        sample_tables = self._collect_sample_tables(parsed_data_dir)
        
        for table_data in sample_tables:
            if not table_data:
                continue
                
            # Parse table (assuming CSV format)
            try:
                lines = table_data.strip().split('\n')
                rows = [line.split(',') for line in lines]
                
                if not rows:
                    continue
                    
                row_count = len(rows)
                col_count = max(len(row) for row in rows) if rows else 0
                total_cells = row_count * col_count
                
                stats['table_row_counts'].append(row_count)
                stats['table_col_counts'].append(col_count)
                stats['table_cell_counts'].append(total_cells)
                
                # Analyze cell contents
                all_cells = [cell.strip() for row in rows for cell in row]
                non_empty_cells = [cell for cell in all_cells if cell]
                numeric_cells = [cell for cell in non_empty_cells if re.match(r'^-?\d+\.?\d*$', cell)]
                
                if total_cells > 0:
                    stats['numeric_cell_ratios'].append(len(numeric_cells) / total_cells)
                    stats['empty_cell_ratios'].append((total_cells - len(non_empty_cells)) / total_cells)
                    stats['table_densities'].append(len(non_empty_cells) / total_cells)
                else:
                    stats['numeric_cell_ratios'].append(0)
                    stats['empty_cell_ratios'].append(1)
                    stats['table_densities'].append(0)
                
                if non_empty_cells:
                    avg_cell_length = sum(len(cell) for cell in non_empty_cells) / len(non_empty_cells)
                    stats['avg_cell_lengths'].append(avg_cell_length)
                else:
                    stats['avg_cell_lengths'].append(0)
                
                # Header detection confidence (simple heuristic)
                if rows:
                    first_row = rows[0]
                    header_indicators = sum(1 for cell in first_row if 
                                          cell.strip() and 
                                          (cell.strip().replace(' ', '').isalpha() or 
                                           len(cell.strip()) > 3))
                    header_confidence = header_indicators / len(first_row) if first_row else 0
                    stats['header_confidence_scores'].append(header_confidence)
                else:
                    stats['header_confidence_scores'].append(0)
                    
            except Exception as e:
                logger.warning(f"Error parsing table data: {e}")
                continue
        
        # Convert to numpy arrays
        for key in stats:
            stats[key] = np.array(stats[key])
            
        # Calculate distribution statistics
        distribution_stats = {}
        for metric, values in stats.items():
            if len(values) > 0:
                distribution_stats[metric] = {
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values)),
                    'median': float(np.median(values)),
                    'q25': float(np.percentile(values, 25)),
                    'q75': float(np.percentile(values, 75)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'count': len(values)
                }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'type': 'table_distributions',
            'raw_data': {k: v.tolist() for k, v in stats.items()},
            'statistics': distribution_stats
        }
    
    def visualize_distributions(self, text_stats: Dict[str, Any], table_stats: Dict[str, Any]) -> None:
        """Create comprehensive visualization plots for distribution analysis."""
        logger.info("Creating distribution visualization plots...")
        
        # Create figure with subplots
        fig = plt.figure(figsize=(20, 16))
        
        # Text distribution plots
        self._plot_text_distributions(fig, text_stats)
        
        # Table distribution plots  
        self._plot_table_distributions(fig, table_stats, text_stats)
        
        # Save the comprehensive plot
        plt.tight_layout()
        output_path = self.output_dir / f"distribution_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Distribution plots saved to {output_path}")
        
        # Create individual focused plots
        self._create_focused_plots(text_stats, table_stats)
    
    def _plot_text_distributions(self, fig: plt.Figure, text_stats: Dict[str, Any]) -> None:
        """Plot text-specific distribution charts."""
        try:
            text_data = text_stats['raw_data']
        except Exception as e:
            logger.error(f"Error accessing text stats: {e}")
            return
        
        # Chunk length distribution
        ax1 = fig.add_subplot(3, 4, 1)
        ax1.hist(text_data['chunk_lengths'], bins=20, alpha=0.7, color='skyblue')
        ax1.set_title('Text Chunk Length Distribution')
        ax1.set_xlabel('Characters')
        ax1.set_ylabel('Frequency')
        
        # Word count distribution
        ax2 = fig.add_subplot(3, 4, 2)
        ax2.hist(text_data['word_counts'], bins=20, alpha=0.7, color='lightgreen')
        ax2.set_title('Word Count Distribution')
        ax2.set_xlabel('Words per chunk')
        ax2.set_ylabel('Frequency')
        
        # Numeric token ratio
        ax3 = fig.add_subplot(3, 4, 3)
        ax3.hist(text_data['numeric_token_ratios'], bins=15, alpha=0.7, color='orange')
        ax3.set_title('Numeric Token Ratio Distribution')
        ax3.set_xlabel('Ratio of numeric tokens')
        ax3.set_ylabel('Frequency')
        
        # Average word length
        ax4 = fig.add_subplot(3, 4, 4)
        ax4.hist(text_data['avg_word_lengths'], bins=15, alpha=0.7, color='pink')
        ax4.set_title('Average Word Length Distribution')
        ax4.set_xlabel('Average characters per word')
        ax4.set_ylabel('Frequency')
    
    def _plot_table_distributions(self, fig: plt.Figure, table_stats: Dict[str, Any], text_stats: Dict[str, Any] = None) -> None:
        """Plot table-specific distribution charts."""
        table_data = table_stats['raw_data']
        
        # Table dimensions
        ax5 = fig.add_subplot(3, 4, 5)
        ax5.scatter(table_data['table_row_counts'], table_data['table_col_counts'], alpha=0.6)
        ax5.set_title('Table Dimensions Distribution')
        ax5.set_xlabel('Rows')
        ax5.set_ylabel('Columns')
        
        # Cell count distribution
        ax6 = fig.add_subplot(3, 4, 6)
        ax6.hist(table_data['table_cell_counts'], bins=15, alpha=0.7, color='purple')
        ax6.set_title('Table Cell Count Distribution')
        ax6.set_xlabel('Total cells')
        ax6.set_ylabel('Frequency')
        
        # Numeric cell ratio
        ax7 = fig.add_subplot(3, 4, 7)
        ax7.hist(table_data['numeric_cell_ratios'], bins=15, alpha=0.7, color='red')
        ax7.set_title('Numeric Cell Ratio Distribution')
        ax7.set_xlabel('Ratio of numeric cells')
        ax7.set_ylabel('Frequency')
        
        # Table density
        ax8 = fig.add_subplot(3, 4, 8)
        ax8.hist(table_data['table_densities'], bins=15, alpha=0.7, color='brown')
        ax8.set_title('Table Density Distribution')
        ax8.set_xlabel('Density (non-empty cells ratio)')
        ax8.set_ylabel('Frequency')
        
        # Combined analysis plots
        ax9 = fig.add_subplot(3, 4, 9)
        try:
            ax9.boxplot([text_stats['raw_data']['chunk_lengths'], table_data['table_cell_counts']], 
                       tick_labels=['Text Chunks', 'Table Cells'])
            ax9.set_title('Content Size Comparison')
            ax9.set_ylabel('Size metric')
        except Exception as e:
            ax9.text(0.5, 0.5, f'Plot error: {str(e)[:30]}...', 
                    transform=ax9.transAxes, ha='center', va='center')
            ax9.set_title('Content Size Comparison (Error)')
        
        # Quality indicators
        ax10 = fig.add_subplot(3, 4, 10)
        quality_metrics = {
            'Table Density': np.mean(table_data['table_densities']),
            'Table Header Conf.': np.mean(table_data['header_confidence_scores'])
        }
        
        # Add text metrics if available
        if text_stats is not None:
            quality_metrics.update({
                'Text Capitalization': np.mean(text_stats['raw_data']['capitalization_ratios']),
                'Text Punctuation': np.mean(text_stats['raw_data']['punctuation_ratios'])
            })
        ax10.bar(quality_metrics.keys(), quality_metrics.values(), alpha=0.7)
        ax10.set_title('Quality Indicators')
        ax10.set_ylabel('Average Score')
        ax10.tick_params(axis='x', rotation=45)
        
        # Distribution drift indicators
        ax11 = fig.add_subplot(3, 4, 11)
        drift_metrics = [
            np.std(table_data['table_cell_counts']) / np.mean(table_data['table_cell_counts']),
            np.std(table_data['numeric_cell_ratios']) / (np.mean(table_data['numeric_cell_ratios']) + 0.01)
        ]
        drift_labels = ['Table Size CV', 'Table Numeric CV']
        
        # Add text metrics if available
        if text_stats is not None:
            drift_metrics.insert(0, np.std(text_stats['raw_data']['chunk_lengths']) / np.mean(text_stats['raw_data']['chunk_lengths']))
            drift_metrics.insert(1, np.std(text_stats['raw_data']['numeric_token_ratios']) / (np.mean(text_stats['raw_data']['numeric_token_ratios']) + 0.01))
            drift_labels = ['Text Length CV', 'Text Numeric CV'] + drift_labels
        ax11.bar(drift_labels, drift_metrics, alpha=0.7, color='coral')
        ax11.set_title('Coefficient of Variation (Drift Indicators)')
        ax11.set_ylabel('CV Score')
        ax11.tick_params(axis='x', rotation=45)
        
        # Summary statistics
        ax12 = fig.add_subplot(3, 4, 12)
        summary_parts = [
            f"Table Analysis Summary:",
            f"• Tables analyzed: {len(table_data['table_cell_counts'])}",
            f"• Avg table size: {np.mean(table_data['table_cell_counts']):.1f} cells",
            f"• Avg density: {np.mean(table_data['table_densities']):.3f}"
        ]
        
        if text_stats is not None:
            summary_parts.insert(0, f"Text Analysis Summary:")
            summary_parts.insert(1, f"• Chunks analyzed: {len(text_stats['raw_data']['chunk_lengths'])}")
            summary_parts.insert(2, f"• Avg chunk length: {np.mean(text_stats['raw_data']['chunk_lengths']):.0f} chars")
            summary_parts.insert(3, f"• Avg numeric ratio: {np.mean(text_stats['raw_data']['numeric_token_ratios']):.3f}")
            summary_parts.insert(4, "")
            
        summary_text = "\n".join(summary_parts)
        ax12.text(0.05, 0.95, summary_text, transform=ax12.transAxes, 
                 verticalalignment='top', fontfamily='monospace', fontsize=8)
        ax12.set_title('Analysis Summary')
        ax12.axis('off')
    
    def _create_focused_plots(self, text_stats: Dict[str, Any], table_stats: Dict[str, Any]) -> None:
        """Create individual focused plots for specific metrics."""
        
        # Text chunk length drift plot
        plt.figure(figsize=(10, 6))
        plt.hist(text_stats['raw_data']['chunk_lengths'], bins=30, alpha=0.7, density=True)
        plt.axvline(np.mean(text_stats['raw_data']['chunk_lengths']), color='red', linestyle='--', label='Mean')
        plt.axvline(np.median(text_stats['raw_data']['chunk_lengths']), color='green', linestyle='--', label='Median')
        plt.title('Text Chunk Length Distribution - Drift Analysis')
        plt.xlabel('Chunk Length (characters)')
        plt.ylabel('Density')
        plt.legend()
        plt.savefig(self.output_dir / 'text_chunk_length_drift.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Numeric token ratio analysis
        plt.figure(figsize=(10, 6))
        plt.hist(text_stats['raw_data']['numeric_token_ratios'], bins=20, alpha=0.7, density=True)
        plt.axvline(np.mean(text_stats['raw_data']['numeric_token_ratios']), color='red', linestyle='--', label='Mean')
        plt.title('Numeric Token Ratio Distribution - Content Drift Analysis')
        plt.xlabel('Numeric Token Ratio')
        plt.ylabel('Density')
        plt.legend()
        plt.savefig(self.output_dir / 'numeric_token_drift.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Table structure analysis
        plt.figure(figsize=(12, 8))
        plt.subplot(2, 2, 1)
        plt.scatter(table_stats['raw_data']['table_row_counts'], table_stats['raw_data']['table_col_counts'], alpha=0.6)
        plt.xlabel('Rows')
        plt.ylabel('Columns')
        plt.title('Table Structure Distribution')
        
        plt.subplot(2, 2, 2)
        plt.hist(table_stats['raw_data']['table_densities'], bins=15, alpha=0.7)
        plt.xlabel('Table Density')
        plt.ylabel('Frequency')
        plt.title('Table Density Distribution')
        
        plt.subplot(2, 2, 3)
        plt.hist(table_stats['raw_data']['numeric_cell_ratios'], bins=15, alpha=0.7)
        plt.xlabel('Numeric Cell Ratio')
        plt.ylabel('Frequency')
        plt.title('Numeric Content Distribution')
        
        plt.subplot(2, 2, 4)
        plt.boxplot([table_stats['raw_data']['table_row_counts'], 
                    table_stats['raw_data']['table_col_counts']], 
                   tick_labels=['Rows', 'Columns'])
        plt.ylabel('Count')
        plt.title('Table Dimension Summary')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'table_structure_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _collect_sample_texts(self, parsed_dir: str) -> List[str]:
        """Collect sample text content for analysis."""
        # For demo purposes, return sample texts from ground truth
        sample_texts = []
        
        ground_truth_dir = Path("evaluation/ground_truth")
        for text_file in ground_truth_dir.glob("*_text.txt"):
            with open(text_file, 'r', encoding='utf-8') as f:
                sample_texts.append(f.read())
        
        # Add some synthetic variations to demonstrate drift detection
        if sample_texts:
            base_text = sample_texts[0]
            
            # Simulate different extraction qualities
            variations = [
                base_text,  # Perfect extraction
                base_text.replace('.', '. '),  # Extra spaces
                base_text.replace('\n', ' '),  # Line breaks removed
                ' '.join(base_text.split()[:len(base_text.split())//2]),  # Truncated
                base_text + ' ' + base_text[:100],  # Duplicated content
            ]
            sample_texts.extend(variations)
        
        return sample_texts
    
    def _collect_sample_tables(self, parsed_dir: str) -> List[str]:
        """Collect sample table content for analysis."""
        sample_tables = []
        
        ground_truth_dir = Path("evaluation/ground_truth")
        for table_file in ground_truth_dir.glob("*_table.csv"):
            with open(table_file, 'r', encoding='utf-8') as f:
                sample_tables.append(f.read())
        
        return sample_tables
    
    def save_drift_analysis(self, text_stats: Dict[str, Any], table_stats: Dict[str, Any]) -> None:
        """Save drift analysis results to JSON file."""
        analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'text_analysis': text_stats,
            'table_analysis': table_stats,
            'drift_indicators': {
                'text_length_cv': float(np.std(text_stats['raw_data']['chunk_lengths']) / np.mean(text_stats['raw_data']['chunk_lengths'])),
                'text_numeric_cv': float(np.std(text_stats['raw_data']['numeric_token_ratios']) / (np.mean(text_stats['raw_data']['numeric_token_ratios']) + 0.01)),
                'table_size_cv': float(np.std(table_stats['raw_data']['table_cell_counts']) / np.mean(table_stats['raw_data']['table_cell_counts'])),
                'table_density_cv': float(np.std(table_stats['raw_data']['table_densities']) / np.mean(table_stats['raw_data']['table_densities']))
            }
        }
        
        output_file = self.output_dir / 'drift_analysis_results.json'
        with open(output_file, 'w') as f:
            json.dump(analysis_results, f, indent=2)
            
        logger.info(f"Drift analysis results saved to {output_file}")


if __name__ == "__main__":
    analyzer = DistributionDriftAnalyzer()
    
    # Analyze distributions
    text_stats = analyzer.analyze_text_distributions()
    table_stats = analyzer.analyze_table_distributions()
    
    # Create visualizations
    analyzer.visualize_distributions(text_stats, table_stats)
    
    # Save results
    analyzer.save_drift_analysis(text_stats, table_stats)
    
    print("📊 Distribution Drift Analysis Complete!")
    print(f"Text chunks analyzed: {len(text_stats['raw_data']['chunk_lengths'])}")
    print(f"Tables analyzed: {len(table_stats['raw_data']['table_cell_counts'])}")
    print(f"Visualizations saved to: {analyzer.output_dir}")
    print(f"Key drift indicators:")
    print(f"  - Text length CV: {np.std(text_stats['raw_data']['chunk_lengths']) / np.mean(text_stats['raw_data']['chunk_lengths']):.3f}")
    print(f"  - Table size CV: {np.std(table_stats['raw_data']['table_cell_counts']) / np.mean(table_stats['raw_data']['table_cell_counts']):.3f}")
