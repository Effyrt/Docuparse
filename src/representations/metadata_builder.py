import json
from pathlib import Path

class MetadataBuilder:
    def __init__(self, output_dir="data/parsed/metadata", company="Meta", fiscal_year=2023):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.company = company
        self.fiscal_year = fiscal_year

    def _make_record(self, doc_id, block_type, page, bbox, text, source_path):
        return {
            "doc_id": doc_id,
            "company": self.company,
            "fiscal_year": self.fiscal_year,
            "page": page,
            "block_type": block_type,
            "bbox": bbox,
            "text": text.strip() if text else "",
            "source_path": source_path,
        }

    def build_metadata(self, json_path, doc_id):
        with open(json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        records = []

        #  iterate texts
        for i, node in enumerate(doc.get("texts", [])):
            records.append(self._make_record(
                doc_id, "text",
                node.get("page_no", -1),
                node.get("bbox", []),
                node.get("text", ""),
                f"#/texts/{i}"
            ))

        #  iterate tables
        for i, node in enumerate(doc.get("tables", [])):
            records.append(self._make_record(
                doc_id, "table",
                node.get("page_no", -1),
                node.get("bbox", []),
                "[TABLE]",
                f"#/tables/{i}"
            ))

        #  iterate pictures
        for i, node in enumerate(doc.get("pictures", [])):
            records.append(self._make_record(
                doc_id, "picture",
                node.get("page_no", -1),
                node.get("bbox", []),
                "[PICTURE]",
                f"#/pictures/{i}"
            ))

        # ✅ save JSONL
        out_jsonl = self.output_dir / f"{doc_id}_metadata.jsonl"
        with open(out_jsonl, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[MetadataBuilder] Saved metadata to {out_jsonl} ({len(records)} records)")

        # ✅ save Markdown summary
        out_md = self.output_dir / f"{doc_id}_provenance.md"
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(f"# Provenance Summary for {doc_id}\n\n")
            current_page = None
            for r in sorted(records, key=lambda x: (x["page"], x["block_type"])):
                if r["page"] != current_page:
                    current_page = r["page"]
                    f.write(f"\n---\n\n## Page {current_page}\n\n")
                f.write(f"- ({r['block_type']}) {r['text']}\n")
        print(f"[MetadataBuilder] Saved provenance to {out_md}")

        return records


if __name__ == "__main__":
    builder = MetadataBuilder(company="Meta", fiscal_year=2023)
    docs = [
        ("data/parsed/docling/10-K_docling.json", "10-K"),
        ("data/parsed/docling/10-Q_docling.json", "10-Q"),
    ]
    for path, doc_id in docs:
        builder.build_metadata(path, doc_id)
