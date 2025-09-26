# Part 6: Storage Format Comparison

## Formats Evaluated
The assignment’s objective is to build a financial report parsing pipeline for automating the ingestion and analysis of SEC filings. Within this context, the choice of storage format is guided primarily by usability and structural preservation.

We compared three storage formats for the parsed SEC filings metadata:

1. **JSON**   
   - Pros: Highly structured, machine-readable, and well-suited for automated processing and downstream analytics.  
   - Cons: Repetitive key-value pairs make the format verbose and less convenient for quick human review.  

2. **Markdown**  
   - Pros: Preserves structural elements such as headings, lists, and tables. Readable for humans and effective in LLM-driven retrieval pipelines.  
   - Cons: Not as standardized for programmatic parsing compared to JSON.  

3. **TXT**  
   - Pros: Extremely simple, lightweight, and universally supported.  
   - Cons: Strips away all structure, limiting its usefulness for complex analysis or retrieval tasks.  

## File Size Considerations
We also compared the relative file sizes of the three formats:

- **JSON**: Typically the largest due to repeated keys like `doc_id`, `page`, `block_type`, and `text`.  
  - On average, JSON requires about twice the storage space of Markdown.  

- **Markdown**: More compact, since it retains structure without redundant key labels.  
  - Generally smaller than JSON while still being human-friendly.  

- **TXT**: The most lightweight option, consisting only of raw text.  
  - However, it eliminates semantic structure, reducing overall utility.  

Although storage differences are not critical in practice, they highlight Markdown’s advantage: it is significantly smaller than JSON while retaining essential structure, making it a practical middle ground.

## Decision
For the pipeline, we chose **Markdown** as the primary storage format.  
- It offers an optimal balance between readability and semantic structure.  
- It supports both human inspection and integration into LLM-based RAG workflows.  

We will retain **JSON** as a secondary format for programmatic needs.  
**TXT** will serve only as a baseline reference and will not be used in subsequent stages.  
This decision aligns with the overall pipeline goal of Project LANTERN—streamlining the ingestion and analysis of financial filings for more efficient and accurate workflows.
