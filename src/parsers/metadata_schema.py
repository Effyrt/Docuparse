#!/usr/bin/env python3
"""
Unified Metadata Schema Implementation

Implements the complete metadata schema system:
1. Define unified schema for doc blocks
2. Convert Docling JSON to JSONL records  
3. Reassemble report sections into Markdown

Author: PeiYing Branch Implementation
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime


@dataclass
class DocumentBlock:
    """Unified metadata schema for document blocks"""
    doc_id: str
    company: str
    fiscal_year: int
    page: int
    section: str
    block_type: str  # "text", "table", "figure", "title", "section_header"
    bbox: List[float]  # [left, top, right, bottom]
    text: Optional[str]
    source_path: str
    confidence: Optional[float] = None
    extraction_method: str = "docling"
    level: Optional[int] = None
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            'doc_id': self.doc_id,
            'company': self.company,
            'fiscal_year': self.fiscal_year,
            'page': self.page,
            'section': self.section,
            'block_type': self.block_type,
            'bbox': self.bbox,
            'text': self.text,
            'source_path': self.source_path,
            'extraction_method': self.extraction_method
        }
        
        # Add optional fields if present
        if self.confidence is not None:
            result['confidence'] = self.confidence
        if self.level is not None:
            result['level'] = self.level
        if self.timestamp is not None:
            result['timestamp'] = self.timestamp
            
        return result


class DocumentMetadataExtractor:
    """Extract metadata from document filenames and content"""
    
    @staticmethod
    def extract_company_from_filename(filename: str) -> str:
        """Extract company name from filename"""
        filename = filename.lower()
        
        # Common company patterns in SEC filings
        if 'meta' in filename:
            return 'META'
        elif 'apple' in filename:
            return 'AAPL'
        elif 'microsoft' in filename:
            return 'MSFT'
        elif 'google' in filename or 'alphabet' in filename:
            return 'GOOGL'
        elif 'amazon' in filename:
            return 'AMZN'
        else:
            # Try to extract from filename pattern
            # e.g., "2024_companyname_10k.pdf"
            parts = filename.replace('.pdf', '').split('_')
            if len(parts) >= 2:
                return parts[1].upper()
            return 'UNKNOWN'
    
    @staticmethod
    def extract_fiscal_year_from_filename(filename: str) -> int:
        """Extract fiscal year from filename"""
        # Look for 4-digit year pattern
        year_match = re.search(r'(20\d{2})', filename)
        if year_match:
            return int(year_match.group(1))
        
        # Default to current year if not found
        return datetime.now().year
    
    @staticmethod
    def extract_doc_type_from_filename(filename: str) -> str:
        """Extract document type (10-K, 10-Q, etc.)"""
        filename = filename.lower()
        
        if '10-k' in filename or '10k' in filename:
            return '10-K'
        elif '10-q' in filename or '10q' in filename:
            return '10-Q'
        elif '8-k' in filename or '8k' in filename:
            return '8-K'
        else:
            return 'UNKNOWN'


class DoclingToJSONLConverter:
    """Convert Docling JSON format to unified JSONL schema"""
    
    def __init__(self):
        self.metadata_extractor = DocumentMetadataExtractor()
    
    def convert_docling_to_jsonl(self, docling_json_path: str, output_jsonl_path: str) -> Dict[str, Any]:
        """
        Convert Docling JSON to JSONL format with unified schema
        
        Args:
            docling_json_path: Path to Docling JSON file
            output_jsonl_path: Path to output JSONL file
            
        Returns:
            Conversion statistics
        """
        print(f"🔄 Converting Docling JSON to JSONL...")
        print(f"   Input: {docling_json_path}")
        print(f"   Output: {output_jsonl_path}")
        
        # Load Docling JSON
        with open(docling_json_path, 'r', encoding='utf-8') as f:
            docling_data = json.load(f)
        
        # Extract document metadata
        filename = docling_data['origin']['filename']
        doc_id = docling_data['name']
        company = self.metadata_extractor.extract_company_from_filename(filename)
        fiscal_year = self.metadata_extractor.extract_fiscal_year_from_filename(filename)
        timestamp = datetime.now().isoformat()
        
        print(f"   📋 Document: {doc_id}")
        print(f"   🏢 Company: {company}")
        print(f"   📅 Fiscal Year: {fiscal_year}")
        
        # Convert to JSONL
        output_path = Path(output_jsonl_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        stats = {
            'doc_id': doc_id,
            'company': company,
            'fiscal_year': fiscal_year,
            'total_blocks': 0,
            'text_blocks': 0,
            'table_blocks': 0,
            'figure_blocks': 0,
            'pages_processed': set(),
            'sections_found': set(),
            'conversion_time': timestamp
        }
        
        with open(output_jsonl_path, 'w', encoding='utf-8') as f:
            # Process text elements
            for text_elem in docling_data.get('texts', []):
                block = self._convert_text_element(
                    text_elem, doc_id, company, fiscal_year, filename, timestamp
                )
                f.write(json.dumps(block.to_dict()) + '\n')
                
                stats['total_blocks'] += 1
                stats['text_blocks'] += 1
                stats['pages_processed'].add(block.page)
                stats['sections_found'].add(block.section)
            
            # Process table elements
            for table_elem in docling_data.get('tables', []):
                block = self._convert_table_element(
                    table_elem, doc_id, company, fiscal_year, filename, timestamp
                )
                f.write(json.dumps(block.to_dict()) + '\n')
                
                stats['total_blocks'] += 1
                stats['table_blocks'] += 1
                stats['pages_processed'].add(block.page)
                stats['sections_found'].add(block.section)
            
            # Process figure/picture elements
            for figure_elem in docling_data.get('pictures', []):
                block = self._convert_figure_element(
                    figure_elem, doc_id, company, fiscal_year, filename, timestamp
                )
                f.write(json.dumps(block.to_dict()) + '\n')
                
                stats['total_blocks'] += 1
                stats['figure_blocks'] += 1
                stats['pages_processed'].add(block.page)
                stats['sections_found'].add(block.section)
        
        # Convert sets to lists for JSON serialization
        stats['pages_processed'] = sorted(list(stats['pages_processed']))
        stats['sections_found'] = sorted(list(stats['sections_found']))
        
        print(f"✅ Conversion complete!")
        print(f"   📊 Total blocks: {stats['total_blocks']}")
        print(f"   📝 Text blocks: {stats['text_blocks']}")
        print(f"   📋 Table blocks: {stats['table_blocks']}")
        print(f"   🖼️ Figure blocks: {stats['figure_blocks']}")
        print(f"   📄 Pages: {len(stats['pages_processed'])}")
        print(f"   📑 Sections: {len(stats['sections_found'])}")
        
        return stats
    
    def _convert_text_element(self, text_elem: Dict, doc_id: str, company: str, 
                            fiscal_year: int, filename: str, timestamp: str) -> DocumentBlock:
        """Convert Docling text element to DocumentBlock"""
        
        # Extract provenance info (page and bbox)
        prov = text_elem['prov'][0] if text_elem.get('prov') else {}
        page_no = prov.get('page_no', 1)
        bbox_info = prov.get('bbox', {})
        
        # Convert bbox to [left, top, right, bottom] format
        bbox = [
            bbox_info.get('l', 0),
            bbox_info.get('t', 0), 
            bbox_info.get('r', 0),
            bbox_info.get('b', 0)
        ]
        
        # Map Docling labels to our section types
        section = self._map_docling_label_to_section(text_elem.get('label', 'unknown'))
        
        return DocumentBlock(
            doc_id=doc_id,
            company=company,
            fiscal_year=fiscal_year,
            page=page_no,
            section=section,
            block_type='text',
            bbox=bbox,
            text=text_elem.get('text', ''),
            source_path=filename,
            level=text_elem.get('level'),
            timestamp=timestamp
        )
    
    def _convert_table_element(self, table_elem: Dict, doc_id: str, company: str,
                             fiscal_year: int, filename: str, timestamp: str) -> DocumentBlock:
        """Convert Docling table element to DocumentBlock"""
        
        prov = table_elem['prov'][0] if table_elem.get('prov') else {}
        page_no = prov.get('page_no', 1)
        bbox_info = prov.get('bbox', {})
        
        bbox = [
            bbox_info.get('l', 0),
            bbox_info.get('t', 0),
            bbox_info.get('r', 0), 
            bbox_info.get('b', 0)
        ]
        
        section = self._map_docling_label_to_section(table_elem.get('label', 'table'))
        
        # Extract table text content if available
        table_text = self._extract_table_text(table_elem)
        
        return DocumentBlock(
            doc_id=doc_id,
            company=company,
            fiscal_year=fiscal_year,
            page=page_no,
            section=section,
            block_type='table',
            bbox=bbox,
            text=table_text,
            source_path=filename,
            timestamp=timestamp
        )
    
    def _convert_figure_element(self, figure_elem: Dict, doc_id: str, company: str,
                              fiscal_year: int, filename: str, timestamp: str) -> DocumentBlock:
        """Convert Docling figure element to DocumentBlock"""
        
        prov = figure_elem['prov'][0] if figure_elem.get('prov') else {}
        page_no = prov.get('page_no', 1)
        bbox_info = prov.get('bbox', {})
        
        bbox = [
            bbox_info.get('l', 0),
            bbox_info.get('t', 0),
            bbox_info.get('r', 0),
            bbox_info.get('b', 0)
        ]
        
        section = self._map_docling_label_to_section(figure_elem.get('label', 'figure'))
        
        return DocumentBlock(
            doc_id=doc_id,
            company=company,
            fiscal_year=fiscal_year,
            page=page_no,
            section=section,
            block_type='figure',
            bbox=bbox,
            text=figure_elem.get('text', '[Figure]'),
            source_path=filename,
            timestamp=timestamp
        )
    
    def _map_docling_label_to_section(self, docling_label: str) -> str:
        """Map Docling labels to our standardized section names"""
        
        label_mapping = {
            'section_header': 'header',
            'title': 'title',
            'text': 'body',
            'document_index': 'toc',
            'table': 'tables',
            'figure': 'figures',
            'footnote': 'footnotes',
            'caption': 'captions',
            'reference': 'references'
        }
        
        return label_mapping.get(docling_label, 'other')
    
    def _extract_table_text(self, table_elem: Dict) -> str:
        """Extract text representation from table data"""
        
        try:
            table_data = table_elem.get('data', {})
            if isinstance(table_data, dict) and 'table_cells' in table_data:
                # Extract cell text
                cells = table_data['table_cells']
                cell_texts = []
                for cell in cells:
                    if isinstance(cell, dict) and 'text' in cell:
                        cell_texts.append(cell['text'])
                
                return ' | '.join(cell_texts) if cell_texts else '[Table data]'
            
            return '[Table data]'
            
        except Exception:
            return '[Table data]'


class SectionReassembler:
    """Reassemble document sections from JSONL records into Markdown"""
    
    def __init__(self):
        pass
    
    def reassemble_section(self, jsonl_path: str, section_name: str, 
                          output_md_path: Optional[str] = None) -> str:
        """
        Reassemble a specific section from JSONL records into Markdown
        
        Args:
            jsonl_path: Path to JSONL file with document blocks
            section_name: Section to reassemble ('header', 'body', 'tables', etc.)
            output_md_path: Optional path to save Markdown output
            
        Returns:
            Markdown content as string
        """
        print(f"📖 Reassembling section: {section_name}")
        print(f"   Source: {jsonl_path}")
        
        # Load and filter records by section
        section_blocks = []
        
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                block_data = json.loads(line.strip())
                if block_data['section'] == section_name:
                    section_blocks.append(block_data)
        
        if not section_blocks:
            print(f"⚠️ No blocks found for section: {section_name}")
            return ""
        
        # Sort by page and then by vertical position (top of bbox)
        section_blocks.sort(key=lambda x: (x['page'], -x['bbox'][1]))
        
        print(f"   📋 Found {len(section_blocks)} blocks")
        
        # Generate Markdown
        markdown_content = self._generate_section_markdown(section_blocks, section_name)
        
        # Save to file if path provided
        if output_md_path:
            output_path = Path(output_md_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            print(f"   💾 Saved to: {output_md_path}")
        
        return markdown_content
    
    def reassemble_full_document(self, jsonl_path: str, output_md_path: str) -> str:
        """
        Reassemble full document from JSONL records into structured Markdown
        
        Args:
            jsonl_path: Path to JSONL file with document blocks
            output_md_path: Path to save full Markdown document
            
        Returns:
            Full Markdown content
        """
        print(f"📄 Reassembling full document")
        print(f"   Source: {jsonl_path}")
        
        # Load all records
        all_blocks = []
        doc_info = {}
        
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                block_data = json.loads(line.strip())
                all_blocks.append(block_data)
                
                # Capture document info from first block
                if not doc_info:
                    doc_info = {
                        'doc_id': block_data['doc_id'],
                        'company': block_data['company'],
                        'fiscal_year': block_data['fiscal_year'],
                        'source_path': block_data['source_path']
                    }
        
        # Group by sections
        sections = {}
        for block in all_blocks:
            section = block['section']
            if section not in sections:
                sections[section] = []
            sections[section].append(block)
        
        # Sort each section by page and position
        for section_blocks in sections.values():
            section_blocks.sort(key=lambda x: (x['page'], -x['bbox'][1]))
        
        print(f"   📊 Document info: {doc_info['company']} {doc_info['fiscal_year']}")
        print(f"   📑 Sections found: {list(sections.keys())}")
        print(f"   📋 Total blocks: {len(all_blocks)}")
        
        # Generate full Markdown document
        markdown_content = self._generate_full_document_markdown(sections, doc_info)
        
        # Save to file
        output_path = Path(output_md_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"   💾 Full document saved to: {output_md_path}")
        
        return markdown_content
    
    def _generate_section_markdown(self, section_blocks: List[Dict], section_name: str) -> str:
        """Generate Markdown for a specific section"""
        
        lines = []
        lines.append(f"# {section_name.title()} Section")
        lines.append("")
        
        current_page = None
        
        for block in section_blocks:
            # Add page separator if page changes
            if current_page != block['page']:
                current_page = block['page']
                if len(lines) > 2:  # Not the first page
                    lines.append("")
                    lines.append("---")
                    lines.append("")
                lines.append(f"## Page {current_page}")
                lines.append("")
            
            # Add block content based on type
            if block['block_type'] == 'table':
                lines.append("### Table")
                lines.append("")
                lines.append(f"```")
                lines.append(block['text'] or '[Table data]')
                lines.append(f"```")
                lines.append("")
            elif block['block_type'] == 'figure':
                lines.append("### Figure")
                lines.append("")
                lines.append(f"*{block['text'] or '[Figure]'}*")
                lines.append("")
            else:
                # Text content
                text = block['text'] or ''
                if text:
                    # Add appropriate markdown formatting based on content
                    if len(text) < 100 and text.isupper():
                        lines.append(f"### {text}")
                    else:
                        lines.append(text)
                    lines.append("")
        
        return '\n'.join(lines)
    
    def _generate_full_document_markdown(self, sections: Dict[str, List[Dict]], 
                                       doc_info: Dict) -> str:
        """Generate full document Markdown with all sections"""
        
        lines = []
        
        # Document header
        lines.append(f"# {doc_info['company']} - {doc_info['fiscal_year']} SEC Filing")
        lines.append("")
        lines.append(f"**Document ID:** {doc_info['doc_id']}")
        lines.append(f"**Company:** {doc_info['company']}")
        lines.append(f"**Fiscal Year:** {doc_info['fiscal_year']}")
        lines.append(f"**Source:** {doc_info['source_path']}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Table of contents
        lines.append("## Table of Contents")
        lines.append("")
        section_order = ['header', 'toc', 'body', 'tables', 'figures', 'footnotes', 'other']
        
        for section in section_order:
            if section in sections:
                lines.append(f"- [{section.title()}](#{section})")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Add each section
        for section in section_order:
            if section in sections:
                section_md = self._generate_section_markdown(sections[section], section)
                lines.append(section_md)
                lines.append("")
        
        return '\n'.join(lines)


def main():
    """Example usage of the metadata schema system"""
    
    # Example conversion
    converter = DoclingToJSONLConverter()
    reassembler = SectionReassembler()
    
    # Convert Docling JSON to JSONL
    docling_json = "data/parsed/docling/2024_1_meta_docling.json"
    jsonl_output = "data/parsed/metadata/2024_1_meta_blocks.jsonl"
    
    if Path(docling_json).exists():
        print("🔄 Converting Docling JSON to JSONL...")
        stats = converter.convert_docling_to_jsonl(docling_json, jsonl_output)
        
        # Reassemble specific section
        print("\n📖 Reassembling header section...")
        header_md = reassembler.reassemble_section(
            jsonl_output, 
            'header', 
            'data/parsed/metadata/2024_1_meta_header.md'
        )
        
        # Reassemble full document
        print("\n📄 Reassembling full document...")
        full_md = reassembler.reassemble_full_document(
            jsonl_output,
            'data/parsed/metadata/2024_1_meta_full_document.md'
        )
        
        print("\n✅ Metadata schema implementation complete!")
        print(f"   📊 JSONL: {jsonl_output}")
        print(f"   📋 Header MD: data/parsed/metadata/2024_1_meta_header.md")
        print(f"   📄 Full MD: data/parsed/metadata/2024_1_meta_full_document.md")
    
    else:
        print(f"❌ Docling JSON not found: {docling_json}")


if __name__ == "__main__":
    main()
