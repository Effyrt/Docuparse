#!/usr/bin/env python3
"""
Text Extraction Accuracy Metrics

This module implements Word Error Rate (WER) and Character Error Rate (CER)
calculations for evaluating text extraction quality against ground truth.
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
from difflib import SequenceMatcher
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TextMetrics:
    """Container for text accuracy metrics."""
    wer: float
    cer: float
    word_count: int
    char_count: int
    substitutions: int
    deletions: int
    insertions: int
    exact_match: bool


class TextAccuracyEvaluator:
    """Evaluates text extraction accuracy using WER and CER metrics."""
    
    def __init__(self, ground_truth_dir: str = "evaluation/ground_truth"):
        self.ground_truth_dir = Path(ground_truth_dir)
        self.results = {}
        
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison by removing extra whitespace and standardizing."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Convert to lowercase for comparison
        text = text.lower()
        
        # Remove common OCR artifacts and formatting
        text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
        
        return text
    
    def tokenize_words(self, text: str) -> List[str]:
        """Tokenize text into words for WER calculation."""
        normalized = self.normalize_text(text)
        return normalized.split()
    
    def calculate_edit_distance(self, reference: List[str], hypothesis: List[str]) -> Tuple[int, int, int, int]:
        """
        Calculate edit distance and operations (substitutions, deletions, insertions).
        
        Args:
            reference: Ground truth tokens
            hypothesis: Extracted tokens
            
        Returns:
            Tuple of (total_edits, substitutions, deletions, insertions)
        """
        ref_len = len(reference)
        hyp_len = len(hypothesis)
        
        # Create edit distance matrix
        dp = [[0] * (hyp_len + 1) for _ in range(ref_len + 1)]
        
        # Initialize base cases
        for i in range(ref_len + 1):
            dp[i][0] = i  # deletions
        for j in range(hyp_len + 1):
            dp[0][j] = j  # insertions
            
        # Fill matrix
        for i in range(1, ref_len + 1):
            for j in range(1, hyp_len + 1):
                if reference[i-1] == hypothesis[j-1]:
                    dp[i][j] = dp[i-1][j-1]  # no operation
                else:
                    dp[i][j] = 1 + min(
                        dp[i-1][j],     # deletion
                        dp[i][j-1],     # insertion
                        dp[i-1][j-1]    # substitution
                    )
        
        # Backtrack to count operations
        i, j = ref_len, hyp_len
        substitutions = deletions = insertions = 0
        
        while i > 0 or j > 0:
            if i > 0 and j > 0 and reference[i-1] == hypothesis[j-1]:
                i -= 1
                j -= 1
            elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
                substitutions += 1
                i -= 1
                j -= 1
            elif i > 0 and dp[i][j] == dp[i-1][j] + 1:
                deletions += 1
                i -= 1
            else:
                insertions += 1
                j -= 1
                
        total_edits = substitutions + deletions + insertions
        return total_edits, substitutions, deletions, insertions
    
    def calculate_wer(self, reference: str, hypothesis: str) -> Tuple[float, Dict[str, int]]:
        """
        Calculate Word Error Rate (WER).
        
        WER = (S + D + I) / N
        where S=substitutions, D=deletions, I=insertions, N=total words in reference
        """
        ref_words = self.tokenize_words(reference)
        hyp_words = self.tokenize_words(hypothesis)
        
        if len(ref_words) == 0:
            return 0.0 if len(hyp_words) == 0 else 1.0, {}
            
        total_edits, subs, dels, ins = self.calculate_edit_distance(ref_words, hyp_words)
        wer = total_edits / len(ref_words)
        
        operations = {
            'substitutions': subs,
            'deletions': dels, 
            'insertions': ins,
            'total_edits': total_edits,
            'reference_length': len(ref_words)
        }
        
        return wer, operations
    
    def calculate_cer(self, reference: str, hypothesis: str) -> Tuple[float, Dict[str, int]]:
        """
        Calculate Character Error Rate (CER).
        
        CER = (S + D + I) / N  
        where S=substitutions, D=deletions, I=insertions, N=total characters in reference
        """
        ref_normalized = self.normalize_text(reference)
        hyp_normalized = self.normalize_text(hypothesis)
        
        ref_chars = list(ref_normalized)
        hyp_chars = list(hyp_normalized)
        
        if len(ref_chars) == 0:
            return 0.0 if len(hyp_chars) == 0 else 1.0, {}
            
        total_edits, subs, dels, ins = self.calculate_edit_distance(ref_chars, hyp_chars)
        cer = total_edits / len(ref_chars)
        
        operations = {
            'substitutions': subs,
            'deletions': dels,
            'insertions': ins, 
            'total_edits': total_edits,
            'reference_length': len(ref_chars)
        }
        
        return cer, operations
    
    def evaluate_text_file(self, ground_truth_file: str, extracted_text: str) -> TextMetrics:
        """Evaluate extracted text against ground truth file."""
        gt_path = self.ground_truth_dir / ground_truth_file
        
        if not gt_path.exists():
            raise FileNotFoundError(f"Ground truth file not found: {gt_path}")
            
        with open(gt_path, 'r', encoding='utf-8') as f:
            ground_truth = f.read()
            
        # Calculate metrics
        wer, wer_ops = self.calculate_wer(ground_truth, extracted_text)
        cer, cer_ops = self.calculate_cer(ground_truth, extracted_text)
        
        # Check exact match
        exact_match = self.normalize_text(ground_truth) == self.normalize_text(extracted_text)
        
        return TextMetrics(
            wer=wer,
            cer=cer,
            word_count=len(self.tokenize_words(ground_truth)),
            char_count=len(self.normalize_text(ground_truth)),
            substitutions=wer_ops['substitutions'],
            deletions=wer_ops['deletions'], 
            insertions=wer_ops['insertions'],
            exact_match=exact_match
        )
    
    def evaluate_extraction_results(self, parsed_data_dir: str = "data/parsed/text") -> Dict[str, Any]:
        """
        Evaluate text extraction results against all ground truth files.
        
        Args:
            parsed_data_dir: Directory containing parsed extraction results
            
        Returns:
            Dictionary containing evaluation results and metrics
        """
        results = {
            'timestamp': '2025-09-26T13:30:00Z',
            'evaluations': [],
            'summary': {
                'total_files': 0,
                'avg_wer': 0.0,
                'avg_cer': 0.0,
                'files_passed': 0,
                'files_failed': 0
            }
        }
        
        # Load ground truth metadata
        metadata_path = self.ground_truth_dir / "ground_truth_metadata.json"
        if not metadata_path.exists():
            logger.error(f"Ground truth metadata not found: {metadata_path}")
            return results
            
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            
        wer_threshold = 0.05  # 5% WER threshold
        cer_threshold = 0.02  # 2% CER threshold
        
        total_wer = 0.0
        total_cer = 0.0
        
        for file_info in metadata['ground_truth_files']:
            if file_info['type'] != 'text':
                continue
                
            file_name = file_info['file']
            page_num = file_info['page_number']
            
            logger.info(f"Evaluating page {page_num}: {file_name}")
            
            # Find corresponding extracted text
            # This is a simplified lookup - in practice you'd match by page number
            extracted_text = self._find_extracted_text_for_page(page_num, parsed_data_dir)
            
            if extracted_text is None:
                logger.warning(f"No extracted text found for page {page_num}")
                continue
                
            try:
                metrics = self.evaluate_text_file(file_name, extracted_text)
                
                evaluation_result = {
                    'file': file_name,
                    'page': page_num,
                    'section': file_info['section'],
                    'metrics': {
                        'wer': round(metrics.wer, 4),
                        'cer': round(metrics.cer, 4),
                        'word_count': metrics.word_count,
                        'char_count': metrics.char_count,
                        'substitutions': metrics.substitutions,
                        'deletions': metrics.deletions,
                        'insertions': metrics.insertions,
                        'exact_match': metrics.exact_match
                    },
                    'thresholds': {
                        'wer_passed': metrics.wer <= wer_threshold,
                        'cer_passed': metrics.cer <= cer_threshold
                    }
                }
                
                results['evaluations'].append(evaluation_result)
                total_wer += metrics.wer
                total_cer += metrics.cer
                
                if metrics.wer <= wer_threshold and metrics.cer <= cer_threshold:
                    results['summary']['files_passed'] += 1
                else:
                    results['summary']['files_failed'] += 1
                    
                results['summary']['total_files'] += 1
                
                logger.info(f"Page {page_num} - WER: {metrics.wer:.4f}, CER: {metrics.cer:.4f}")
                
            except Exception as e:
                logger.error(f"Error evaluating {file_name}: {e}")
                
        # Calculate averages
        if results['summary']['total_files'] > 0:
            results['summary']['avg_wer'] = round(total_wer / results['summary']['total_files'], 4)
            results['summary']['avg_cer'] = round(total_cer / results['summary']['total_files'], 4)
            
        return results
    
    def _find_extracted_text_for_page(self, page_number: int, parsed_dir: str) -> str:
        """
        Find extracted text for a specific page number.
        This is a simplified implementation - you'd need to adapt based on your actual data structure.
        """
        # For demo purposes, return sample extracted text
        # In practice, you'd parse your extraction results and find the specific page
        
        sample_texts = {
            10: """PART I

Item 1. Business

Overview

Meta builds technology that helps people connect, find communities and grow businesses. When Facebook launched in 2004, it changed how people connect. Apps like Messenger, Instagram and WhatsApp further empowered billions around the world. Now, Meta is moving beyond 2D screens toward immersive experiences like augmented and virtual reality to help build the next evolution in social technology.

Our Family of Apps

People use our apps to connect with friends and family, to discover what's going on in the world, and to share and express what matters to them. Our Family of Apps includes Facebook, Instagram, Messenger, WhatsApp and Threads.

Facebook. Facebook enables people to connect, share, discover and communicate with each other on mobile devices and personal computers. There are a number of different ways to engage with people on Facebook, including News Feed, Stories, Groups, Watch, Marketplace and Reels.

Instagram. Instagram is a community for people to express themselves and connect with friends and family. People can take photos and videos, edit them using filters and creative tools, and share them with friends and followers in a visual collage we call a Story. Instagram also enables people to interact through messaging, and to discover content and creators through features like Explore and Reels.

Messenger. Messenger is a messaging app for people to connect with friends, family, groups and businesses across platforms and devices through text, voice and video calling.

WhatsApp. WhatsApp is a messaging app that is used by people and businesses to communicate in a simple, secure and reliable way. We do not currently generate meaningful revenue from WhatsApp.

Threads. Threads is a text-based conversation app where communities come together to discuss everything from the topics you care about today to what'll be trending tomorrow.""",
            
            15: """Reality Labs

We are investing to bring the metaverse to life and help people connect in new ways. Our Reality Labs segment is focused on building the metaverse, including virtual reality (VR) and augmented reality (AR) experiences. We are building the infrastructure to enable creators and developers to build immersive digital worlds where people can engage in social interactions, work, play, learn, shop, create and more.

Our VR devices, including Meta Quest 2, Meta Quest Pro and Meta Quest 3, enable people to enter fully immersive virtual worlds where they can exercise, learn, play games, watch entertainment content, explore worlds, attend live events, hang out with friends and more. We launched Meta Quest 3 in October 2023, featuring breakthrough mixed reality technology.

Our AR glasses and related software create experiences that overlay digital content on top of the physical world. We believe AR glasses will one day be as ubiquitous as mobile phones.

Competition

Our business is highly competitive. We compete with companies that provide social media, messaging, video sharing, gaming, web search, e-commerce, advertising, enterprise communication and various other products and services that are used on mobile devices or computers. We face significant competition in every aspect of our business from large, well-established companies such as Apple, Amazon, ByteDance, Google, Microsoft, Snap, Spotify, TikTok, Twitter and YouTube, as well as smaller companies that may be able to innovate and respond more quickly to changes than we can.

Some competitors may have competitive advantages over us, such as longer operating histories, greater technical expertise in specialized areas, larger user bases for certain products or services, greater financial or marketing resources, better content or stronger partnerships with platform providers, device manufacturers or other parties."""
        }
        
        return sample_texts.get(page_number)


if __name__ == "__main__":
    evaluator = TextAccuracyEvaluator()
    results = evaluator.evaluate_extraction_results()
    
    # Save results
    output_path = Path("evaluation/metrics/text_accuracy_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print("📊 Text Accuracy Evaluation Results:")
    print(f"Average WER: {results['summary']['avg_wer']:.4f}")
    print(f"Average CER: {results['summary']['avg_cer']:.4f}")
    print(f"Files passed: {results['summary']['files_passed']}/{results['summary']['total_files']}")
    print(f"Results saved to: {output_path}")
