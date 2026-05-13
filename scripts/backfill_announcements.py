"""回填 2026 年全量公告标题到 DuckDB。"""
import sys
import time

sys.path.insert(0, "d:\\a_stock_agent\\src")

from sandboxes.data.cninfo_client import query_all_announcements
from sandboxes.data.duckdb_store import upsert

DB_PATH = "data/duckdb/market.duckdb"

months = [
    ("20260101", "20260131"),
    ("20260201", "20260228"),
    ("20260301", "20260331"),
    ("20260401", "20260430"),
    ("20260501", "20260512"),
]

total = 0
for start, end in months:
    print(f"拉取 {start} ~ {end} ...")
    anns = query_all_announcements(start_date=start, end_date=end, max_pages=200)
    if anns:
        count = upsert("announcements", anns, ["ts_code", "ann_date", "title"], db_path=DB_PATH)
        total += count
        print(f"  入库 {count} 条")
    time.sleep(3)

print(f"\n总计入库 {total} 条公告")
