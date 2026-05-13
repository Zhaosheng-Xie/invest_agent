"""检查 002428 在 20260404 及之前/之后可用的时间线数据。"""
import sys
sys.path.insert(0, "src")
from sandboxes.data.tushare_client import _get_pro

pro = _get_pro()

# 1. report_rc 全量时间线
print("=" * 60)
print("1. report_rc 时间线（全量）")
print("=" * 60)
try:
    df = pro.report_rc(ts_code="002428.SZ")
    print(f"  总记录: {len(df)}")
    for _, row in df.iterrows():
        date = row.get("report_date", "")
        mark = " <<<< 20260404之后" if str(date) > "20260404" else ""
        print(f"  [{date}] {row.get('org_name', '')} | {row.get('rating', '')} | {row.get('report_title', '')}{mark}")
except Exception as e:
    print(f"  ERROR: {e}")

# 2. stk_surv 20260404之前的调研
print("\n" + "=" * 60)
print("2. stk_surv 20260404之前的调研")
print("=" * 60)
try:
    df = pro.stk_surv(ts_code="002428.SZ")
    before = df[df["surv_date"] <= "20260404"] if "surv_date" in df.columns else df
    print(f"  20260404之前: {len(before)} 条")
    for _, row in before.tail(10).iterrows():
        orgs = str(row.get("rece_org", ""))[:80]
        print(f"  [{row.get('surv_date', '')}] {row.get('org_type', '')} | {orgs}")
except Exception as e:
    print(f"  ERROR: {e}")

# 3. announcements 时间线 - 检查有没有"投资者关系"类公告
print("\n" + "=" * 60)
print("3. DuckDB announcements 中'投资者关系/调研'类公告")
print("=" * 60)
try:
    from sandboxes.data.duckdb_store import query_safe
    db = "data/duckdb/market.duckdb"
    rows = query_safe(
        "SELECT ann_date, title, ts_code FROM announcements "
        "WHERE (title LIKE '%投资者关系%' OR title LIKE '%调研%' OR title LIKE '%活动记录%') "
        "AND ts_code LIKE '%002428%' "
        "ORDER BY ann_date DESC LIMIT 10",
        db_path=db,
    )
    if rows:
        for r in rows:
            print(f"  [{r.get('ann_date', '')}] {r.get('title', '')}")
    else:
        print("  无匹配公告")
        rows2 = query_safe(
            "SELECT ann_date, title, ts_code FROM announcements "
            "WHERE title LIKE '%投资者关系活动记录%' "
            "ORDER BY ann_date DESC LIMIT 5",
            db_path=db,
        )
        if rows2:
            print("  全市场'投资者关系活动记录'公告样例:")
            for r in rows2:
                print(f"    [{r.get('ann_date', '')}] {r.get('ts_code', '')} | {r.get('title', '')}")
except Exception as e:
    print(f"  ERROR: {e}")

# 4. 关键时间节点
print("\n" + "=" * 60)
print("4. 关键时间节点对比")
print("=" * 60)
print("  20260402: 2025年年度报告摘要 + 化合物半导体业务进展自愿披露")
print("  20260403: 磷化铟单晶片建设项目公告 + InP可行性分析报告")
print("  20260404: 第九届董事会决议公告 + 建设项目公告(重复)")
print("  20260407: report_rc 买入评级研报 (look-ahead, 20260404不可用)")
print("  20260425: report_rc 买入评级研报 x3")
print("  20260507: 最近一次机构调研")
