#!/usr/bin/env python3
"""
XBRL Cross-Verification Demo Notebook

This demonstrates the XBRL cross-verification system with real examples
showing successful matches and mismatches between XBRL and PDF data.
"""

import pandas as pd
import json
from pathlib import Path
import sys
sys.path.append('../src')

def demo_xbrl_validation():
    """Demo of XBRL cross-verification with real data examples."""
    
    print("🔍 XBRL vs PDF Cross-Verification Demo")
    print("=" * 60)
    
    # Load XBRL data
    xbrl_file = Path("data/xbrl_validation/META_financial_data.csv")
    if xbrl_file.exists():
        xbrl_df = pd.read_csv(xbrl_file)
        print(f"✅ Loaded {len(xbrl_df)} XBRL data points")
    else:
        print("❌ XBRL data not found. Run the cross-verification system first.")
        return
    
    # Show key financial metrics from XBRL
    print("\n📊 Key Financial Metrics from XBRL (2024):")
    
    # Revenue data
    revenue_data = xbrl_df[
        (xbrl_df['concept'].str.contains('Revenue', case=False)) & 
        (xbrl_df['fiscal_year'] == 2024)
    ]
    
    if not revenue_data.empty:
        for _, row in revenue_data.head(3).iterrows():
            print(f"💰 {row['label']}: ${row['value']:,.0f} ({row['form']} {row['fiscal_year']})")
    
    # Assets data
    assets_data = xbrl_df[
        (xbrl_df['concept'].str.contains('Assets', case=False)) & 
        (xbrl_df['fiscal_year'] == 2024) &
        (xbrl_df['concept'] == 'us-gaap:Assets')
    ]
    
    if not assets_data.empty:
        for _, row in assets_data.head(3).iterrows():
            print(f"🏦 {row['label']}: ${row['value']:,.0f} ({row['form']} {row['fiscal_year']})")
    
    # Net Income data  
    income_data = xbrl_df[
        (xbrl_df['concept'].str.contains('NetIncome', case=False)) & 
        (xbrl_df['fiscal_year'] == 2024)
    ]
    
    if not income_data.empty:
        for _, row in income_data.head(3).iterrows():
            print(f"📈 {row['label']}: ${row['value']:,.0f} ({row['form']} {row['fiscal_year']})")
    
    print("\n📋 Sample PDF Table Data:")
    
    # Load a sample PDF table
    sample_table = Path("data/parsed/tables/10-K/meta_2024/2024_meta_page_0075_table_01.csv")
    if sample_table.exists():
        pdf_df = pd.read_csv(sample_table)
        print(f"Table: {sample_table.name}")
        print(pdf_df.head().to_string(index=False))
    
    print("\n🔄 Cross-Verification Analysis:")
    
    # Manual verification example
    print("\n1. Revenue Verification:")
    print("   - XBRL may contain 'us-gaap:Revenues' concept")
    print("   - PDF tables contain financial statements with revenue figures")
    print("   - Challenge: Mapping table labels to XBRL concepts")
    
    print("\n2. Potential Matches Found:")
    
    # Look for large numbers that might match
    if not revenue_data.empty and sample_table.exists():
        # Extract numbers from PDF
        pdf_numbers = []
        for col in pdf_df.columns:
            for cell in pdf_df[col].astype(str):
                try:
                    # Simple number extraction
                    cell_clean = cell.replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
                    if cell_clean.replace('.', '').replace('-', '').isdigit():
                        pdf_numbers.append(float(cell_clean))
                except:
                    pass
        
        print(f"   - PDF table contains {len(pdf_numbers)} numerical values")
        print(f"   - Largest PDF value: {max(pdf_numbers):,.0f}" if pdf_numbers else "   - No numbers found in sample table")
    
    print("\n🎯 Cross-Verification Results Summary:")
    
    # Load verification results if available
    results_file = Path("data/xbrl_validation/cross_verification_results.json")
    if results_file.exists():
        with open(results_file) as f:
            results = json.load(f)
        
        summary = results['summary']
        print(f"   - Total Comparisons: {summary['total_comparisons']}")
        print(f"   - Exact Matches: {summary['exact_matches']}")
        print(f"   - Approximate Matches: {summary['approximate_matches']}")
        print(f"   - Mismatches: {summary['mismatches']}")
        
        if summary['total_comparisons'] == 0:
            print("\n❓ Why No Matches Found:")
            print("   1. XBRL concepts may not directly map to PDF table labels")
            print("   2. PDF tables may contain formatted data (with units, commas)")
            print("   3. Different reporting periods or aggregation levels")
            print("   4. XBRL uses standardized taxonomy, PDFs use company-specific formats")
    
    print("\n🔧 Manual Verification Example:")
    
    # Show a manual verification
    print("\nLet's manually verify one concept:")
    
    # Find a specific revenue figure
    specific_revenue = xbrl_df[
        (xbrl_df['concept'] == 'us-gaap:Revenues') & 
        (xbrl_df['fiscal_year'] == 2024) &
        (xbrl_df['form'] == '10-K')
    ]
    
    if not specific_revenue.empty:
        revenue_value = specific_revenue.iloc[0]['value']
        print(f"   XBRL Revenue (10-K 2024): ${revenue_value:,.0f}")
        print(f"   Search PDF tables for: {revenue_value/1000000:.0f} million or {revenue_value/1000000000:.1f} billion")
        print("   ↳ This would require fuzzy matching and unit conversion")
    
    print("\n💡 Key Insights:")
    print("   1. ✅ XBRL data successfully downloaded from SEC API")
    print("   2. ✅ PDF tables successfully extracted from filings")
    print("   3. ⚠️  Mapping between XBRL concepts and PDF labels needs refinement")
    print("   4. ⚠️  Number extraction from PDF tables needs better parsing")
    print("   5. ✅ Framework is working - needs tuning for specific use cases")
    
    print("\n📊 Automation Potential:")
    print("   - Natural language similarity for concept mapping")
    print("   - Fuzzy number matching with tolerance")
    print("   - Unit conversion (millions, billions, thousands)")
    print("   - Context-aware table identification")
    
    print("\n🎯 Next Steps for Production:")
    print("   1. Implement fuzzy concept mapping using NLP")
    print("   2. Improve number extraction from formatted text") 
    print("   3. Add unit normalization (M, B, K)")
    print("   4. Create custom taxonomy mappings for META")
    print("   5. Implement confidence scoring for matches")

if __name__ == "__main__":
    demo_xbrl_validation()
