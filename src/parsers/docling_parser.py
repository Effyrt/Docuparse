from pathlib import Path
import json
from docling.document_converter import DocumentConverter

class DoclingParser:
    def __init__(self, output_dir: str = "data/parsed/docling"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.converter = DocumentConverter()

    def parse_pdf(self, pdf_path: str):
        pdf_path = Path(pdf_path)

        # Run docling converter
        result = self.converter.convert(pdf_path)

        # export_to_dict()
        doc_dict = result.document.export_to_dict()

        # Save output
        out_file = self.output_dir / f"{pdf_path.stem}_docling.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(doc_dict, f, indent=2, ensure_ascii=False)

        print(f"[DoclingParser] Saved parsed output to {out_file}")
        return out_file


if __name__ == "__main__":
    parser = DoclingParser()

    pdf_files = [
        "data/raw/10-K.pdf",
        "data/raw/10-Q.pdf",
    ]

    for pdf in pdf_files:
        parser.parse_pdf(pdf)
