from pathlib import Path
import json
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat

class DoclingParser:
    def __init__(self, max_pages: int = None, output_dir: str = "data/parsed/docling"):
        self.max_pages = max_pages
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.converter = DocumentConverter()
    
    def parse_pdf_comprehensive(self, pdf_path: str):
        """Parse PDF and export to both JSON and Markdown with detailed analysis"""
        pdf_path = Path(pdf_path)
        
        print(f"\n🔄 COMPREHENSIVE DOCLING ANALYSIS: {pdf_path.name}")
        print("=" * 70)
        
        # Run docling converter
        result = self.converter.convert(pdf_path)
        document = result.document
        
        # Export to different formats
        doc_dict = document.export_to_dict()
        markdown_content = document.export_to_markdown()
        
        # Save JSON output
        json_file = self.output_dir / f"{pdf_path.stem}_docling.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(doc_dict, f, indent=2, ensure_ascii=False)
        
        # Save Markdown output  
        md_file = self.output_dir / f"{pdf_path.stem}_docling.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        # Critical feature analysis (reading order, tables, formulas)
        self._analyze_critical_features(doc_dict, pdf_path.stem)
        
        print(f"\n💾 Outputs saved:")
        print(f"  📄 JSON: {json_file}")
        print(f"  📝 Markdown: {md_file}")
        
        return {
            'document': document,
            'json_dict': doc_dict,
            'markdown': markdown_content,
            'json_file': json_file,
            'md_file': md_file
        }
    
    def _analyze_document_structure(self, document, doc_name):
        """Detailed analysis focusing on READING ORDER and document structure"""
        
        print(f"\n📖 READING ORDER ANALYSIS: {doc_name}")
        print("-" * 60)
        
        # Basic statistics
        if hasattr(document, 'pages'):
            print(f"📄 Total pages: {len(document.pages)}")
            
            for i, page in enumerate(document.pages[:3]):  # Deep analysis of first 3 pages
                print(f"\n{'='*40}")
                print(f"📄 PAGE {i+1} READING ORDER ANALYSIS")
                print(f"{'='*40}")
                
                page_elements = getattr(page, 'elements', [])
                
                # Sort elements by reading order (top-to-bottom, left-to-right)
                positioned_elements = []
                for elem in page_elements:
                    if hasattr(elem, 'bbox') and elem.bbox:
                        bbox = elem.bbox
                        if hasattr(bbox, 't') and hasattr(bbox, 'l'):
                            positioned_elements.append({
                                'element': elem,
                                'top': bbox.t,
                                'left': bbox.l,
                                'text': getattr(elem, 'text', '')[:80] + '...' if len(getattr(elem, 'text', '')) > 80 else getattr(elem, 'text', ''),
                                'label': getattr(elem, 'label', 'unknown')
                            })
                
                # Sort by reading order: top-to-bottom first, then left-to-right
                positioned_elements.sort(key=lambda x: (x['top'], x['left']))
                
                print(f"🔍 Found {len(positioned_elements)} positioned elements")
                print(f"📋 Reading order sequence (first 10):")
                
                # Analyze reading order patterns
                left_column_elements = []
                right_column_elements = []
                page_width_threshold = 300  # Approximate middle of page
                
                for idx, elem_info in enumerate(positioned_elements[:15]):  # Show first 15 elements
                    elem = elem_info['element']
                    label = elem_info['label']
                    text = elem_info['text']
                    top = elem_info['top']
                    left = elem_info['left']
                    
                    # Determine if left or right column
                    column = "LEFT" if left < page_width_threshold else "RIGHT"
                    if left < page_width_threshold:
                        left_column_elements.append(elem_info)
                    else:
                        right_column_elements.append(elem_info)
                    
                    print(f"  {idx+1:2d}. [{column:5}] {label:15} (y:{top:3.0f}, x:{left:3.0f}) {text}")
                
                # Multi-column analysis
                print(f"\n📊 MULTI-COLUMN ANALYSIS:")
                print(f"  📍 Left column elements: {len(left_column_elements)}")
                print(f"  📍 Right column elements: {len(right_column_elements)}")
                
                if len(left_column_elements) > 0 and len(right_column_elements) > 0:
                    print(f"  ✅ Multi-column layout detected!")
                    
                    # Check if reading order respects columns
                    print(f"\n🔄 READING ORDER VALIDATION:")
                    print(f"  📖 Does Docling read left column first, then right?")
                    
                    # Simplified check: are left column elements generally before right column elements?
                    left_positions = [positioned_elements.index(elem) for elem in positioned_elements if elem in left_column_elements and elem in positioned_elements[:10]]
                    right_positions = [positioned_elements.index(elem) for elem in positioned_elements if elem in right_column_elements and elem in positioned_elements[:10]]
                    
                    if left_positions and right_positions:
                        avg_left_pos = sum(left_positions) / len(left_positions)
                        avg_right_pos = sum(right_positions) / len(right_positions)
                        
                        if avg_left_pos < avg_right_pos:
                            print(f"  ✅ Correct: Left column (avg pos {avg_left_pos:.1f}) before right column (avg pos {avg_right_pos:.1f})")
                        else:
                            print(f"  ⚠️  Questionable: Right column (avg pos {avg_right_pos:.1f}) before left column (avg pos {avg_left_pos:.1f})")
                
                # Footnote detection with position analysis
                print(f"\n📝 FOOTNOTE ANALYSIS:")
                footnote_indicators = ['*', '†', '‡', '§', '¶', '(1)', '(2)', '(3)', 'See footnote', 'Note:']
                footnote_elements = []
                
                for elem_info in positioned_elements:
                    text = elem_info['text']
                    if any(indicator in text for indicator in footnote_indicators):
                        footnote_elements.append(elem_info)
                
                if footnote_elements:
                    print(f"  📌 Found {len(footnote_elements)} potential footnote elements")
                    for fn in footnote_elements[:3]:  # Show first 3 footnotes
                        print(f"    • {fn['text']} (y:{fn['top']:.0f})")
                else:
                    print(f"  📌 No footnotes detected on this page")
                
                # Table reading order analysis
                table_elements = [e for e in positioned_elements if 'table' in str(e['label']).lower()]
                if table_elements:
                    print(f"\n📊 TABLE ANALYSIS:")
                    print(f"  📋 Found {len(table_elements)} table elements")
                    for table in table_elements[:2]:
                        print(f"    📊 Table at position (y:{table['top']:.0f}, x:{table['left']:.0f})")
                        # Could analyze table cell reading order here
                
                print(f"-" * 40)
    
    def _analyze_critical_features(self, doc_dict, doc_name):
        """Critical analysis of reading order, table merging, and formulas"""
        import re
        
        print(f"\n🎯 CRITICAL FEATURES ANALYSIS: {doc_name}")
        print("=" * 70)
        
        # 1. READING ORDER ANALYSIS
        print(f"\n📖 1. READING ORDER & MULTI-COLUMN FLOWS")
        print("-" * 50)
        
        body = doc_dict.get('body', {})
        children = body.get('children', [])
        
        print(f"📋 Document reading sequence: {len(children)} elements")
        
        # Show reading sequence pattern
        sequence_types = []
        for i, child in enumerate(children[:20]):
            ref = child.get('$ref', '')
            element_type = ref.split('/')[1] if '/' in ref else 'unknown'
            element_id = ref.split('/')[-1] if '/' in ref else 'unknown'
            sequence_types.append(element_type)
            
            if i < 15:  # Show first 15
                print(f"  {i+1:2d}. {element_type:8} #{element_id}")
        
        # Analyze multi-column patterns
        text_sequence = [(i, ref) for i, ref in enumerate([(child.get('$ref', '')) for child in children[:50]]) if 'texts/' in ref]
        if len(text_sequence) > 5:
            text_ids = []
            for _, ref in text_sequence:
                try:
                    text_id = int(ref.split('/')[-1])
                    text_ids.append(text_id)
                except:
                    continue
            
            consecutive = sum(1 for i in range(1, len(text_ids)) if text_ids[i] - text_ids[i-1] == 1)
            large_jumps = sum(1 for i in range(1, len(text_ids)) if text_ids[i] - text_ids[i-1] > 10)
            
            print(f"📊 Multi-column analysis:")
            print(f"  • Consecutive text blocks: {consecutive}")
            print(f"  • Large ID jumps (>10): {large_jumps}")
            
            if large_jumps > 2:
                print(f"  ⚠️  Multi-column jumping detected - reading order may cross columns")
            else:
                print(f"  ✅ Linear reading order maintained")
        
        # 2. TABLE STRUCTURE & CELL MERGING
        print(f"\n📊 2. TABLE STRUCTURE & CELL MERGING")
        print("-" * 50)
        
        tables = doc_dict.get('tables', [])
        print(f"📋 Found {len(tables)} tables")
        
        total_merged_cells = 0
        for i, table in enumerate(tables[:3]):  # Analyze first 3 tables
            print(f"\n--- TABLE {i+1} ---")
            
            if 'data' in table and isinstance(table['data'], dict):
                data = table['data']
                if 'table_cells' in data:
                    cells = data['table_cells']
                    print(f"📋 Cells: {len(cells)}")
                    
                    # Check for merged cells
                    merged_count = 0
                    for cell in cells[:20]:  # Check first 20 cells
                        if isinstance(cell, dict):
                            rowspan = cell.get('rowspan', 1)
                            colspan = cell.get('colspan', 1)
                            if rowspan > 1 or colspan > 1:
                                merged_count += 1
                                total_merged_cells += 1
                                text = cell.get('text', '')[:30] + '...' if len(cell.get('text', '')) > 30 else cell.get('text', '')
                                print(f"    🔗 Merged cell: {rowspan}×{colspan} - {text}")
                    
                    if merged_count == 0:
                        print(f"    📋 No merged cells detected in sample")
                
                # Check grid structure
                if 'grid' in data:
                    grid = data['grid']
                    if isinstance(grid, list) and len(grid) > 0:
                        print(f"    📊 Grid: {len(grid)} rows × {len(grid[0]) if grid[0] else 0} cols")
        
        print(f"\n📊 TABLE MERGING SUMMARY:")
        print(f"  🔗 Total merged cells found: {total_merged_cells}")
        if total_merged_cells > 0:
            print(f"  ✅ Docling correctly identifies merged cells")
        else:
            print(f"  ⚠️  No merged cells detected - may not handle complex tables")
        
        # 3. FORMULA & MATHEMATICAL CONTENT
        print(f"\n🧮 3. FORMULAS & MATHEMATICAL EXPRESSIONS")
        print("-" * 50)
        
        texts = doc_dict.get('texts', [])
        
        # Mathematical patterns to detect
        formula_patterns = [
            (r'\$[\d,]+(?:\.\d{2})?', 'Dollar amounts'),
            (r'\d+\.\d+%', 'Percentages'),
            (r'\$[^$]*\$', 'LaTeX inline math'),
            (r'\\[a-zA-Z]+', 'LaTeX commands'),
            (r'\d+\s*[×*]\s*\d+', 'Multiplication'),
            (r'\d+\s*/\s*\d+', 'Fractions'),
            (r'[=≈≠≤≥]', 'Math operators'),
            (r'\([0-9,]+\)', 'Parenthetical numbers')
        ]
        
        formula_findings = {pattern[1]: 0 for pattern in formula_patterns}
        sample_formulas = {pattern[1]: [] for pattern in formula_patterns}
        
        for i, text in enumerate(texts[:200]):  # Check first 200 texts
            text_content = text.get('text', '')
            
            for pattern, name in formula_patterns:
                matches = re.findall(pattern, text_content)
                if matches:
                    formula_findings[name] += len(matches)
                    if len(sample_formulas[name]) < 3:  # Keep first 3 examples
                        sample_formulas[name].extend(matches[:3])
        
        print(f"🔍 Scanned {min(200, len(texts))} text elements")
        
        total_math_content = sum(formula_findings.values())
        if total_math_content > 0:
            print(f"📊 Mathematical content detected:")
            for name, count in formula_findings.items():
                if count > 0:
                    examples = sample_formulas[name][:2]
                    examples_str = f" (e.g., {', '.join(examples)})" if examples else ""
                    print(f"  • {name}: {count}{examples_str}")
        else:
            print(f"❌ No mathematical formulas detected")
        
        # Check for dedicated equation elements
        equations = doc_dict.get('equations', [])
        if equations:
            print(f"🧮 Dedicated equation elements: {len(equations)}")
        
        # 4. FOOTNOTE ANALYSIS
        print(f"\n📝 4. FOOTNOTE HANDLING")
        print("-" * 50)
        
        footnote_indicators = ['*', '†', '‡', '§', '¶', '(1)', '(2)', '(3)', 'See footnote', 'Note:', 'footnote']
        footnote_texts = []
        
        for i, text in enumerate(texts[:100]):
            text_content = text.get('text', '')
            if any(indicator in text_content for indicator in footnote_indicators):
                footnote_texts.append({
                    'id': i,
                    'text': text_content[:100] + '...' if len(text_content) > 100 else text_content
                })
        
        if footnote_texts:
            print(f"📌 Found {len(footnote_texts)} potential footnote elements:")
            for fn in footnote_texts[:3]:
                print(f"  • Text #{fn['id']}: {fn['text']}")
        else:
            print(f"📌 No footnotes detected")
        
        print(f"\n🎯 CRITICAL FEATURES SUMMARY:")
        print(f"  📖 Reading order: {'Multi-column aware' if large_jumps > 2 else 'Linear flow'}")
        print(f"  📊 Table merging: {'Detected' if total_merged_cells > 0 else 'Not found'}")
        print(f"  🧮 Math content: {total_math_content} expressions found")
        print(f"  📝 Footnotes: {len(footnote_texts)} potential footnotes")

    def parse_pdf_to_terminal(self, pdf_path: str):
        pdf_path = Path(pdf_path)
        
        print(f"\n🔄 Processing: {pdf_path.name}")
        if self.max_pages:
            print(f"📄 Limited to first {self.max_pages} pages")
        
        # Run docling converter
        result = self.converter.convert(pdf_path)

        # Export to dict
        doc_dict = result.document.export_to_dict()
        
        # Debug: Check structure
        print(f"\n🔍 DEBUG: Document structure keys: {list(doc_dict.keys())}")
        
        # Print structured results to terminal
        print(f"\n📊 DOCLING RESULTS FOR: {pdf_path.name}")
        print("=" * 60)
        
        # Check main structure
        if hasattr(result.document, 'pages'):
            print(f"📄 Document has {len(result.document.pages)} pages")
            
            # Limit pages to display
            pages_to_process = min(len(result.document.pages), self.max_pages) if self.max_pages else len(result.document.pages)
            print(f"📄 Showing first {pages_to_process} pages")
            
            for i in range(pages_to_process):
                page = result.document.pages[i]
                print(f"\n--- PAGE {i+1} ---")
                
                # Get page content
                page_dict = page.export_to_dict() if hasattr(page, 'export_to_dict') else {}
                
                # Show basic info
                print(f"📄 Page {i+1} content keys: {list(page_dict.keys()) if page_dict else 'No keys'}")
                
                # Try to get text content
                if hasattr(page, 'text') and page.text:
                    text_preview = page.text[:200] + "..." if len(page.text) > 200 else page.text
                    print(f"📝 Text preview: {text_preview}")
                
                # Try to get elements
                if hasattr(page, 'elements'):
                    print(f"🧩 Elements found: {len(page.elements)}")
                    for j, element in enumerate(page.elements[:3]):  # Show first 3 elements
                        if hasattr(element, 'text') and element.text:
                            element_text = element.text[:80] + "..." if len(element.text) > 80 else element.text
                            print(f"  Element {j+1}: {element_text}")
                
                print("-" * 40)
        
        # Summary
        print(f"\n✅ Processing complete for {pdf_path.name}")
        return doc_dict


if __name__ == "__main__":
    # Initialize parser for analysis
    parser = DoclingParser()
    
    # Analyze existing JSON files for critical features
    docling_dir = Path("data/parsed/docling")
    json_files = list(docling_dir.glob("*.json"))
    
    if not json_files:
        print(f"❌ No existing Docling JSON files found!")
        print(f"📁 Expected files in: {docling_dir}")
        exit(1)
    
    print(f"🎯 DOCLING CRITICAL FEATURES ANALYSIS")
    print(f"📋 Focus: Reading Order, Table Merging, Formulas, Footnotes")
    print(f"📁 Analyzing existing JSON files: {[f.name for f in json_files]}")
    
    for i, json_file in enumerate(json_files, 1):
        print(f"\n{'='*80}")
        print(f"📄 DOCUMENT {i}/{len(json_files)}: {json_file.name}")
        print(f"{'='*80}")
        
        try:
            # Load existing JSON data
            with open(json_file, 'r', encoding='utf-8') as f:
                doc_dict = json.load(f)
            
            doc_name = doc_dict.get('name', json_file.stem)
            
            # Run critical features analysis
            parser._analyze_critical_features(doc_dict, doc_name)
            
            # Generate Markdown if it doesn't exist
            md_file = docling_dir / f"{json_file.stem}.md"
            if not md_file.exists():
                print(f"\n📝 Markdown file not found, checking for conversion capability...")
                # Note: Markdown conversion requires the document object, not just JSON
            else:
                print(f"\n📝 Markdown file exists: {md_file}")
            
            print(f"✅ Analysis complete for {json_file.name}")
            
        except Exception as e:
            print(f"❌ Error analyzing {json_file.name}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🎉 CRITICAL ANALYSIS COMPLETE!")
    print(f"📊 Key findings on reading order, table merging, and formulas shown above")
    print(f"📝 Compare with our custom pdfplumber+LayoutParser pipeline results")
