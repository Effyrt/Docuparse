from pathlib import Path
import json
from google.cloud import documentai


class DocAIOCRParser:
    def __init__(self, project_id: str, location: str, processor_id: str, output_dir: str = "data/parsed/docai_output"):
        self.project_id = project_id
        self.location = location
        self.processor_id = processor_id

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.client = documentai.DocumentProcessorServiceClient()

    def parse_pdf_page(self, pdf_path: str, page_num: int):
        pdf_path = Path(pdf_path)

        # read PDF
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()

        # input to Google AI
        raw_document = documentai.RawDocument(content=pdf_content, mime_type="application/pdf")

        name = self.client.processor_path(self.project_id, self.location, self.processor_id)

        request = documentai.ProcessRequest(
            name=name,
            raw_document=raw_document
        )

        # call API
        result = self.client.process_document(request=request)

        document = result.document

        # download JSON
        out_file = self.output_dir / f"{pdf_path.stem}_page{page_num}_docai.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(output_dict, f, indent=2, ensure_ascii=False)

        print(f"[DocAIOCRParser] Saved parsed output to {out_file}")
        return out_file

#Connect to Google DocAI PROCESSOR_OCR_Parser
if __name__ == "__main__":

    PROJECT_ID = "meta-spirit-473302-c9"   
    LOCATION = "us"
    PROCESSOR_ID = "1c6b7902565b2358"

    parser = DocAIOCRParser(PROJECT_ID, LOCATION, PROCESSOR_ID)

    pdf_file = "data/parsed_buy_tool/10-K_one_page_for_tool_parse.pdf"
    parser.parse_pdf_page(pdf_file, page_num=75)
