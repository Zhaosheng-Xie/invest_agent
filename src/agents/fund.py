"""Fundamental Agent — 基本面分析节点。"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from agents.state import MarketState
from sandboxes.data import tushare_client
from llm_clients.tier_router import get_tier_config
from tools.agent_tools import TOOL_SEARCH_REPORTS, TOOL_CLASSIFY_EVENTS, search_reports, classify_events
from tools.tool_executor import run_agent_with_tools


_PROMPT_PATH = Path(__file__).parent / "prompts" / "fundamental.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


_NON_PRODUCT_KEYWORDS = frozenset([
    "直销", "经销", "分销", "代销", "国内", "国外", "境内", "境外",
    "华东", "华南", "华北", "华中", "西南", "西北", "东北",
    "亚洲", "欧洲", "美洲", "非洲", "大洋洲",
    "内销", "外销", "出口", "进口", "其他地区", "其他渠道",
])


def _is_product_biz(bz_item: str) -> bool:
    """判断 bz_item 是否为产品分类（排除渠道/地区分类）。"""
    return not any(kw in bz_item for kw in _NON_PRODUCT_KEYWORDS)


def _calc_mutation_rate(mainbz_data: list[dict]) -> dict:
    """计算业务结构突变率。按 period 分组，对比最新期 vs 最早期的业务板块占比变化。"""
    from collections import defaultdict

    by_period: dict[str, list[dict]] = defaultdict(list)
    for item in mainbz_data:
        p = item.get("period", "")
        bz_item = item.get("bz_item", "")
        if p and _is_product_biz(bz_item):
            by_period[p].append(item)

    if len(by_period) < 2:
        return {"mutation_score": 0, "years_covered": len(by_period),
                "new_businesses": [], "growing_businesses": [],
                "declining_businesses": [], "summary": "数据不足，无法计算突变率"}

    periods_sorted = sorted(by_period.keys())
    earliest, latest = periods_sorted[0], periods_sorted[-1]

    def _pct_map(items: list[dict]) -> dict[str, float]:
        total = sum(float(it.get("bz_sales") or 0) for it in items)
        if total <= 0:
            return {}
        return {it.get("bz_item", "未知"): float(it.get("bz_sales") or 0) / total * 100
                for it in items if it.get("bz_item")}

    def _fuzzy_key(name: str) -> str:
        return name[:4] if len(name) >= 4 else name

    early_pct = _pct_map(by_period[earliest])
    late_pct = _pct_map(by_period[latest])

    early_fuzzy: dict[str, tuple[str, float]] = {_fuzzy_key(k): (k, v) for k, v in early_pct.items()}
    late_fuzzy: dict[str, tuple[str, float]] = {_fuzzy_key(k): (k, v) for k, v in late_pct.items()}

    new_biz, growing, declining = [], [], []

    for fk, (name, pct) in late_fuzzy.items():
        if fk not in early_fuzzy:
            if pct > 10:
                new_biz.append({"name": name, "latest_pct": round(pct, 1)})
        else:
            early_name, early_val = early_fuzzy[fk]
            change = pct - early_val
            if change > 20:
                growing.append({"name": name, "earliest_pct": round(early_val, 1),
                                "latest_pct": round(pct, 1), "change": round(change, 1)})
            elif change < -20:
                declining.append({"name": early_name, "earliest_pct": round(early_val, 1),
                                  "latest_pct": round(pct, 1), "change": round(change, 1)})

    for fk, (name, pct) in early_fuzzy.items():
        if fk not in late_fuzzy and pct > 1:
            declining.append({"name": name, "earliest_pct": round(pct, 1),
                              "latest_pct": 0.0, "change": round(-pct, 1)})

    max_change = 0.0
    all_late_keys = set(late_fuzzy.keys())
    all_early_keys = set(early_fuzzy.keys())
    for fk in all_late_keys | all_early_keys:
        e = early_fuzzy.get(fk, (None, 0.0))[1]
        l = late_fuzzy.get(fk, (None, 0.0))[1]
        max_change = max(max_change, abs(l - e))

    big_change_count = sum(1 for fk in all_late_keys | all_early_keys
                           if abs(late_fuzzy.get(fk, (None, 0.0))[1]
                                  - early_fuzzy.get(fk, (None, 0.0))[1]) > 10)

    score = len(new_biz) * 20 + big_change_count * 15 + max_change * 1
    score = min(int(score), 100)

    parts = []
    if new_biz:
        names = "、".join(b["name"] for b in new_biz)
        parts.append(f"新增业务 {names}")
    if growing:
        names = "、".join(f'{b["name"]}(+{b["change"]}pct)' for b in growing)
        parts.append(f"快速增长 {names}")
    if declining:
        names = "、".join(f'{b["name"]}({b["change"]}pct)' for b in declining)
        parts.append(f"萎缩业务 {names}")
    summary = f"近{len(periods_sorted)}年业务结构{'发生重大变化：' + '；'.join(parts) if parts else '基本稳定'}"

    return {
        "mutation_score": score,
        "years_covered": len(periods_sorted),
        "new_businesses": new_biz,
        "growing_businesses": growing,
        "declining_businesses": declining,
        "summary": summary,
    }


def _fetch_data(ts_code: str, trade_date: str) -> dict:
    """拉取基本面分析需要的全部数据。"""
    data = {}

    year = trade_date[:4]
    period = f"{int(year)-1}1231"

    for name, func in [
        ("income", tushare_client.get_income),
        ("balancesheet", tushare_client.get_balancesheet),
        ("cashflow", tushare_client.get_cashflow),
        ("fina_indicator", tushare_client.get_fina_indicator),
    ]:
        result = func(ts_code=ts_code, period=period)
        if result["status"] == "ok":
            data[name] = result["data"]

    forecast = tushare_client.get_forecast(ts_code=ts_code)
    if forecast["status"] == "ok":
        data["forecast"] = forecast["data"][:5]

    def _subtract_days(date_str: str, days: int) -> str:
        dt = datetime.strptime(date_str, "%Y%m%d")
        return (dt - timedelta(days=days)).strftime("%Y%m%d")

    start = _subtract_days(trade_date, 100)
    daily_basic = tushare_client.get_daily_basic(
        ts_code=ts_code, start_date=start, end_date=trade_date,
    )
    if daily_basic["status"] == "ok":
        data["daily_basic"] = daily_basic["data"][:5]

    try:
        all_mainbz = []
        base_year = int(trade_date[:4])
        for y in range(base_year - 1, base_year - 6, -1):
            p = f"{y}1231"
            result = tushare_client.get_fina_mainbz(ts_code=ts_code, period=p, type="P")
            if result["status"] == "ok" and result["data"]:
                for item in result["data"]:
                    item["period"] = p
                all_mainbz.extend(result["data"])
            time.sleep(0.5)
        if all_mainbz:
            data["fina_mainbz"] = all_mainbz
            data["biz_mutation_rate"] = _calc_mutation_rate(all_mainbz)
    except Exception:
        pass

    try:
        holdernumber = tushare_client.get_stk_holdernumber(ts_code=ts_code, end_date=trade_date)
        if holdernumber["status"] == "ok":
            data["stk_holdernumber"] = holdernumber["data"][:8]
    except Exception:
        pass

    try:
        research = tushare_client.get_research_report(trade_date)
        if research["status"] == "ok":
            relevant = [r for r in research["data"] if ts_code[:6] in str(r.get("title", "")) or ts_code[:6] in str(r.get("abstr", ""))]
            if relevant:
                data["research_reports"] = relevant[:5]
    except Exception:
        pass

    try:
        stk_surv = tushare_client.get_stk_surv(ts_code=ts_code)
        if stk_surv["status"] == "ok":
            data["stk_surv"] = stk_surv["data"][:10]
    except Exception:
        pass

    try:
        moneyflow = tushare_client.get_moneyflow(ts_code=ts_code, trade_date=trade_date)
        if moneyflow["status"] == "ok":
            data["moneyflow"] = moneyflow["data"][:5]
    except Exception:
        pass

    return data


def fund_node(state: MarketState) -> dict:
    """LangGraph 节点函数：基本面分析。"""
    ts_code = state["ts_code"]
    trade_date = state["trade_date"]
    stock_name = state.get("stock_name", ts_code)

    data = _fetch_data(ts_code, trade_date)

    system_prompt = _load_prompt()
    user_message = (
        f"请分析 {stock_name}（{ts_code}）截至 {trade_date} 的基本面。\n\n"
        f"以下是数据：\n{json.dumps(data, ensure_ascii=False, default=str)}"
    )

    tier = get_tier_config("fund")
    tools = [TOOL_SEARCH_REPORTS, TOOL_CLASSIFY_EVENTS]
    tool_funcs = {"search_reports": search_reports, "classify_events": classify_events}

    response = run_agent_with_tools(
        system_prompt=system_prompt,
        user_message=user_message,
        tools=tools,
        tool_functions=tool_funcs,
        tier_config=tier,
        max_rounds=3,
    )

    content = response["content"]
    try:
        start_idx = content.index("{")
        end_idx = content.rindex("}") + 1
        result = json.loads(content[start_idx:end_idx])
    except (ValueError, json.JSONDecodeError):
        result = {
            "score": 50,
            "highlights": [],
            "risks": ["LLM 输出解析失败"],
            "data_sources": list(data.keys()),
            "summary": content[:500],
        }

    return {"fundamental_score": result}
