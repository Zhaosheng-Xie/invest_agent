"""Step 2c: 单独拉取 002428 公告并灌入"""
import sys
import time
sys.path.insert(0, "src")

from sandboxes.data.cninfo_client import query_all_announcements, query_announcements
from sandboxes.data.duckdb_store import upsert, query_safe

DB = "data/duckdb/market.duckdb"

print("=" * 60)
print("拉取 002428 近期公告")
print("=" * 60)

# 先用 query_announcements 看看 002428 有哪些公告
result = query_announcements(stock="002428", start_date="20260301", end_date="20260430")
print(f"Status: {result['status']}")
print(f"Total count: {result.get('total_count', 0)}")
print(f"Data count: {len(result.get('data', []))}")
if result['status'] == 'ok' and result['data']:
    for ann in result['data'][:20]:
        print(f"  [{ann.get('ann_date')}] {ann.get('title')[:80]} | {ann.get('category')}")
    
    # 写入 DuckDB
    upsert("announcements", result['data'], ["ts_code", "ann_date", "title"], db_path=DB)
    print(f"\n已写入 {len(result['data'])} 条到 DuckDB")

# 翻页拉取更多
time.sleep(2)
all_anns = query_all_announcements(stock="002428", start_date="20260301", end_date="20260430", max_pages=5)
print(f"\n全量拉取: {len(all_anns)} 条")
if all_anns:
    upsert("announcements", all_anns, ["ts_code", "ann_date", "title"], db_path=DB)
    print("已写入 DuckDB")

# 验证
print("\n验证 002428 公告入库情况:")
try:
    rows = query_safe(
        "SELECT * FROM announcements WHERE ts_code LIKE $1 ORDER BY ann_date DESC LIMIT 20",
        ["%002428%"],
        db_path=DB,
    )
    print(f"找到 {len(rows)} 条:")
    for r in rows:
        print(f"  [{r.get('ann_date')}] {r.get('title')[:70]} | {r.get('category')}")
except Exception as e:
    print(f"ERROR: {e}")
