import json
import sqlite3
from pathlib import Path

# SQLite 資料庫檔案路徑
DB_PATH = "data/parsed/metadata.db"

def init_db():
    """建立資料庫和 metadata 資料表（如果還不存在的話）"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id TEXT,
        company TEXT,
        fiscal_year INTEGER,
        page INTEGER,
        block_type TEXT,
        bbox TEXT,
        text TEXT,
        source_path TEXT
    )
    """)
    conn.commit()
    conn.close()

def load_jsonl_subset(jsonl_path, doc_id, limit=5):
    """讀取 JSONL 並插入前 N 行到資料庫"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= limit:   # 只匯前 N 行
                break
            record = json.loads(line)
            cur.execute("""
            INSERT INTO metadata (doc_id, company, fiscal_year, page, block_type, bbox, text, source_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                record.get("company"),
                record.get("fiscal_year"),
                record.get("page"),
                record.get("block_type"),
                json.dumps(record.get("bbox")),
                record.get("text"),
                record.get("source_path")
            ))
    conn.commit()
    conn.close()
    print(f"[DB Loader] 已匯入 {doc_id} 的前 {limit} 行到 DB")

def preview_records(n=5):
    """查詢 DB 中前 N 筆資料"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, doc_id, page, block_type, substr(text, 1, 50) as snippet
        FROM metadata
        LIMIT ?
    """, (n,))
    rows = cur.fetchall()
    conn.close()

    print("\n=== 預覽資料 (前 {} 筆) ===".format(n))
    for row in rows:
        print(row)

if __name__ == "__main__":
    init_db()
    load_jsonl_subset("data/parsed/metadata/10-K_metadata.jsonl", "10-K", limit=5)
    preview_records(5)  # 執行後自動顯示前 5 筆資料
