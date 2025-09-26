#!/usr/bin/env python3
"""
Comprehensive Document Processing Pipeline

Processes all available Docling JSON files through the complete metadata schema pipeline:
1. Convert Docling JSON → JSONL with unified schema
2. Generate section-specific Markdown files
3. Create analysis reports

Usage: python process_all_documents.py
"""

import json
from pathlib import Path
from src.parsers.metadata_schema import DoclingToJSONLConverter, SectionReassembler


def main():
    """Process all available Docling documents"""
    
    print("🚀 COMPREHENSIVE DOCUMENT PROCESSING PIPELINE")
    print("=" * 60)
    
    # Initialize processors
    converter = DoclingToJSONLConverter()
    reassembler = SectionReassembler()
    
    # Find all Docling JSON files
    docling_dir = Path("data/parsed/docling")
    docling_files = list(docling_dir.glob("*_docling.json"))
    
    print(f"📋 Found {len(docling_files)} Docling JSON files:")
    for file in docling_files:
        print(f"   • {file.name}")
    
    if not docling_files:
        print("❌ No Docling JSON files found in data/parsed/docling/")
        return
    
    # Process each document
    processing_results = []
    
    for docling_file in docling_files:
        try:
            print(f"\n🔄 Processing: {docling_file.name}")
            print("-" * 50)
            
            # Setup output paths
            doc_name = docling_file.stem.replace('_docling', '')
            jsonl_output = f"data/parsed/metadata/{doc_name}_blocks.jsonl"
            
            # Convert to JSONL
            stats = converter.convert_docling_to_jsonl(str(docling_file), jsonl_output)
            
            # Generate section-specific Markdown files
            sections_processed = []
            
            # Process each section found in the document
            for section in stats['sections_found']:
                try:
                    md_output = f"data/parsed/metadata/{doc_name}_{section}.md"
                    reassembler.reassemble_section(jsonl_output, section, md_output)
                    sections_processed.append(section)
                except Exception as e:
                    print(f"⚠️ Failed to process section '{section}': {e}")
            
            # Generate full document
            full_md_output = f"data/parsed/metadata/{doc_name}_full_document.md"
            reassembler.reassemble_full_document(jsonl_output, full_md_output)
            
            # Record results
            result = {
                'document': doc_name,
                'jsonl_file': jsonl_output,
                'full_document_md': full_md_output,
                'sections_processed': sections_processed,
                'stats': stats
            }
            processing_results.append(result)
            
            print(f"✅ {doc_name} processed successfully!")
            print(f"   📊 {stats['total_blocks']} blocks ({stats['text_blocks']} text, {stats['table_blocks']} tables)")
            print(f"   📑 {len(sections_processed)} sections: {sections_processed}")
            
        except Exception as e:
            print(f"❌ Failed to process {docling_file.name}: {e}")
            continue
    
    # Generate processing summary
    print(f"\n📊 PROCESSING SUMMARY")
    print("=" * 50)
    
    total_blocks = sum(r['stats']['total_blocks'] for r in processing_results)
    total_pages = sum(len(r['stats']['pages_processed']) for r in processing_results)
    
    print(f"📋 Documents processed: {len(processing_results)}")
    print(f"📊 Total blocks: {total_blocks:,}")
    print(f"📄 Total pages: {total_pages}")
    
    # Show breakdown by document
    for result in processing_results:
        stats = result['stats']
        print(f"\n📄 {result['document']}:")
        print(f"   🏢 Company: {stats['company']}")
        print(f"   📅 Year: {stats['fiscal_year']}")
        print(f"   📊 Blocks: {stats['total_blocks']} (Text: {stats['text_blocks']}, Tables: {stats['table_blocks']}, Figures: {stats['figure_blocks']})")
        print(f"   📄 Pages: {len(stats['pages_processed'])}")
        print(f"   📑 Sections: {len(stats['sections_found'])}")
        print(f"   📝 Files created:")
        print(f"      • JSONL: {result['jsonl_file']}")
        print(f"      • Full MD: {result['full_document_md']}")
        for section in result['sections_processed']:
            print(f"      • {section.title()} MD: data/parsed/metadata/{result['document']}_{section}.md")
    
    # Save processing summary
    summary_file = "data/parsed/metadata/processing_summary.json"
    Path(summary_file).parent.mkdir(parents=True, exist_ok=True)
    
    summary_data = {
        'processing_date': processing_results[0]['stats']['conversion_time'] if processing_results else None,
        'documents_processed': len(processing_results),
        'total_blocks': total_blocks,
        'total_pages': total_pages,
        'results': processing_results
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Processing summary saved to: {summary_file}")
    
    # Show sample JSONL records
    if processing_results:
        print(f"\n📋 SAMPLE JSONL RECORDS")
        print("-" * 30)
        
        sample_jsonl = processing_results[0]['jsonl_file']
        print(f"From: {sample_jsonl}")
        
        with open(sample_jsonl, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 3:  # Show first 3 records
                    break
                record = json.loads(line.strip())
                print(f"Record {i+1}:")
                print(f"  • Page {record['page']}: {record['section']} - {record['block_type']}")
                print(f"  • Text: {record['text'][:60]}...")
                print(f"  • Bbox: {record['bbox']}")
                print()
    
    print(f"\n🎉 COMPREHENSIVE PROCESSING COMPLETE!")
    print(f"   📊 {len(processing_results)} documents converted to JSONL")
    print(f"   📑 All sections reassembled to Markdown")
    print(f"   💾 All outputs saved to data/parsed/metadata/")


if __name__ == "__main__":
    main()
