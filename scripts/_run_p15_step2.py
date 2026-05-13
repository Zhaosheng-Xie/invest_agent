"""Step 2: 灌入 20260404 公告数据"""
import sys
import time
sys.path.insert(0, "src")

from sandboxes.data.cninfo_client import query_all_announcements
from sandboxes.data.duckdb_store import upsert, query_safe

DB = "data/duckdb/market.duckdb"


def step2a_ingest_announcements():
    """灌入 20260404 公告数据（巨潮 API）"""
    print("=" * 60)
    print("STEP 2a: 灌入 20260404 公告数据")
    print("=" * 60)

    # 拉取 20260401~20260404 的公告（覆盖更广范围）
    for date_range in [("20260401", "20260404"), ("20260404", "20260407")]:
        start, end = date_range
        print(f"\n拉取 {start}~{end} 公告...")
        try:
            anns = query_all_announcements(start_date=start, end_date=end, max_pages=10)
            print(f"  获取 {len(anns)} 条公告")
            if anns:
                upsert("announcements", anns, ["ts_code", "ann_date", "title"], db_path=DB)
                print(f"  已写入 DuckDB")
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(2)

    # 验证
    try:
        count = query_safe('SELECT COUNT(*) as cnt FROM announcements', db_path=DB)
        print(f"\nannouncements 总行数: {count[0]['cnt']}")
    except Exception as e:
        print(f"\n验证失败: {e}")


def step2b_check_002428():
    """验证 002428 公告是否已入库"""
    print("\n" + "=" * 60)
    print("STEP 2b: 验证 002428 公告")
    print("=" * 60)

    try:
        rows = query_safe(
            "SELECT * FROM announcements WHERE ts_code LIKE $1 AND ann_date >= $2 ORDER BY ann_date DESC LIMIT 20",
            ["%002428%", "20260401"],
            db_path=DB,
        )
        print(f"找到 {len(rows)} 条 002428 公告:")
        for r in rows:
            print(f"  [{r.get('ann_date')}] {r.get('title')[:60]} | {r.get('category')}")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    step2a_ingest_announcements()
    step2b_check_002428()
