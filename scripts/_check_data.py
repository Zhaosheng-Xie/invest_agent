"""盘点 DuckDB 数据源现状，为 P2 深度研究循环评估数据可用性。"""
import sys
sys.path.insert(0, "src")
from sandboxes.data.duckdb_store import query_safe

db = "data/duckdb/market.duckdb"

print("=" * 60)
print("1. 所有表和行数")
print("=" * 60)
tables = query_safe(
    "SELECT table_name FROM information_schema.tables WHERE table_schema='main'",
    db_path=db,
)
for t in tables:
    name = t["table_name"]
    try:
        cnt = query_safe(f'SELECT COUNT(*) as cnt FROM "{name}"', db_path=db)
        print(f"  {name}: {cnt[0]['cnt']} rows")
    except Exception as e:
        print(f"  {name}: ERROR {e}")

print("\n" + "=" * 60)
print("2. 002428 机构调研记录 (stk_surv)")
print("=" * 60)
try:
    rows = query_safe(
        'SELECT * FROM stk_surv WHERE ts_code LIKE \'%002428%\' ORDER BY surv_date DESC LIMIT 10',
        db_path=db,
    )
    if rows:
        for r in rows:
            print(f"  [{r.get('surv_date','')}] {r.get('fund_visitors','')} | {r.get('rece_place','')} | {r.get('rece_mode','')}")
    else:
        print("  无数据")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print("3. 002428 个股研报")
print("=" * 60)
try:
    rows = query_safe(
        "SELECT title, inst_csname, trade_date, report_type FROM research_report WHERE ts_code LIKE '%002428%' ORDER BY trade_date DESC LIMIT 10",
        db_path=db,
    )
    if rows:
        for r in rows:
            print(f"  [{r.get('trade_date','')}] {r.get('inst_csname','')} | {r.get('report_type','')} | {r.get('title','')}")
    else:
        print("  无数据")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print("4. 002428 公告")
print("=" * 60)
try:
    rows = query_safe(
        "SELECT ann_date, title, category, pdf_url FROM announcements WHERE ts_code LIKE '%002428%' ORDER BY ann_date DESC LIMIT 10",
        db_path=db,
    )
    if rows:
        for r in rows:
            has_pdf = "有PDF" if r.get("pdf_url") else "无PDF"
            print(f"  [{r.get('ann_date','')}] {r.get('title','')} | {r.get('category','')} | {has_pdf}")
    else:
        print("  无数据")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print("5. Tushare 可用接口盘点")
print("=" * 60)
from sandboxes.data import tushare_client
# 检查 stk_surv 接口
try:
    surv = tushare_client.call_api("stk_surv", ts_code="002428.SZ", start_date="20260101", end_date="20260430",
                                    fields="ts_code,surv_date,fund_visitors,rece_place,rece_mode,rece_org,org_type,comp_rece,content")
    if surv["status"] == "ok":
        print(f"  stk_surv: {len(surv['data'])} records")
        for r in surv["data"][:3]:
            content_preview = str(r.get("content", ""))[:100]
            print(f"    [{r.get('surv_date','')}] visitors={r.get('fund_visitors','')} | {content_preview}")
    else:
        print(f"  stk_surv: {surv}")
except Exception as e:
    print(f"  stk_surv: ERROR {e}")

# 检查 report_rc (研报评级)
try:
    rc = tushare_client.call_api("report_rc", ts_code="002428.SZ", start_date="20260101", end_date="20260430",
                                  fields="ts_code,report_date,report_title,analyst,surv_org,rating,pre_rating")
    if rc["status"] == "ok":
        print(f"\n  report_rc: {len(rc['data'])} records")
        for r in rc["data"][:5]:
            print(f"    [{r.get('report_date','')}] {r.get('surv_org','')} | {r.get('rating','')} | {r.get('report_title','')}")
    else:
        print(f"\n  report_rc: {rc}")
except Exception as e:
    print(f"\n  report_rc: ERROR {e}")

# 检查个股新闻 (akshare)
print("\n" + "=" * 60)
print("6. 东财个股新闻 (akshare)")
print("=" * 60)
try:
    from sandboxes.data import akshare_client
    news = akshare_client.get_stock_news_em(symbol="002428")
    if news["status"] == "ok":
        print(f"  stock_news_em: {len(news['data'])} records")
        for r in news["data"][:5]:
            pub = r.get("发布时间", r.get("publish_time", ""))
            title = r.get("新闻标题", r.get("title", ""))
            print(f"    [{pub}] {title}")
    else:
        print(f"  stock_news_em: {news}")
except Exception as e:
    print(f"  stock_news_em: ERROR {e}")

# 检查 LanceDB 知识库
print("\n" + "=" * 60)
print("7. LanceDB 知识库")
print("=" * 60)
try:
    from sandboxes.data.knowledge_store import semantic_search
    results = semantic_search("InP衬底 磷化铟 产能 扩产", ts_code="002428", top_k=3)
    print(f"  知识库检索 'InP衬底 产能': {len(results)} results")
    for r in results:
        print(f"    [{r['source_type']}|{r['ann_date']}] {r['title'][:50]}")
        print(f"      {r['text'][:150]}")
except Exception as e:
    print(f"  知识库: ERROR {e}")

print("\n" + "=" * 60)
print("8. 巨潮公告实时查询 (002428)")
print("=" * 60)
try:
    from sandboxes.data.cninfo_client import query_announcements
    result = query_announcements(stock="002428", start_date="20260101", end_date="20260430", page_size=10)
    if result["status"] == "ok":
        print(f"  巨潮查询: {len(result['data'])} records")
        for r in result["data"][:5]:
            print(f"    [{r.get('ann_date','')}] {r.get('title','')} | pdf={bool(r.get('pdf_url'))}")
    else:
        print(f"  巨潮查询: {result}")
except Exception as e:
    print(f"  巨潮查询: ERROR {e}")
