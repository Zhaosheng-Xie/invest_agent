"""Agent Tool 定义 — OpenAI 格式 schema + 实现函数。"""
from __future__ import annotations

from datetime import datetime, timedelta

from sandboxes.data.duckdb_store import query_safe
from sandboxes.data import tushare_client, akshare_client
from sandboxes.data import industry_map
from sandboxes.data import cninfo_client
from tools.news_search import search_news_for_stock

_DB = "data/duckdb/market.duckdb"

# ---- Tool 实现函数 ----


def search_reports(keyword: str, days: int = 7, db_path: str | None = None) -> str:
    """按关键词搜索近期研报。返回精简文本。"""
    db = db_path or _DB
    try:
        like_pat = f"%{keyword}%"
        rows = query_safe(
            "SELECT title, inst_csname, report_type, trade_date, abstr, name, ts_code FROM research_report "
            "WHERE title LIKE $1 OR abstr LIKE $1 "
            "OR name LIKE $1 OR ts_code LIKE $1 "
            "ORDER BY trade_date DESC LIMIT 10",
            [like_pat],
            db_path=db,
        )
        if not rows:
            return f"未找到包含'{keyword}'的研报"
        lines = []
        for r in rows:
            abstr = str(r.get("abstr", ""))[:200]
            lines.append(f"[{r.get('trade_date','')}] {r.get('inst_csname','')} | {r.get('report_type','')} | {r.get('title','')} | {abstr}")
        return "\n".join(lines)
    except Exception as e:
        return f"研报查询失败: {e}"


def search_reports_by_industry(industry: str, ts_code: str = "", days: int = 7, db_path: str | None = None) -> str:
    """按行业+个股双维度搜索研报。先按 ind_name 搜行业研报，再按 ts_code 搜个股研报，合并去重。"""
    db = db_path or _DB
    try:
        start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        ind_rows = query_safe(
            "SELECT title, inst_csname, report_type, trade_date, abstr, name, ts_code, ind_name "
            "FROM research_report "
            "WHERE ind_name LIKE $1 AND trade_date >= $2 "
            "ORDER BY trade_date DESC LIMIT 20",
            [f"%{industry}%", start],
            db_path=db,
        )

        stock_rows = []
        if ts_code:
            like_code = f"%{ts_code[:6]}%"
            stock_rows = query_safe(
                "SELECT title, inst_csname, report_type, trade_date, abstr, name, ts_code, ind_name "
                "FROM research_report "
                "WHERE (ts_code LIKE $1 OR name LIKE $1 OR title LIKE $1) "
                "AND trade_date >= $2 "
                "ORDER BY trade_date DESC LIMIT 20",
                [like_code, start],
                db_path=db,
            )

        seen_titles: set[str] = set()
        merged = []
        for r in ind_rows + stock_rows:
            t = r.get("title", "")
            if t not in seen_titles:
                seen_titles.add(t)
                merged.append(r)

        if not merged:
            hint = f"'{industry}'行业"
            if ts_code:
                hint += f"或个股'{ts_code}'"
            return f"近{days}天未找到{hint}的研报"

        lines = []
        for r in merged[:20]:
            abstr = str(r.get("abstr", ""))[:200]
            lines.append(
                f"[{r.get('trade_date', '')}] {r.get('inst_csname', '')} | "
                f"{r.get('report_type', '')} | {r.get('title', '')} | {abstr}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"行业研报查询失败: {e}"


def search_policy(keyword: str, db_path: str | None = None) -> str:
    """按关键词搜索政策法规。"""
    db = db_path or _DB
    try:
        like_pat = f"%{keyword}%"
        rows = query_safe(
            "SELECT title, puborg, pubtime, ptype FROM policy "
            "WHERE title LIKE $1 OR ptype LIKE $1 "
            "ORDER BY pubtime DESC LIMIT 10",
            [like_pat],
            db_path=db,
        )
        if not rows:
            return f"未找到包含'{keyword}'的政策"
        return "\n".join(f"[{r.get('pubtime','')}] {r.get('puborg','')} | {r.get('ptype','')} | {r.get('title','')}" for r in rows)
    except Exception as e:
        return f"政策查询失败: {e}"


def match_hot_money(trade_date: str, db_path: str | None = None) -> str:
    """龙虎榜 x 游资名录预匹配：返回当日游资动向。"""
    db = db_path or _DB
    try:
        rows = query_safe(
            "SELECT t.ts_code, t.exalter, t.buy, t.sell, t.net_buy, h.name AS hm_name "
            "FROM top_inst t, hm_list h "
            "WHERE t.trade_date = $1 "
            "AND h.orgs LIKE '%' || t.exalter || '%' "
            "ORDER BY CAST(t.buy AS DOUBLE) DESC LIMIT 20",
            [trade_date],
            db_path=db,
        )
        if not rows:
            return f"{trade_date} 无知名游资席位命中龙虎榜"
        lines = []
        for r in rows:
            buy = float(r.get("buy", 0) or 0)
            sell = float(r.get("sell", 0) or 0)
            action = "买入" if buy > sell else "卖出"
            amt = max(buy, sell)
            lines.append(f"游资{r.get('hm_name','')} 通过{r.get('exalter','')} {action} {r.get('ts_code','')} {amt:.0f}元")
        return "\n".join(lines)
    except Exception as e:
        return f"游资匹配查询失败: {e}"


def get_north_individual(ts_code: str, db_path: str | None = None) -> str:
    """查询个股北向持仓（带时效性检查）。"""
    try:
        symbol = ts_code.split(".")[0]
        result = akshare_client.get_north_flow_individual(symbol=symbol)
        if result["status"] != "ok" or not result["data"]:
            return f"{ts_code} 无北向个股持仓数据"
        data = result["data"]
        dates = [str(r.get("date", "")) for r in data if r.get("date")]
        latest = max(dates) if dates else "未知"
        note = ""
        if latest < "2025":
            note = f"[警告] 数据严重过期（最新{latest}），仅供参考。"
        top5 = sorted(data, key=lambda x: str(x.get("date", "")), reverse=True)[:5]
        lines = [note] if note else []
        for r in top5:
            lines.append(f"[{r.get('date','')}] 持股{r.get('shareholding','')}股, 市值{r.get('close_amt','')}万")
        return "\n".join(lines) or "无数据"
    except Exception as e:
        return f"北向个股查询失败: {e}"


def search_news(keyword: str, count: int = 10, db_path: str | None = None) -> str:
    """按关键词搜索快讯。"""
    db = db_path or _DB
    try:
        rows = query_safe(
            "SELECT * FROM news WHERE title LIKE $1 ORDER BY time DESC LIMIT $2",
            [f"%{keyword}%", count],
            db_path=db,
        )
        if not rows:
            return f"未找到包含'{keyword}'的快讯"
        lines = []
        for r in rows:
            title = r.get("标题", r.get("title", str(r)[:100]))
            time_val = r.get("发布时间", r.get("time", ""))
            source = r.get("source", "")
            lines.append(f"[{time_val}] [{source}] {title}")
        return "\n".join(lines)
    except Exception as e:
        if "does not exist" in str(e) or "not found" in str(e).lower():
            return "快讯表尚未创建，需运行 daily_data_prep 或 backfill_data 写入数据"
        return f"快讯查询失败: {e}"


def get_theme_members(theme_name: str) -> str:
    """查询同花顺板块成分股。"""
    try:
        idx = tushare_client.get_ths_index()
        if idx["status"] != "ok":
            return "板块指数查询失败"
        matched = [r for r in idx["data"] if theme_name in str(r.get("name", ""))]
        if not matched:
            return f"未找到包含'{theme_name}'的板块"
        ts_code = matched[0].get("ts_code", "")
        members = tushare_client.get_ths_member(ts_code=ts_code)
        if members["status"] != "ok":
            return f"板块{ts_code}成分股查询失败"
        lines = [f"板块: {matched[0].get('name','')} ({ts_code})", "成分股:"]
        for m in members["data"][:20]:
            lines.append(f"  {m.get('code','')} {m.get('name','')}")
        return "\n".join(lines)
    except Exception as e:
        return f"板块查询失败: {e}"


def classify_events(ts_code: str, days: int = 30) -> str:
    """结构化事件分类。"""
    try:
        from sandboxes.data.events_db import classify_events as _classify
        from datetime import datetime, timedelta
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        events = _classify(ts_code, start, end)
        if not events:
            return f"{ts_code} 近{days}天无结构化事件"
        lines = []
        for e in events[:10]:
            lines.append(f"[{e.get('ann_date','')}] {e.get('event_type','')} 强度{e.get('strength',0):.1f} | {e.get('detail','')[:100]}")
        return "\n".join(lines)
    except Exception as e:
        return f"事件分类失败: {e}"


def search_news_for_stock_tool(
    ts_code: str,
    stock_name: str,
    mainbz_keywords: str = "",
    days: int = 7,
) -> str:
    """为个股检索相关行业新闻（tool calling 入口，返回文本摘要）。"""
    kw_list = [k.strip() for k in mainbz_keywords.split(",") if k.strip()] if mainbz_keywords else None
    result = search_news_for_stock(ts_code, stock_name, mainbz_keywords=kw_list, days=days)
    if not result["news"]:
        return result["summary"]
    lines = [result["summary"], f"关键词: {', '.join(result['keywords_used'][:10])}", ""]
    for n in result["news"][:15]:
        lines.append(f"[{n['time']}] [{n['source']}] {n['title']} (匹配:{n['matched_keyword']})")
    return "\n".join(lines)


def get_industry_chain(ts_code: str) -> str:
    """查询股票所属产业链（上下游映射）。"""
    try:
        result = industry_map.get_stock_industries(ts_code)
        keywords = result.get("matched_chain_keywords", [])
        chain = result.get("industry_chain", {})
        bz = result.get("mainbz_keywords", [])
        concepts = result.get("ths_concepts", [])

        lines = [f"股票: {result.get('stock_name', '')} ({ts_code})"]
        if concepts:
            lines.append(f"概念板块: {', '.join(concepts[:10])}")
        if bz:
            lines.append(f"主营业务: {', '.join(bz[:10])}")
        if keywords:
            lines.append(f"匹配产业链关键词: {', '.join(keywords)}")
        if chain.get("upstream"):
            lines.append(f"上游: {', '.join(chain['upstream'][:10])}")
        if chain.get("midstream"):
            lines.append(f"中游: {', '.join(chain['midstream'][:10])}")
        if chain.get("downstream"):
            lines.append(f"下游: {', '.join(chain['downstream'][:10])}")
        if not keywords:
            lines.append("未匹配到已知产业链关键词，仅展示原始业务数据")
        return "\n".join(lines)
    except Exception as e:
        return f"产业链查询失败: {e}"


def find_stocks_in_chain(keyword: str) -> str:
    """从产业关键词找相关上市公司。"""
    try:
        stocks = industry_map.find_related_stocks(keyword)
        if not stocks:
            return f"未找到'{keyword}'相关的上市公司（可能板块数据未入库）"
        lines = [f"'{keyword}'相关股票（共{len(stocks)}只）:"]
        for s in stocks[:20]:
            lines.append(f"  {s['ts_code']} {s.get('name', '')} [{s.get('chain_position', '')}] 来源:{s.get('source_sector', '')}")
        if len(stocks) > 20:
            lines.append(f"  ... 还有{len(stocks) - 20}只")
        return "\n".join(lines)
    except Exception as e:
        return f"产业链股票查询失败: {e}"


def search_announcements(ts_code: str, days: int = 90, db_path: str | None = None) -> str:
    """查询个股近期公告标题列表（DuckDB announcements 表）。"""
    db = db_path or _DB
    try:
        start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        code6 = ts_code.split(".")[0]
        rows = query_safe(
            "SELECT * FROM announcements WHERE ts_code LIKE $1 AND ann_date >= $2 "
            "ORDER BY ann_date DESC LIMIT 20",
            [f"%{code6}%", start],
            db_path=db,
        )
        if not rows:
            return f"{ts_code} 近{days}天无公告记录"
        lines = []
        for r in rows:
            lines.append(f"[{r.get('ann_date', '')}] {r.get('title', '')} | {r.get('category', r.get('type', ''))}")
        return "\n".join(lines)
    except Exception as e:
        if "does not exist" in str(e) or "not found" in str(e).lower():
            return "公告库暂无数据"
        return f"公告查询失败: {e}"


def fetch_stock_reports(ts_code: str, days: int = 30) -> str:
    """实时获取个股券商研报（通过 tushare API）。"""
    try:
        start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        result = tushare_client.get_research_report_by_stock(
            ts_code=ts_code, start_date=start,
        )
        if result["status"] != "ok" or not result["data"]:
            return f"{ts_code} 近{days}天无个股研报"
        lines = []
        for r in result["data"][:15]:
            abstr = str(r.get("abstr", ""))[:200]
            lines.append(
                f"[{r.get('trade_date', '')}] {r.get('inst_csname', '')} | "
                f"{r.get('title', '')} | {abstr}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"个股研报查询失败: {e}"


def fetch_stock_news(ts_code: str, stock_name: str = "", days: int = 7) -> str:
    """实时获取东方财富个股新闻（akshare）。"""
    try:
        code6 = ts_code.split(".")[0]
        result = akshare_client.get_stock_news_em(symbol=code6)
        if result["status"] != "ok" or not result["data"]:
            return f"{ts_code} 无个股新闻数据"
        lines = []
        for r in result["data"][:20]:
            pub_time = r.get("发布时间", r.get("publish_time", r.get("time", "")))
            title = r.get("新闻标题", r.get("title", str(r)[:100]))
            source = r.get("新闻来源", r.get("source", ""))
            lines.append(f"[{pub_time}] {title} | {source}")
        return "\n".join(lines)
    except Exception as e:
        return f"个股新闻查询失败: {e}"


def search_policy_content(keyword: str, days: int = 90, db_path: str | None = None) -> str:
    """按关键词搜索政策法规并返回正文内容（前500字）。"""
    db = db_path or _DB
    try:
        like_pat = f"%{keyword}%"
        rows = query_safe(
            "SELECT title, puborg, pubtime, ptype, content FROM policy "
            "WHERE title LIKE $1 OR content LIKE $1 "
            "ORDER BY pubtime DESC LIMIT 5",
            [like_pat],
            db_path=db,
        )
        if not rows:
            return f"未找到包含'{keyword}'的政策正文"
        lines = []
        for r in rows:
            content = str(r.get("content", ""))[:500]
            lines.append(
                f"[{r.get('pubtime', '')}] {r.get('puborg', '')} | {r.get('title', '')}\n"
                f"正文摘要: {content}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        if "does not exist" in str(e) or "not found" in str(e).lower():
            return "政策库暂无数据"
        return f"政策正文查询失败: {e}"


def search_knowledge(query: str, ts_code: str = "", source_type: str = "", top_k: int = 5) -> str:
    """语义检索知识库（公告正文/研报摘要/政策内容）。"""
    try:
        from sandboxes.data.knowledge_store import semantic_search
        results = semantic_search(query=query, ts_code=ts_code, source_type=source_type, top_k=top_k)
        if not results:
            return f"知识库中未找到与'{query}'相关的内容"
        lines = []
        for r in results:
            source = r["source_type"]
            date = r["ann_date"]
            title = r["title"][:50]
            text = r["text"][:300]
            lines.append(f"[{source}|{date}] {title}\n{text}\n")
        return "\n---\n".join(lines)
    except Exception as e:
        if "Table" in str(e) and "not found" in str(e):
            return "知识库暂无数据"
        return f"知识库检索失败: {e}"


def fetch_announcement_content(ts_code: str, title_keyword: str = "", db_path: str | None = None) -> str:
    """获取个股公告正文。优先 DuckDB pdf_url → 巨潮 API → LanceDB 语义搜索。"""
    code6 = ts_code.split(".")[0]
    db = db_path or _DB
    candidates = []

    # 来源 1：DuckDB announcements 表（可能有 pdf_url）
    try:
        like_code = f"%{code6}%"
        rows = query_safe(
            "SELECT ann_date, title, category, pdf_url FROM announcements "
            "WHERE ts_code LIKE $1 ORDER BY ann_date DESC LIMIT 20",
            [like_code],
            db_path=db,
        )
        if rows:
            candidates = [{"ann_date": r.get("ann_date", ""), "title": r.get("title", ""),
                           "pdf_url": r.get("pdf_url", "") or ""} for r in rows]
    except Exception:
        pass

    # 来源 2：巨潮 API 实时查询
    if not candidates:
        try:
            result = cninfo_client.query_announcements(stock=code6, page_size=10)
            if result["status"] == "ok" and result["data"]:
                candidates = result["data"]
        except Exception:
            pass

    # 按 title_keyword 过滤
    if title_keyword and candidates:
        filtered = [a for a in candidates if title_keyword in a.get("title", "")]
        if filtered:
            candidates = filtered

    # 尝试从有 pdf_url 的候选中下载正文
    for ann in candidates:
        pdf_url = ann.get("pdf_url", "")
        if not pdf_url:
            continue
        try:
            text = cninfo_client.fetch_announcement_text(pdf_url)
            if text and len(text) > 50:
                header = f"[{ann.get('ann_date', '')}] {ann.get('title', '')}\n"
                return header + text[:3000]
        except Exception:
            continue

    # Fallback：LanceDB 语义搜索
    try:
        from sandboxes.data.knowledge_store import semantic_search
        query_text = f"{ts_code} {title_keyword}" if title_keyword else ts_code
        results = semantic_search(query=query_text, ts_code=ts_code, source_type="announcement", top_k=3)
        if results:
            lines = []
            for r in results:
                lines.append(f"[{r['ann_date']}] {r['title'][:50]}\n{r['text'][:1000]}")
            return "（来源：知识库语义检索）\n\n" + "\n---\n".join(lines)
    except Exception:
        pass

    if candidates:
        titles = [f"[{a.get('ann_date', '')}] {a.get('title', '')}" for a in candidates[:10]]
        return f"公告 PDF 提取失败，以下为匹配的公告列表:\n" + "\n".join(titles)
    return f"{ts_code} 未查到公告"


# ---- Tool Schema（OpenAI 格式，供 Kimi tool calling 用）----

TOOL_SEARCH_REPORTS = {
    "type": "function",
    "function": {
        "name": "search_reports",
        "description": "按股票名称或行业关键词搜索近期券商研报摘要。返回评级、目标价、核心观点。用于交叉验证基本面判断或发现市场共识。",
        "parameters": {"type": "object", "properties": {"keyword": {"type": "string", "description": "股票简称或行业关键词"}}, "required": ["keyword"]},
    },
}

TOOL_SEARCH_REPORTS_INDUSTRY = {
    "type": "function",
    "function": {
        "name": "search_reports_by_industry",
        "description": "按行业+个股双维度搜索近7天研报。行业研报（如'光通信行业深度'）通过 ind_name 匹配，个股研报通过 ts_code/name/title 匹配，合并去重。",
        "parameters": {
            "type": "object",
            "properties": {
                "industry": {"type": "string", "description": "行业关键词，如'光通信'、'半导体'"},
                "ts_code": {"type": "string", "description": "股票代码如002428.SZ，可选", "default": ""},
                "days": {"type": "integer", "description": "近N天，默认7", "default": 7},
            },
            "required": ["industry"],
        },
    },
}

TOOL_SEARCH_POLICY = {
    "type": "function",
    "function": {
        "name": "search_policy",
        "description": "按关键词搜索国家政策法规（来源：国务院、各部委公开文件）。用于判断政策驱动主线。",
        "parameters": {"type": "object", "properties": {"keyword": {"type": "string", "description": "政策关键词如'半导体'、'新能源'"}}, "required": ["keyword"]},
    },
}

TOOL_MATCH_HOT_MONEY = {
    "type": "function",
    "function": {
        "name": "match_hot_money",
        "description": "查询当日龙虎榜与知名游资名录的匹配结果。返回'游资X通过Y营业部买入Z股N万'的预匹配结果。",
        "parameters": {"type": "object", "properties": {"trade_date": {"type": "string", "description": "交易日期YYYYMMDD"}}, "required": ["trade_date"]},
    },
}

TOOL_GET_NORTH = {
    "type": "function",
    "function": {
        "name": "get_north_individual",
        "description": "查询个股北向资金持仓变化（带数据时效性检查）。注意：数据可能滞后。",
        "parameters": {"type": "object", "properties": {"ts_code": {"type": "string", "description": "股票代码如000988.SZ"}}, "required": ["ts_code"]},
    },
}

TOOL_SEARCH_NEWS = {
    "type": "function",
    "function": {
        "name": "search_news",
        "description": "按关键词搜索财联社+金十快讯。用于捕捉实时热点和事件催化。",
        "parameters": {"type": "object", "properties": {"keyword": {"type": "string", "description": "搜索关键词"}}, "required": ["keyword"]},
    },
}

TOOL_GET_THEME = {
    "type": "function",
    "function": {
        "name": "get_theme_members",
        "description": "查询同花顺概念/行业板块的成分股列表。用于从主题推导受益标的。",
        "parameters": {"type": "object", "properties": {"theme_name": {"type": "string", "description": "板块名称如'CPO'、'光模块'"}}, "required": ["theme_name"]},
    },
}

TOOL_CLASSIFY_EVENTS = {
    "type": "function",
    "function": {
        "name": "classify_events",
        "description": "对指定股票做结构化事件分类（业绩预告/解禁/增减持等），返回事件类型和强度评分。",
        "parameters": {"type": "object", "properties": {"ts_code": {"type": "string", "description": "股票代码"}, "days": {"type": "integer", "description": "近N天，默认30", "default": 30}}, "required": ["ts_code"]},
    },
}

TOOL_SEARCH_NEWS_FOR_STOCK = {
    "type": "function",
    "function": {
        "name": "search_news_for_stock_tool",
        "description": "为个股检索相关行业新闻。自动从股票名称和主营业务关键词匹配快讯，返回近N天相关新闻。用于发现行业催化剂、涨价/政策等事件。",
        "parameters": {
            "type": "object",
            "properties": {
                "ts_code": {"type": "string", "description": "股票代码如002428.SZ"},
                "stock_name": {"type": "string", "description": "股票简称如云南锗业"},
                "mainbz_keywords": {"type": "string", "description": "主营业务关键词，逗号分隔，如'锗,化合物半导体,InP'", "default": ""},
                "days": {"type": "integer", "description": "近N天，默认7", "default": 7},
            },
            "required": ["ts_code", "stock_name"],
        },
    },
}

TOOL_GET_INDUSTRY_CHAIN = {
    "type": "function",
    "function": {
        "name": "get_industry_chain",
        "description": "查询股票所属产业链，返回上游/中游/下游节点映射。用于理解公司在产业链中的位置，做'快讯→产业链→受益公司'的链式推理。",
        "parameters": {"type": "object", "properties": {"ts_code": {"type": "string", "description": "股票代码如002428.SZ"}}, "required": ["ts_code"]},
    },
}

TOOL_FIND_STOCKS_IN_CHAIN = {
    "type": "function",
    "function": {
        "name": "find_stocks_in_chain",
        "description": "从产业关键词（如'光模块'、'InP'、'人形机器人'）找同产业链的上市公司列表。用于从产业趋势发现受益标的。",
        "parameters": {"type": "object", "properties": {"keyword": {"type": "string", "description": "产业关键词如'光模块'、'算力'、'固态电池'"}}, "required": ["keyword"]},
    },
}

TOOL_SEARCH_ANNOUNCEMENTS = {
    "type": "function",
    "function": {
        "name": "search_announcements",
        "description": "查询个股近期公告标题列表（来源DuckDB公告库）。返回公告日期、标题和类型。用于了解公司近期重大事项。",
        "parameters": {
            "type": "object",
            "properties": {
                "ts_code": {"type": "string", "description": "股票代码如002428.SZ"},
                "days": {"type": "integer", "description": "查询近N天，默认90", "default": 90},
            },
            "required": ["ts_code"],
        },
    },
}

TOOL_FETCH_STOCK_REPORTS = {
    "type": "function",
    "function": {
        "name": "fetch_stock_reports",
        "description": "实时获取个股券商研报（通过tushare API），返回日期、券商、标题、摘要。与search_reports区别：这个按ts_code精确查个股研报，不依赖DuckDB预入库。",
        "parameters": {
            "type": "object",
            "properties": {
                "ts_code": {"type": "string", "description": "股票代码如002428.SZ"},
                "days": {"type": "integer", "description": "查询近N天，默认30", "default": 30},
            },
            "required": ["ts_code"],
        },
    },
}

TOOL_FETCH_STOCK_NEWS = {
    "type": "function",
    "function": {
        "name": "fetch_stock_news",
        "description": "实时获取东方财富个股新闻（akshare接口）。返回发布时间、标题、来源。与search_news区别：这个直接按股票代码拉取东财个股新闻页，数据更精准。",
        "parameters": {
            "type": "object",
            "properties": {
                "ts_code": {"type": "string", "description": "股票代码如002428.SZ"},
                "stock_name": {"type": "string", "description": "股票简称（可选）", "default": ""},
                "days": {"type": "integer", "description": "近N天，默认7", "default": 7},
            },
            "required": ["ts_code"],
        },
    },
}

TOOL_SEARCH_POLICY_CONTENT = {
    "type": "function",
    "function": {
        "name": "search_policy_content",
        "description": "按关键词搜索政策法规并返回正文内容（前500字）。与search_policy区别：这个返回政策正文摘要，而非仅标题。",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "政策关键词如'半导体'、'新能源'"},
                "days": {"type": "integer", "description": "查询近N天，默认90", "default": 90},
            },
            "required": ["keyword"],
        },
    },
}

TOOL_FETCH_ANNOUNCEMENT_CONTENT = {
    "type": "function",
    "function": {
        "name": "fetch_announcement_content",
        "description": "通过巨潮资讯查询个股公告并提取PDF正文（前3000字）。用于获取公告全文内容，如业绩预告详情、重大资产重组说明等。",
        "parameters": {
            "type": "object",
            "properties": {
                "ts_code": {"type": "string", "description": "股票代码如002428.SZ"},
                "title_keyword": {"type": "string", "description": "公告标题关键词过滤，如'业绩预告'", "default": ""},
            },
            "required": ["ts_code"],
        },
    },
}

TOOL_SEARCH_KNOWLEDGE = {
    "type": "function",
    "function": {
        "name": "search_knowledge",
        "description": "语义检索知识库，搜索公告正文、研报摘要、政策法规内容。输入自然语言查询，返回最相关的文本片段。适用于查找'某公司是否有扩产计划'、'某产业链有哪些政策支持'等深度问题。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "自然语言查询，如'InP衬底产能扩张'"},
                "ts_code": {"type": "string", "description": "可选，限定股票代码", "default": ""},
                "source_type": {"type": "string", "description": "可选，限定来源类型：announcement/report/policy", "default": ""},
            },
            "required": ["query"],
        },
    },
}

def get_report_rating(ts_code: str, days: int = 180) -> str:
    """获取个股券商研报评级历史（tushare report_rc 接口）。"""
    try:
        start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        pro = tushare_client._get_pro()
        df = pro.report_rc(ts_code=ts_code, start_date=start)
        if df is None or df.empty:
            return f"{ts_code} 近{days}天无研报评级"
        lines = []
        for _, row in df.head(10).iterrows():
            lines.append(
                f"[{row.get('report_date', '')}] {row.get('org_name', '')} | "
                f"评级: {row.get('rating', '')} | {row.get('report_title', '')}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"研报评级查询失败: {e}"


def get_mainbiz_detail(ts_code: str, period: str = "") -> str:
    """获取个股主营业务构成（按产品分拆）。"""
    try:
        if not period:
            year = datetime.now().year - 1
            period = f"{year}1231"
        result = tushare_client.get_fina_mainbz(ts_code=ts_code, period=period, type="P")
        if result["status"] != "ok" or not result["data"]:
            return f"{ts_code} 无主营业务构成数据"
        lines = [f"{ts_code} 主营业务构成 (期间: {period}):"]
        for r in result["data"]:
            name = r.get("bz_item", "")
            sales = float(r.get("bz_sales", 0) or 0)
            profit = float(r.get("bz_profit", 0) or 0)
            margin = (profit / sales * 100) if sales > 0 else 0
            lines.append(f"  {name}: 营收{sales/1e8:.2f}亿, 毛利{profit/1e8:.2f}亿, 毛利率{margin:.1f}%")
        return "\n".join(lines)
    except Exception as e:
        return f"主营业务查询失败: {e}"


# ---- Tool Schema: get_report_rating ----

TOOL_GET_REPORT_RATING = {
    "type": "function",
    "function": {
        "name": "get_report_rating",
        "description": "获取个股券商研报评级历史（tushare report_rc接口）。返回评级日期、券商名称、评级变动（如买入/增持/中性）和研报标题。用于了解卖方分析师对个股的最新观点和评级趋势。",
        "parameters": {
            "type": "object",
            "properties": {
                "ts_code": {"type": "string", "description": "股票代码如002428.SZ"},
                "days": {"type": "integer", "description": "查询近N天，默认180", "default": 180},
            },
            "required": ["ts_code"],
        },
    },
}

TOOL_GET_MAINBIZ_DETAIL = {
    "type": "function",
    "function": {
        "name": "get_mainbiz_detail",
        "description": "获取个股主营业务构成（按产品分拆），返回每个产品线的营收、毛利和毛利率。用于分析公司业务结构和盈利能力变化。",
        "parameters": {
            "type": "object",
            "properties": {
                "ts_code": {"type": "string", "description": "股票代码如002428.SZ"},
                "period": {"type": "string", "description": "报告期如20231231，空则默认上一年年报", "default": ""},
            },
            "required": ["ts_code"],
        },
    },
}

ALL_TOOLS = [
    TOOL_SEARCH_REPORTS, TOOL_SEARCH_REPORTS_INDUSTRY, TOOL_SEARCH_POLICY,
    TOOL_MATCH_HOT_MONEY, TOOL_GET_NORTH, TOOL_SEARCH_NEWS, TOOL_GET_THEME,
    TOOL_CLASSIFY_EVENTS, TOOL_SEARCH_NEWS_FOR_STOCK,
    TOOL_GET_INDUSTRY_CHAIN, TOOL_FIND_STOCKS_IN_CHAIN,
    TOOL_SEARCH_ANNOUNCEMENTS, TOOL_FETCH_STOCK_REPORTS, TOOL_FETCH_STOCK_NEWS,
    TOOL_SEARCH_POLICY_CONTENT, TOOL_FETCH_ANNOUNCEMENT_CONTENT,
    TOOL_SEARCH_KNOWLEDGE,
    TOOL_GET_REPORT_RATING, TOOL_GET_MAINBIZ_DETAIL,
]

TOOL_FUNCTIONS = {
    "search_reports": search_reports,
    "search_reports_by_industry": search_reports_by_industry,
    "search_policy": search_policy,
    "match_hot_money": match_hot_money,
    "get_north_individual": get_north_individual,
    "search_news": search_news,
    "get_theme_members": get_theme_members,
    "classify_events": classify_events,
    "search_news_for_stock_tool": search_news_for_stock_tool,
    "get_industry_chain": get_industry_chain,
    "find_stocks_in_chain": find_stocks_in_chain,
    "search_announcements": search_announcements,
    "fetch_stock_reports": fetch_stock_reports,
    "fetch_stock_news": fetch_stock_news,
    "search_policy_content": search_policy_content,
    "fetch_announcement_content": fetch_announcement_content,
    "search_knowledge": search_knowledge,
    "get_report_rating": get_report_rating,
    "get_mainbiz_detail": get_mainbiz_detail,
}
