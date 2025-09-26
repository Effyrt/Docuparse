#!/usr/bin/env python3
"""
XBRL Cross-Verification System

Single file that:
1. Downloads XBRL files using SEC EDGAR API
2. Parses XBRL to extract financial data
3. Cross-verifies with PDF table extraction results
4. Reports matches and mismatches
"""

import os
import json
import logging
import requests
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import re
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class XBRLCrossVerification:
    """Complete XBRL download, parsing, and cross-verification system."""
    
    def __init__(self, output_dir: str = "data/xbrl_validation"):
        """Initialize the XBRL cross-verification system."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # SEC API base URL
        self.sec_api_base = "https://data.sec.gov/api/xbrl/companyfacts"
        self.edgar_base = "https://www.sec.gov/Archives/edgar/data"
        
        # Common headers for SEC requests
        self.headers = {
            'User-Agent': 'DocuParse XBRL Validator hemanth.rayudu@example.com'
        }
        
        # Company information
        self.companies = {
            "META": {
                "cik": "1326801",
                "ticker": "META",
                "name": "Meta Platforms Inc"
            }
        }
        
        # XBRL namespace mappings
        self.xbrl_namespaces = {
            'xbrl': 'http://www.xbrl.org/2003/instance',
            'dei': 'http://xbrl.sec.gov/dei/2023',
            'us-gaap': 'http://fasb.org/us-gaap/2023',
            'meta': 'http://www.meta.com/20240930'
        }
        
        # Financial concept mappings
        self.financial_concepts = {
            # Revenue concepts
            'Revenue': ['us-gaap:Revenues', 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'],
            'Net Income': ['us-gaap:NetIncomeLoss', 'us-gaap:ProfitLoss'],
            'Total Assets': ['us-gaap:Assets'],
            'Total Liabilities': ['us-gaap:Liabilities'],
            'Cash and Cash Equivalents': ['us-gaap:CashAndCashEquivalentsAtCarryingValue'],
            'Total Stockholders Equity': ['us-gaap:StockholdersEquity'],
            'Research and Development': ['us-gaap:ResearchAndDevelopmentExpense'],
            'Marketing and Sales': ['us-gaap:SellingAndMarketingExpense'],
        }
    
    def download_company_facts(self, ticker: str) -> Dict[str, Any]:
        """Download company facts JSON from SEC API."""
        if ticker not in self.companies:
            raise ValueError(f"Unknown ticker: {ticker}")
        
        cik = self.companies[ticker]["cik"].zfill(10)  # Pad with zeros
        url = f"{self.sec_api_base}/CIK{cik}.json"
        
        logger.info(f"Downloading company facts for {ticker} from {url}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            company_facts = response.json()
            
            # Save to file
            facts_file = self.output_dir / f"{ticker}_company_facts.json"
            with open(facts_file, 'w') as f:
                json.dump(company_facts, f, indent=2)
            
            logger.info(f"Saved company facts to {facts_file}")
            return company_facts
            
        except Exception as e:
            logger.error(f"Error downloading company facts for {ticker}: {e}")
            return {}
    
    def parse_company_facts(self, company_facts: Dict[str, Any], ticker: str) -> pd.DataFrame:
        """Parse company facts JSON to extract financial data."""
        financial_data = []
        
        if 'facts' not in company_facts:
            logger.warning("No facts found in company data")
            return pd.DataFrame()
        
        facts = company_facts['facts']
        
        # Process US-GAAP facts
        if 'us-gaap' in facts:
            for concept, data in facts['us-gaap'].items():
                if 'units' in data:
                    # Handle different unit types (USD, shares, etc.)
                    for unit_type, unit_data in data['units'].items():
                        for entry in unit_data:
                            financial_data.append({
                                'ticker': ticker,
                                'concept': concept,
                                'label': data.get('label', concept),
                                'description': data.get('description', ''),
                                'unit': unit_type,
                                'value': entry.get('val'),
                                'start_date': entry.get('start'),
                                'end_date': entry.get('end'),
                                'filed_date': entry.get('filed'),
                                'form': entry.get('form'),
                                'fiscal_year': entry.get('fy'),
                                'fiscal_period': entry.get('fp'),
                                'quarter': entry.get('quarter')
                            })
        
        # Process DEI (Document and Entity Information) facts
        if 'dei' in facts:
            for concept, data in facts['dei'].items():
                if 'units' in data:
                    for unit_type, unit_data in data['units'].items():
                        for entry in unit_data:
                            financial_data.append({
                                'ticker': ticker,
                                'concept': concept,
                                'label': data.get('label', concept),
                                'description': data.get('description', ''),
                                'unit': unit_type,
                                'value': entry.get('val'),
                                'start_date': entry.get('start'),
                                'end_date': entry.get('end'),
                                'filed_date': entry.get('filed'),
                                'form': entry.get('form'),
                                'fiscal_year': entry.get('fy'),
                                'fiscal_period': entry.get('fp'),
                                'quarter': entry.get('quarter')
                            })
        
        df = pd.DataFrame(financial_data)
        
        if not df.empty:
            # Clean and format data
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df['fiscal_year'] = pd.to_numeric(df['fiscal_year'], errors='coerce')
            
            # Filter for recent years (2023-2024)
            df = df[df['fiscal_year'].isin([2023, 2024])]
            
            # Save processed data
            csv_file = self.output_dir / f"{ticker}_financial_data.csv"
            df.to_csv(csv_file, index=False)
            logger.info(f"Saved financial data to {csv_file}")
        
        return df
    
    def load_pdf_table_data(self) -> Dict[str, pd.DataFrame]:
        """Load extracted table data from PDF processing."""
        pdf_tables = {}
        
        # Look for table CSV files in parsed data
        tables_dir = Path("data/parsed/tables")
        if not tables_dir.exists():
            logger.warning("No parsed tables directory found")
            return pdf_tables
        
        # Find CSV files
        csv_files = list(tables_dir.rglob("*.csv"))
        
        for csv_file in csv_files:
            try:
                # Extract filing info from path
                path_parts = csv_file.parts
                filing_info = "_".join(path_parts[-3:-1])  # e.g., "10-K_META_2024"
                
                df = pd.read_csv(csv_file)
                pdf_tables[f"{filing_info}_{csv_file.stem}"] = df
                
                logger.info(f"Loaded PDF table: {csv_file}")
                
            except Exception as e:
                logger.warning(f"Could not load {csv_file}: {e}")
        
        return pdf_tables
    
    def extract_numbers_from_text(self, text: str) -> List[float]:
        """Extract numerical values from text."""
        if pd.isna(text) or not isinstance(text, str):
            return []
        
        # Pattern to match numbers (including thousands separators and decimals)
        pattern = r'[\$\(]?[\d,]+\.?\d*[%\)]?'
        matches = re.findall(pattern, text)
        
        numbers = []
        for match in matches:
            try:
                # Clean the number
                clean_num = re.sub(r'[\$,\(\)%]', '', match)
                if clean_num:
                    num = float(clean_num)
                    # Convert to millions if it looks like it's in thousands
                    if num > 1000000:
                        num = num / 1000000  # Convert to millions
                    numbers.append(num)
            except ValueError:
                continue
        
        return numbers
    
    def find_concept_mapping(self, table_label: str, xbrl_concepts: List[str]) -> Optional[str]:
        """Find the best matching XBRL concept for a table label using similarity."""
        if not table_label or not xbrl_concepts:
            return None
        
        table_label_clean = table_label.lower().strip()
        best_match = None
        best_score = 0
        
        # Direct keyword matching
        concept_keywords = {
            'revenue': ['revenue', 'sales', 'income from operations'],
            'net income': ['net income', 'profit', 'earnings'],
            'assets': ['total assets', 'assets'],
            'liabilities': ['total liabilities', 'liabilities'],
            'cash': ['cash', 'cash equivalents'],
            'equity': ['equity', 'stockholders equity', 'shareholders equity'],
            'research': ['research', 'development', 'r&d'],
            'marketing': ['marketing', 'sales expense', 'advertising']
        }
        
        for concept_group, keywords in concept_keywords.items():
            for keyword in keywords:
                if keyword in table_label_clean:
                    # Find matching XBRL concept
                    for concept in xbrl_concepts:
                        if concept_group.replace(' ', '').lower() in concept.lower():
                            return concept
        
        # Fuzzy string matching as fallback
        for concept in xbrl_concepts:
            score = SequenceMatcher(None, table_label_clean, concept.lower()).ratio()
            if score > best_score and score > 0.6:  # 60% similarity threshold
                best_score = score
                best_match = concept
        
        return best_match
    
    def cross_verify_data(self, xbrl_df: pd.DataFrame, pdf_tables: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Cross-verify XBRL data against PDF table extractions."""
        verification_results = {
            'timestamp': datetime.now().isoformat(),
            'matches': [],
            'mismatches': [],
            'summary': {
                'total_comparisons': 0,
                'exact_matches': 0,
                'approximate_matches': 0,
                'mismatches': 0,
                'no_pdf_data': 0
            }
        }
        
        logger.info("Starting cross-verification of XBRL vs PDF data...")
        
        # Group XBRL data by filing type and year
        xbrl_grouped = xbrl_df.groupby(['form', 'fiscal_year'])
        
        for (form, year), xbrl_group in xbrl_grouped:
            logger.info(f"Verifying {form} {year}")
            
            # Find corresponding PDF table
            pdf_key_pattern = f"{form}.*{year}"
            matching_pdf_tables = {k: v for k, v in pdf_tables.items() if re.search(pdf_key_pattern, k)}
            
            if not matching_pdf_tables:
                verification_results['summary']['no_pdf_data'] += len(xbrl_group)
                continue
            
            # Get key financial concepts for verification
            key_concepts = [
                'us-gaap:Revenues',
                'us-gaap:NetIncomeLoss', 
                'us-gaap:Assets',
                'us-gaap:CashAndCashEquivalentsAtCarryingValue'
            ]
            
            for concept in key_concepts:
                xbrl_data = xbrl_group[xbrl_group['concept'] == concept]
                
                if xbrl_data.empty:
                    continue
                
                # Get the most recent value
                xbrl_value = xbrl_data.iloc[-1]['value']
                xbrl_label = xbrl_data.iloc[-1]['label']
                
                if pd.isna(xbrl_value):
                    continue
                
                # Search for matching values in PDF tables
                found_match = False
                
                for table_name, pdf_df in matching_pdf_tables.items():
                    # Extract all numbers from the PDF table
                    pdf_numbers = []
                    for col in pdf_df.columns:
                        for cell in pdf_df[col].astype(str):
                            pdf_numbers.extend(self.extract_numbers_from_text(cell))
                    
                    # Check for matches (convert XBRL value to millions if needed)
                    xbrl_value_millions = xbrl_value / 1000000 if xbrl_value > 1000000 else xbrl_value
                    
                    for pdf_num in pdf_numbers:
                        # Check for exact match (within 1%)
                        if abs(pdf_num - xbrl_value_millions) / max(xbrl_value_millions, 1) < 0.01:
                            verification_results['matches'].append({
                                'filing': f"{form} {year}",
                                'concept': concept,
                                'label': xbrl_label,
                                'xbrl_value': xbrl_value,
                                'pdf_value': pdf_num,
                                'pdf_table': table_name,
                                'match_type': 'exact',
                                'difference_percent': abs(pdf_num - xbrl_value_millions) / xbrl_value_millions * 100
                            })
                            verification_results['summary']['exact_matches'] += 1
                            found_match = True
                            break
                        
                        # Check for approximate match (within 10%)
                        elif abs(pdf_num - xbrl_value_millions) / max(xbrl_value_millions, 1) < 0.1:
                            verification_results['matches'].append({
                                'filing': f"{form} {year}",
                                'concept': concept,
                                'label': xbrl_label,
                                'xbrl_value': xbrl_value,
                                'pdf_value': pdf_num,
                                'pdf_table': table_name,
                                'match_type': 'approximate',
                                'difference_percent': abs(pdf_num - xbrl_value_millions) / xbrl_value_millions * 100
                            })
                            verification_results['summary']['approximate_matches'] += 1
                            found_match = True
                            break
                    
                    if found_match:
                        break
                
                if not found_match:
                    verification_results['mismatches'].append({
                        'filing': f"{form} {year}",
                        'concept': concept,
                        'label': xbrl_label,
                        'xbrl_value': xbrl_value,
                        'pdf_tables_searched': list(matching_pdf_tables.keys()),
                        'reason': 'No matching value found in PDF tables'
                    })
                    verification_results['summary']['mismatches'] += 1
                
                verification_results['summary']['total_comparisons'] += 1
        
        # Save verification results
        results_file = self.output_dir / "cross_verification_results.json"
        with open(results_file, 'w') as f:
            json.dump(verification_results, f, indent=2)
        
        logger.info(f"Cross-verification complete. Results saved to {results_file}")
        return verification_results
    
    def generate_verification_report(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable verification report."""
        report = []
        report.append("# XBRL vs PDF Cross-Verification Report")
        report.append(f"Generated: {results['timestamp']}")
        report.append("")
        
        # Summary
        summary = results['summary']
        report.append("## Summary")
        report.append(f"- Total Comparisons: {summary['total_comparisons']}")
        report.append(f"- Exact Matches: {summary['exact_matches']}")
        report.append(f"- Approximate Matches: {summary['approximate_matches']}")
        report.append(f"- Mismatches: {summary['mismatches']}")
        report.append(f"- No PDF Data: {summary['no_pdf_data']}")
        report.append("")
        
        # Calculate success rate
        total_with_data = summary['total_comparisons'] - summary['no_pdf_data']
        if total_with_data > 0:
            success_rate = (summary['exact_matches'] + summary['approximate_matches']) / total_with_data * 100
            report.append(f"**Success Rate: {success_rate:.1f}%**")
        report.append("")
        
        # Matches
        if results['matches']:
            report.append("## ✅ Successful Matches")
            for match in results['matches']:
                report.append(f"### {match['filing']} - {match['label']}")
                report.append(f"- XBRL Value: ${match['xbrl_value']:,.0f}")
                report.append(f"- PDF Value: ${match['pdf_value']:.0f}M")
                report.append(f"- Match Type: {match['match_type']}")
                report.append(f"- Difference: {match['difference_percent']:.2f}%")
                report.append(f"- Source Table: {match['pdf_table']}")
                report.append("")
        
        # Mismatches
        if results['mismatches']:
            report.append("## ❌ Mismatches")
            for mismatch in results['mismatches']:
                report.append(f"### {mismatch['filing']} - {mismatch['label']}")
                report.append(f"- XBRL Value: ${mismatch['xbrl_value']:,.0f}")
                report.append(f"- Reason: {mismatch['reason']}")
                report.append(f"- PDF Tables Searched: {', '.join(mismatch['pdf_tables_searched'])}")
                report.append("")
        
        # Recommendations
        report.append("## 🔧 Recommendations")
        
        if summary['mismatches'] > summary['exact_matches']:
            report.append("- **High mismatch rate detected** - Review PDF table extraction accuracy")
            report.append("- Consider improving OCR quality or table parsing algorithms")
        
        if summary['no_pdf_data'] > 0:
            report.append("- **Missing PDF data** - Ensure all filings have corresponding extracted tables")
        
        if summary['approximate_matches'] > summary['exact_matches']:
            report.append("- **Many approximate matches** - May indicate unit conversion issues")
            report.append("- Review number extraction and unit standardization")
        
        report_text = "\n".join(report)
        
        # Save report
        report_file = self.output_dir / "verification_report.md"
        with open(report_file, 'w') as f:
            f.write(report_text)
        
        logger.info(f"Verification report saved to {report_file}")
        return report_text
    
    def run_full_verification(self, ticker: str = "META") -> Dict[str, Any]:
        """Run the complete XBRL cross-verification process."""
        logger.info(f"Starting full XBRL cross-verification for {ticker}")
        
        # Step 1: Download company facts
        company_facts = self.download_company_facts(ticker)
        if not company_facts:
            logger.error("Failed to download company facts")
            return {}
        
        # Step 2: Parse financial data
        xbrl_df = self.parse_company_facts(company_facts, ticker)
        if xbrl_df.empty:
            logger.error("No financial data parsed from XBRL")
            return {}
        
        logger.info(f"Parsed {len(xbrl_df)} XBRL data points")
        
        # Step 3: Load PDF table data
        pdf_tables = self.load_pdf_table_data()
        logger.info(f"Loaded {len(pdf_tables)} PDF tables")
        
        # Step 4: Cross-verify
        results = self.cross_verify_data(xbrl_df, pdf_tables)
        
        # Step 5: Generate report
        report = self.generate_verification_report(results)
        
        # Display summary
        print("\n" + "="*60)
        print("XBRL CROSS-VERIFICATION SUMMARY")
        print("="*60)
        print(f"Total Comparisons: {results['summary']['total_comparisons']}")
        print(f"Exact Matches: {results['summary']['exact_matches']}")
        print(f"Approximate Matches: {results['summary']['approximate_matches']}")
        print(f"Mismatches: {results['summary']['mismatches']}")
        
        if results['summary']['total_comparisons'] > 0:
            success_rate = (results['summary']['exact_matches'] + results['summary']['approximate_matches']) / results['summary']['total_comparisons'] * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        print("\n📄 Detailed report saved to: data/xbrl_validation/verification_report.md")
        
        return results


if __name__ == "__main__":
    # Run XBRL cross-verification
    verifier = XBRLCrossVerification()
    results = verifier.run_full_verification("META")
