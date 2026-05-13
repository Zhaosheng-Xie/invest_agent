"""个股级新闻检索 — 从 DuckDB news 表中按关键词搜索与个股相关的行业快讯。"""
from __future__ import annotations

from datetime import datetime, timedelta

from sandboxes.data.duckdb_store import query_safe

_DB = "data/duckdb/market.duckdb"

_STOP_WORDS = frozenset({
    "其他", "合计", "小计", "其他业务", "其他收入",
    "公司", "有限公司", "股份有限公司",
})


def extract_mainbz_keywords(mainbz_data: list[dict]) -> list[str]:
    """从 fina_mainbz 数据中提取关键词用于新闻搜索。

    逻辑：取所有 bz_item，去重，去掉太泛的词，拆分长名称。
    """
    raw_items: set[str] = set()
    for row in mainbz_data:
        item = str(row.get("bz_item", "")).strip()
        if not item or item in _STOP_WORDS:
            continue
        raw_items.add(item)

    keywords: list[str] = []
    seen: set[str] = set()
    for item in sorted(raw_items):
        if item in seen:
            continue
        seen.add(item)
        keywords.append(item)
        if len(item) >= 6:
            mid = len(item) // 2
            for start in range(0, len(item) - 3, 2):
                sub = item[start:start + 4]
                if sub not in _STOP_WORDS and sub not in seen and len(sub) >= 3:
                    seen.add(sub)
                    keywords.append(sub)

    return keywords


def _extract_stock_name_keywords(stock_name: str) -> list[str]:
    """从股票名称中提取搜索关键词。

    例: "云南锗业" → ["锗"], "中国平安" → ["平安"]
    """
    prefixes = ("中国", "中信", "上海", "北京", "深圳", "广东", "江苏", "浙江",
                "山东", "四川", "云南", "湖南", "湖北", "河南", "河北", "福建",
                "安徽", "新疆", "ST", "*ST")
    suffixes = ("股份", "集团", "控股", "科技", "电子", "实业", "工业",
                "材料", "能源", "医药", "生物", "通信", "信息")

    name = stock_name.strip()
    for p in prefixes:
        if name.startswith(p):
            name = name[len(p):]
            break

    for s in suffixes:
        if name.endswith(s) and len(name) > len(s):
            name = name[:-len(s)]
            break

    keywords = []
    if len(name) >= 2:
        keywords.append(name)
    if len(stock_name) >= 2 and stock_name not in keywords:
        keywords.append(stock_name)
    return keywords


def search_news_for_stock(
    ts_code: str,
    stock_name: str,
    mainbz_keywords: list[str] | None = None,
    days: int = 7,
    db_path: str | None = None,
) -> dict:
    """为个股检索相关行业新闻。

    关键词来源：
    1. stock_name 拆分
    2. mainbz_keywords（从 fina_mainbz 的 bz_item 提取）

    返回:
        {
            "ts_code": "002428.SZ",
            "keywords_used": [...],
            "news_count": 12,
            "news": [{"title": "...", "time": "...", "source": "cls", "relevance": "high"}],
            "summary": "近7天有12条相关快讯，主要涉及..."
        }
    """
    db = db_path or _DB

    keywords = _extract_stock_name_keywords(stock_name)
    if mainbz_keywords:
        for kw in mainbz_keywords:
            if kw not in keywords and kw not in _STOP_WORDS:
                keywords.append(kw)

    if not keywords:
        return {
            "ts_code": ts_code,
            "keywords_used": [],
            "news_count": 0,
            "news": [],
            "summary": "无有效关键词，跳过新闻检索",
        }

    capped_days = min(days, 3650)
    start_date = (datetime.now() - timedelta(days=capped_days)).strftime("%Y-%m-%d %H:%M")

    all_news: list[dict] = []
    seen_titles: set[str] = set()

    for kw in keywords:
        try:
            rows = query_safe(
                "SELECT title, time, source FROM news "
                "WHERE title LIKE $1 "
                "AND time >= $2 "
                "ORDER BY time DESC LIMIT 30",
                [f"%{kw}%", start_date],
                db_path=db,
            )
        except Exception:
            continue

        for r in rows:
            title = str(r.get("title", ""))
            if title in seen_titles:
                continue
            seen_titles.add(title)
            relevance = "high" if stock_name in title or ts_code.split(".")[0] in title else "medium"
            all_news.append({
                "title": title,
                "time": str(r.get("time", "")),
                "source": str(r.get("source", "")),
                "relevance": relevance,
                "matched_keyword": kw,
            })

    all_news.sort(key=lambda x: x.get("time", ""), reverse=True)
    all_news = all_news[:30]

    kw_counts: dict[str, int] = {}
    for n in all_news:
        mk = n.get("matched_keyword", "")
        kw_counts[mk] = kw_counts.get(mk, 0) + 1
    top_kws = sorted(kw_counts, key=lambda k: kw_counts[k], reverse=True)[:3]
    topics = "、".join(top_kws) if top_kws else "无"

    summary = f"近{days}天有{len(all_news)}条相关快讯，主要涉及{topics}" if all_news else f"近{days}天无相关快讯"

    return {
        "ts_code": ts_code,
        "keywords_used": keywords,
        "news_count": len(all_news),
        "news": all_news,
        "summary": summary,
    }
