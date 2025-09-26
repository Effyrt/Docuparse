from pathlib import Path
import json
from docling.document_converter import DocumentConverter
from docai_parser import DocAIOCRParser

class DoclingOrFallbackParser:
    """
    Parser that tries Docling first.
    If Docling fails or returns empty results, it falls back to Google Document AI OCR.
    """
    def __init__(self,
                 output_dir: str = "data/parsed/fallback_output",
                 project_id: str = "YOUR_PROJECT_ID",
                 location: str = "us",
                 processor_id: str = "YOUR_OCR_PROCESSOR_ID"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.converter = DocumentConverter()
        self.docai_parser = DocAIOCRParser(project_id, location, processor_id)

    def parse_pdf(self, pdf_path: str, page_num: int = None):
        pdf_path = Path(pdf_path)

        # Step 1: Try Docling
        try:
            result = self.converter.convert(pdf_path)
            doc_dict = result.document.export_to_dict()

            if not doc_dict.get("pages"):
                raise ValueError("Docling returned no pages")

            out_file = self.output_dir / f"{pdf_path.stem}_docling.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(doc_dict, f, indent=2, ensure_ascii=False)

            print(f"[DoclingOrFallbackParser] Saved Docling output to {out_file}")
            return out_file

        except Exception as e:
            print(f"[Fallback Triggered] Docling failed, switching to Google OCR: {e}")
            # Step 2: Fallback to Google OCR
            if page_num:
                return self.docai_parser.parse_pdf_page(pdf_path, page_num=page_num)
            else:
                return self.docai_parser.parse_pdf(pdf_path)


if __name__ == "__main__":

    PROJECT_ID = "meta-spirit-473302-c9"
    LOCATION = "us"
    PROCESSOR_ID = "1c6b7902565b2358"

    parser = DoclingOrFallbackParser(
        project_id=PROJECT_ID,
        location=LOCATION,
        processor_id=PROCESSOR_ID
    )

    pdf_file = "data/parsed_buy_tool/10-K_one_page_for_tool_parse.pdf"
    parser.parse_pdf(pdf_file, page_num=75)
