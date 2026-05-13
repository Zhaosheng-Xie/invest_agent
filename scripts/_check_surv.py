"""检查 stk_surv / report_rc 等 P2 关键数据源可用性。"""
import sys
sys.path.insert(0, "src")
from sandboxes.data.tushare_client import _get_pro

pro = _get_pro()

# 1. stk_surv: 机构调研纪要
print("=" * 60)
print("1. stk_surv (机构调研纪要) - 002428.SZ")
print("=" * 60)
try:
    df = pro.stk_surv(ts_code="002428.SZ")
    print(f"  记录数: {len(df)}")
    if len(df) > 0:
        print(f"  列: {list(df.columns)}")
        for _, row in df.head(3).iterrows():
            print(f"  [{row.get('surv_date', '')}] visitors={row.get('fund_visitors', '')}")
            print(f"    org_type={row.get('org_type', '')}, rece_org={str(row.get('rece_org', ''))[:80]}")
            content = str(row.get("content", ""))
            print(f"    content({len(content)}字): {content[:200]}")
            print()
except Exception as e:
    print(f"  ERROR: {e}")

# 2. report_rc: 研报评级
print("\n" + "=" * 60)
print("2. report_rc (研报评级) - 002428.SZ")
print("=" * 60)
try:
    df = pro.report_rc(ts_code="002428.SZ", start_date="20260101", end_date="20260430")
    print(f"  记录数: {len(df)}")
    if len(df) > 0:
        print(f"  列: {list(df.columns)}")
        for _, row in df.head(5).iterrows():
            print(f"  [{row.get('report_date', '')}] {row.get('surv_org', '')} | rating={row.get('rating', '')} -> {row.get('pre_rating', '')} | {row.get('report_title', '')}")
except Exception as e:
    print(f"  ERROR: {e}")

# 3. research_report by ts_code: 个股研报（带摘要）
print("\n" + "=" * 60)
print("3. research_report (个股研报) - 002428.SZ")
print("=" * 60)
try:
    df = pro.research_report(
        ts_code="002428.SZ",
        start_date="20260101",
        fields="title,report_type,author,name,ts_code,inst_csname,ind_name,abstr,trade_date,url",
    )
    print(f"  记录数: {len(df)}")
    if len(df) > 0:
        for _, row in df.head(5).iterrows():
            abstr = str(row.get("abstr", ""))[:200]
            print(f"  [{row.get('trade_date', '')}] {row.get('inst_csname', '')} | {row.get('title', '')}")
            print(f"    摘要: {abstr}")
            print()
except Exception as e:
    print(f"  ERROR: {e}")

# 4. 全量检查可用的 tushare 接口
print("\n" + "=" * 60)
print("4. 补充接口可用性检查")
print("=" * 60)

# stk_holdertrade
try:
    df = pro.stk_holdertrade(ts_code="002428.SZ", start_date="20250101", end_date="20260430")
    print(f"  stk_holdertrade: {len(df)} rows")
except Exception as e:
    print(f"  stk_holdertrade: {e}")

# top10_holders
try:
    df = pro.top10_holders(ts_code="002428.SZ", period="20251231")
    print(f"  top10_holders: {len(df)} rows")
except Exception as e:
    print(f"  top10_holders: {e}")

# fina_mainbz (主营业务)
try:
    df = pro.fina_mainbz(ts_code="002428.SZ", period="20251231", type="P")
    print(f"  fina_mainbz (产品): {len(df)} rows")
    if len(df) > 0:
        for _, row in df.head(5).iterrows():
            print(f"    {row.get('bz_item', '')} | 营收: {row.get('bz_sales', '')} | 占比: {row.get('bz_profit', '')}")
except Exception as e:
    print(f"  fina_mainbz: {e}")
