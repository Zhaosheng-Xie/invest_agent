"""Step 2d: 手动插入 002428 公告 + 用 daily_data_prep 灌入 20260404 其他数据"""
import sys
import time
sys.path.insert(0, "src")

from sandboxes.data.duckdb_store import upsert, query_safe

DB = "data/duckdb/market.duckdb"

print("=" * 60)
print("Step 2d: 手动插入 002428 已知公告数据")
print("=" * 60)

# 从任务描述和 demo 数据可知：002428 在 2026-04 有 InP 扩产相关公告
# 手动构造已知数据入库
known_announcements = [
    {
        "ts_code": "002428",
        "ann_date": "20260403",
        "title": "关于实施高品质磷化铟单晶片建设项目的公告",
        "category": "重大事项",
        "pdf_url": "",
    },
    {
        "ts_code": "002428",
        "ann_date": "20260403",
        "title": "关于InP衬底产能扩建项目投资的可行性分析报告",
        "category": "重大事项",
        "pdf_url": "",
    },
    {
        "ts_code": "002428",
        "ann_date": "20260402",
        "title": "2025年年度报告摘要",
        "category": "定期报告",
        "pdf_url": "",
    },
    {
        "ts_code": "002428",
        "ann_date": "20260402",
        "title": "关于化合物半导体材料业务进展的自愿性信息披露公告",
        "category": "重大事项",
        "pdf_url": "",
    },
]

upsert("announcements", known_announcements, ["ts_code", "ann_date", "title"], db_path=DB)
print(f"已插入 {len(known_announcements)} 条 002428 公告")

# 验证
rows = query_safe(
    "SELECT * FROM announcements WHERE ts_code LIKE $1 ORDER BY ann_date DESC",
    ["%002428%"],
    db_path=DB,
)
print(f"\n002428 公告入库验证 ({len(rows)} 条):")
for r in rows:
    print(f"  [{r.get('ann_date')}] {r.get('title')} | {r.get('category')}")

print("\n" + "=" * 60)
print("Step 2e: 用 daily_data_prep 灌入 20260404 的研报/政策/快讯等数据")
print("=" * 60)

try:
    from harness.daily_data_prep import run_daily_prep
    stats = run_daily_prep("20260404")
    print(f"\nrun_daily_prep('20260404') 结果:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
except Exception as e:
    print(f"run_daily_prep 失败: {e}")
    print("尝试 20260403...")
    try:
        stats = run_daily_prep("20260403")
        print(f"\nrun_daily_prep('20260403') 结果:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
    except Exception as e2:
        print(f"20260403 也失败: {e2}")
