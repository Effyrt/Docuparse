# Part 7 — Build vs Buy Experiment

## 📊 Side-by-side Comparison (10-K Page 75)

| Aspect | Docling (Open-source) | Google Document AI – OCR | Google Document AI – Form Parser |
|--------|------------------------|---------------------------|----------------------------------|
| **Text Extraction Quality** | Paragraphs are readable, but numbers sometimes break across lines | Paragraphs and numbers are continuous and accurate, close to the original PDF | Outputs structured tables rather than plain text |
| **Table Structure** | Tables treated as indented text, no row/column structure | Tables appear as text blocks, difficult to convert to CSV | Tables fully structured (row/col/cell with boundingPoly coordinates) |
| **Output Format** | JSON (custom schema) | JSON (text blocks + bounding boxes) | JSON (tables → headerRows, bodyRows, cells, boundingPoly) |
| **Cost** | Free | ~$1.50 / 1,000 pages | ~$30 / 1,000 pages |
| **Privacy** | Runs locally, no data transfer | Requires upload to Google Cloud (compliant with regulations) | Same as OCR, processed on Google Cloud |

---

## 📌 Discussion
- **Docling**: Free and local, suitable for most filings, but weak in table parsing.  
- **Google OCR**: High text accuracy, recommended as a fallback for OCR.  
- **Google Form Parser**: Provides the best structured tables (ideal for financial data), but has the highest cost.  

👉 **Recommendation**:  
Use **Docling as the default** pipeline. For **low-quality scans or table-heavy pages**, enable **Google Document AI - OCR** as a fallback. 

## 🛠️ Implementation Note
We implemented a combined script `docling_or_fallback_parser.py`.  
- The parser first tries **Docling** (open-source pipeline).  
- If Docling fails or produces no pages, it automatically falls back to **Google Document AI OCR** (`docai_parser.py`).  
- Outputs are saved in `data/parsed/fallback_output/`.
