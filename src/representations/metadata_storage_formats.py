import json
from pathlib import Path

def convert_metadata(input_file: Path, output_dir: Path):
    
    # read JSONL
    records = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    # (delete _metadata.jsonl)
    base_name = input_file.stem.replace("_metadata", "")

    # --- 1. Markdown ---
    md_path = output_dir / f"{base_name}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Parsed Metadata Representation for {base_name}\n\n")
        current_page = None
        for rec in records:
            page = rec.get("page", -1)
            if page != current_page:
                current_page = page
                f.write(f"\n---\n\n## Page {page}\n\n")
            f.write(f"- ({rec['block_type']}) {rec['text']}\n")
    print(f"[Part6] Saved Markdown → {md_path}")

    # --- 2. JSON ---
    json_path = output_dir / f"{base_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"[Part6] Saved JSON → {json_path}")

    # --- 3. TXT ---
    txt_path = output_dir / f"{base_name}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(rec.get("text", "") + "\n")
    print(f"[Part6] Saved TXT → {txt_path}")


if __name__ == "__main__":
    input_dir = Path(r"C:\Users\Pauline\Desktop\PEI\NEU_assignments\DAMG 7245_(2025 Fall)\data\parsed\metadata")
    output_dir = Path(r"C:\Users\Pauline\Desktop\PEI\NEU_assignments\DAMG 7245_(2025 Fall)\data\parsed\metadata_representations")
    output_dir.mkdir(parents=True, exist_ok=True)

    # find all JSONL files
    jsonl_files = list(input_dir.glob("*.jsonl"))
    if not jsonl_files:
        print(f"[Part6] ❌ didn't find any JSONL files in {input_dir}")
    else:
        for file in jsonl_files:
            convert_metadata(file, output_dir)
