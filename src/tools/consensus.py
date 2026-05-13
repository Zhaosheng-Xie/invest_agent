"""卖方一致预期 — 统计近 N 天券商研报覆盖、评级分布、核心观点。"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from sandboxes.data.duckdb_store import query_safe

_DB = "data/duckdb/market.duckdb"

_RATING_PATTERNS: list[tuple[str, str]] = [
    ("强烈推荐", "买入"),
    ("买入", "买入"),
    ("谨慎推荐", "增持"),
    ("推荐", "买入"),
    ("增持", "增持"),
    ("中性", "中性"),
    ("持有", "中性"),
    ("减持", "减持"),
    ("卖出", "卖出"),
    ("回避", "卖出"),
]


def _extract_rating(abstr: str) -> str:
    """从研报摘要中提取评级关键词，返回标准化评级。"""
    if not abstr:
        return "未识别"
    for keyword, rating in _RATING_PATTERNS:
        if keyword in abstr:
            return rating
    return "未识别"


def build_consensus(ts_code: str, days: int = 30, db_path: str | None = None) -> dict:
    """构建卖方一致预期。

    查询 DuckDB research_report 表近 N 天内覆盖该股的研报，统计覆盖券商数、
    评级分布和核心观点摘要。
    """
    db = db_path or _DB
    start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    empty_result = {
        "ts_code": ts_code,
        "coverage_count": 0,
        "broker_count": 0,
        "brokers": [],
        "rating_distribution": {},
        "recent_reports": [],
        "summary": f"近{days}天无券商覆盖",
    }

    try:
        like_pat = f"%{ts_code[:6]}%"
        rows = query_safe(
            "SELECT title, inst_csname, trade_date, abstr, ts_code, name "
            "FROM research_report "
            "WHERE (ts_code LIKE $1 OR name LIKE $1 OR title LIKE $1) "
            "AND trade_date >= $2 "
            "ORDER BY trade_date DESC",
            [like_pat, start],
            db_path=db,
        )
    except Exception:
        return empty_result

    if not rows:
        return empty_result

    brokers: set[str] = set()
    rating_dist: dict[str, int] = {}
    recent_reports = []

    for r in rows:
        inst = r.get("inst_csname", "") or ""
        if inst:
            brokers.add(inst)

        abstr = str(r.get("abstr", "") or "")
        rating = _extract_rating(abstr)
        rating_dist[rating] = rating_dist.get(rating, 0) + 1

        recent_reports.append({
            "title": r.get("title", ""),
            "inst_csname": inst,
            "trade_date": r.get("trade_date", ""),
            "abstr": abstr[:200],
        })

    positive = rating_dist.get("买入", 0) + rating_dist.get("增持", 0)
    neutral = rating_dist.get("中性", 0)
    negative = rating_dist.get("减持", 0) + rating_dist.get("卖出", 0)
    unknown = rating_dist.get("未识别", 0)

    parts = []
    if positive:
        parts.append(f"{positive}买入/增持")
    if neutral:
        parts.append(f"{neutral}中性")
    if negative:
        parts.append(f"{negative}减持/卖出")
    if unknown:
        parts.append(f"{unknown}未识别")
    rating_text = "、".join(parts) if parts else "无评级"

    tone = "偏正面" if positive > neutral + negative else (
        "偏负面" if negative > positive else "中性"
    )

    summary = (
        f"近{days}天{len(brokers)}家券商覆盖，"
        f"评级{tone}（{rating_text}）"
    )

    return {
        "ts_code": ts_code,
        "coverage_count": len(rows),
        "broker_count": len(brokers),
        "brokers": sorted(brokers),
        "rating_distribution": rating_dist,
        "recent_reports": recent_reports[:10],
        "summary": summary,
    }
