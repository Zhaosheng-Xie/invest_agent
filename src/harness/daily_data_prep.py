"""盘后全市场数据预拉取 + 入库 DuckDB。每天 16:30 运行一次。"""
from __future__ import annotations

from datetime import datetime, timedelta

from sandboxes.data import tushare_client, akshare_client
from sandboxes.data.duckdb_store import upsert

_DB = "data/duckdb/market.duckdb"


def _subtract_days(date_str: str, days: int) -> str:
    dt = datetime.strptime(date_str, "%Y%m%d")
    return (dt - timedelta(days=days)).strftime("%Y%m%d")


def run_daily_prep(trade_date: str, db_path: str | None = None) -> dict:
    """盘后预拉取全市场共享数据。返回各表写入行数统计。"""
    db = db_path or _DB
    stats = {}

    # 1. 研报：近 7 天
    all_reports = []
    for offset in range(7):
        date = _subtract_days(trade_date, offset)
        try:
            result = tushare_client.get_research_report(date)
            if result["status"] == "ok" and result["data"]:
                all_reports.extend(result["data"])
        except Exception:
            pass
    if all_reports:
        stats["research_report"] = upsert("research_report", all_reports, ["title", "trade_date"], db_path=db)

    # 2. 政策法规：近 30 天（含正文）
    try:
        import re as _re
        start = _subtract_days(trade_date, 30)
        result = tushare_client.get_npr(start_date=start, end_date=trade_date)
        if result["status"] == "ok" and result["data"]:
            for item in result["data"]:
                html = item.pop("content_html", "") or ""
                content = _re.sub(r'<[^>]+>', '', html).strip()
                item["content"] = content[:10000]
            stats["policy"] = upsert("policy", result["data"], ["title", "pubtime"], db_path=db)
    except Exception as e:
        stats["policy_error"] = str(e)

    # 3. 游资名录（字段: name/desc/orgs）
    try:
        result = tushare_client.get_hm_list()
        if result["status"] == "ok" and result["data"]:
            stats["hm_list"] = upsert("hm_list", result["data"], ["name"], db_path=db)
    except Exception as e:
        stats["hm_list_error"] = str(e)

    # 4. 龙虎榜 + 机构席位（回溯最近 5 个交易日，跳过假期空数据）
    import time
    for name, make_func, keys in [
        ("top_list", lambda d: tushare_client.get_top_list(trade_date=d), ["ts_code", "trade_date"]),
        ("top_inst", lambda d: tushare_client.get_top_inst(trade_date=d), ["ts_code", "trade_date"]),
    ]:
        for offset in range(5):
            dt = _subtract_days(trade_date, offset)
            try:
                result = make_func(dt)
                if result["status"] == "ok" and result["data"]:
                    stats[name] = upsert(name, result["data"], keys, db_path=db)
                    break
                time.sleep(1)
            except Exception:
                time.sleep(2)

    # 5. 板块资金流
    for name, func in [
        ("moneyflow_ind_ths", lambda: tushare_client.get_moneyflow_ind_ths(trade_date=trade_date)),
        ("moneyflow_cnt_ths", lambda: tushare_client.get_moneyflow_cnt_ths(trade_date=trade_date)),
    ]:
        try:
            result = func()
            if result["status"] == "ok" and result["data"]:
                stats[name] = upsert(name, result["data"], ["ts_code", "trade_date"], db_path=db)
        except Exception:
            pass

    # 6. 快讯（字段可能是中文：时间/内容 或 英文）
    for source, func in [("cls", lambda: akshare_client.get_cls_news(count=200)), ("jin10", lambda: akshare_client.get_jin10_news(count=200))]:
        try:
            result = func()
            if result["status"] == "ok" and result["data"]:
                normalized = []
                for r in result["data"]:
                    item = {
                        "title": r.get("标题", r.get("title", r.get("内容", str(r)[:200]))),
                        "time": str(r.get("发布时间", r.get("time", r.get("时间", "")))),
                        "source": source,
                    }
                    normalized.append(item)
                stats[f"news_{source}"] = upsert("news", normalized, ["title", "source"], db_path=db)
        except Exception as e:
            stats[f"news_{source}_error"] = str(e)

    # 7. 涨跌停
    try:
        result = tushare_client.get_limit_list_d(trade_date=trade_date)
        if result["status"] == "ok" and result["data"]:
            stats["limit_list"] = upsert("limit_list", result["data"], ["ts_code", "trade_date"], db_path=db)
    except Exception:
        pass

    # 8. 板块指数
    try:
        result = tushare_client.get_ths_index()
        if result["status"] == "ok" and result["data"]:
            stats["ths_index"] = upsert("ths_index_cache", result["data"], ["ts_code"], db_path=db)
    except Exception:
        pass

    # 9. 公告：当日全市场（巨潮API）
    anns = []
    try:
        from sandboxes.data.cninfo_client import query_all_announcements
        anns = query_all_announcements(start_date=trade_date, end_date=trade_date)
        if anns:
            stats["announcements"] = upsert("announcements", anns, ["ts_code", "ann_date", "title"], db_path=db)
    except Exception as e:
        stats["announcements_error"] = str(e)

    # 10. 高价值公告正文 -> 知识库
    try:
        from sandboxes.data.cninfo_client import fetch_announcement_text
        from sandboxes.data.knowledge_store import ingest_announcement

        important_categories = ["重大事项", "资产重组", "融资公告", "持股变动"]
        important_keywords = [
            "扩产", "投资", "项目", "收购", "产能", "战略合作",
            "中标", "订单", "增持", "回购", "定增",
        ]

        high_value = [a for a in anns if
                      a.get("category", "") in important_categories or
                      any(kw in a.get("title", "") for kw in important_keywords)]

        ingested = 0
        for ann in high_value[:50]:
            if ann.get("pdf_url"):
                text = fetch_announcement_text(ann["pdf_url"])
                if text and len(text) > 100:
                    ingest_announcement(
                        ts_code=ann.get("ts_code", ""),
                        title=ann.get("title", ""),
                        text=text,
                        ann_date=ann.get("ann_date", ""),
                    )
                    ingested += 1
                time.sleep(1)
        stats["knowledge_ingested"] = ingested
    except Exception as e:
        stats["knowledge_error"] = str(e)

    return stats
