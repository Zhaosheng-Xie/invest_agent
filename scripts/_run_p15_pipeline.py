"""P1.5 完整 pipeline 执行脚本：灌入 20260404 数据 → signal_discovery → hypothesis_engine"""
import sys
import json
import time
sys.path.insert(0, "src")

from sandboxes.data.duckdb_store import query_safe, upsert

DB = "data/duckdb/market.duckdb"

def step1_check_db():
    """检查 DuckDB 数据状况"""
    print("=" * 60)
    print("STEP 1: 检查 DuckDB 数据状况")
    print("=" * 60)

    tables = query_safe(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'",
        db_path=DB
    )
    print(f"Tables: {[t['table_name'] for t in tables]}")

    for tbl in ['announcements', 'research_report', 'news', 'policy',
                'limit_list', 'moneyflow_cnt_ths', 'top_list', 'top_inst',
                'hm_list', 'ths_index_cache']:
        try:
            count = query_safe(f'SELECT COUNT(*) as cnt FROM "{tbl}"', db_path=DB)
            print(f"  {tbl}: {count[0]['cnt']} rows")
        except Exception as e:
            print(f"  {tbl}: NOT EXISTS or ERROR - {str(e)[:60]}")

    # 检查 announcements 日期范围
    try:
        dates = query_safe(
            'SELECT MIN("ann_date") as min_d, MAX("ann_date") as max_d FROM announcements',
            db_path=DB
        )
        print(f"\n  announcements 日期范围: {dates[0]['min_d']} ~ {dates[0]['max_d']}")
    except Exception:
        pass

    # 检查 research_report 日期范围
    try:
        dates = query_safe(
            'SELECT MIN("trade_date") as min_d, MAX("trade_date") as max_d FROM research_report',
            db_path=DB
        )
        print(f"  research_report 日期范围: {dates[0]['min_d']} ~ {dates[0]['max_d']}")
    except Exception:
        pass


if __name__ == "__main__":
    step1_check_db()
