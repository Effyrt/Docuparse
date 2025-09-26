from pathlib import Path
import json
from docling.document_converter import DocumentConverter


class DoclingOrFallbackParser:
    """
    Parser that tries Docling first.
    If Docling fails or returns empty results, it falls back to Google Document AI OCR.
    """
    def __init__(self,
                 output_dir: str = "data/parsed/docling_or_fallback",
                 project_id: str = None,
                 location: str = "us",
                 processor_id: str = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.converter = DocumentConverter()
        # 注意：這裡不會初始化 Google Client，等 fallback 時才會用到
        self.project_id = project_id
        self.location = location
        self.processor_id = processor_id

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

            # Step 2: Fallback to Google OCR, 這裡才初始化 client
            if self.project_id and self.processor_id:
                try:
                    from docai_parser import DocAIOCRParser
                    docai_parser = DocAIOCRParser(self.project_id,
                                                  self.location,
                                                  self.processor_id)
                    if page_num:
                        return docai_parser.parse_pdf_page(pdf_path, page_num=page_num)
                    else:
                        return docai_parser.parse_pdf(pdf_path)
                except Exception as e2:
                    print(f"[Error] Google OCR fallback also failed: {e2}")
                    return None
            else:
                print("[Warning] Google OCR not configured, returning None.")
                return None


if __name__ == "__main__":
    parser = DoclingOrFallbackParser(
        output_dir="data/parsed/docling_or_fallback",
        project_id="meta-spirit-473302-c9",   # ⚠️ 可選
        location="us",
        processor_id="1c6b7902565b2358"
    )

    # 掃描 data/raw 下面的所有 PDF
    raw_dir = Path("data/raw")
    pdf_files = list(raw_dir.glob("*.pdf"))

    for pdf_file in pdf_files:
        print(f"🚀 Parsing {pdf_file} ...")
        parser.parse_pdf(pdf_file)


