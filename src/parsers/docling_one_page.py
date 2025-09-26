from pathlib import Path
import json
from docling.document_converter import DocumentConverter

class DoclingOnePageParser:
    def __init__(self, output_dir: str = "data/parsed/docling_one_page_to_compare"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.converter = DocumentConverter()

    def parse_pdf(self, pdf_path: Path):
        # 用 Docling 解析這份單頁 PDF
        result = self.converter.convert(pdf_path)
        doc_dict = result.document.export_to_dict()

        # 儲存 JSON
        out_file = self.output_dir / f"{pdf_path.stem}_docling.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(doc_dict, f, indent=2, ensure_ascii=False)

        print(f"[DoclingOnePageParser] Saved parsed output to {out_file}")
        return out_file


if __name__ == "__main__":
    parser = DoclingOnePageParser()

    # 用相對路徑，不要寫 C:/Users...
    pdf_file = Path("data/parsed_buy_tool/10-K_one_page_for_tool_parse.pdf")
    parser.parse_pdf(pdf_file)
