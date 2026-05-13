"""Step 4: 灌入 20260407 数据并验证研报在 DuckDB。"""
import sys
sys.path.insert(0, "src")

from harness.daily_data_prep import run_daily_prep

# 先跑 20260407 的数据灌入
print("=== Running daily_prep for 20260407 ===")
try:
    stats = run_daily_prep("20260407")
    print(f"Stats: {stats}")
except Exception as e:
    print(f"daily_prep failed: {e}")
    # 可能不是交易日，试 20260408
    print("\n=== Trying 20260408 ===")
    try:
        stats = run_daily_prep("20260408")
        print(f"Stats: {stats}")
    except Exception as e2:
        print(f"20260408 also failed: {e2}")

# 检查 DuckDB 中的研报数据
print("\n=== Checking research_report in DuckDB ===")
from sandboxes.data.duckdb_store import query_safe
try:
    rows = query_safe(
        "SELECT title, inst_csname, trade_date FROM research_report "
        "WHERE (ts_code LIKE $1 OR name LIKE $2) AND trade_date >= $3 "
        "ORDER BY trade_date DESC LIMIT 10",
        ["%002428%", "%云南锗业%", "20260401"],
        db_path="data/duckdb/market.duckdb"
    )
    print(f"Found {len(rows)} reports for 002428:")
    for r in rows:
        print(f"  [{r['trade_date']}] {r['inst_csname']} | {r['title']}")
except Exception as e:
    print(f"Query failed: {e}")
