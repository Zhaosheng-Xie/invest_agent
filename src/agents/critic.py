"""Critic Agent — 独立挑刺节点（GAN 模式）。"""
from __future__ import annotations

import json
from pathlib import Path

from agents.state import MarketState
from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config

_PROMPT_PATH = Path(__file__).parent / "prompts" / "critic.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


_SUMMARY_KEYS = ("score", "summary", "highlights", "risks", "verdict", "direction", "confidence")


def _slim(agent_data: dict) -> dict:
    """只保留 Critic 需要审查的关键字段，减少 token 消耗。"""
    return {k: v for k, v in agent_data.items() if k in _SUMMARY_KEYS and v}


def _format_prior_analysis(state: MarketState) -> str:
    """将前序 agent 的分析结果格式化为精简文本。"""
    sections = [
        ("基本面分析", "fundamental_score"),
        ("技术面分析", "technical_score"),
        ("宏观/主题分析", "macro_themes"),
        ("事件分析", "event_analysis"),
        ("机构资金", "flow_institutional"),
        ("游资动向", "flow_hot_money"),
        ("风控评估", "risk_assessment"),
        ("回测结果", "backtest_result"),
    ]
    parts = []
    for title, key in sections:
        if key in state and state[key]:
            parts.append(f"## {title}\n{json.dumps(_slim(state[key]), ensure_ascii=False, default=str)}")

    return "\n\n".join(parts) if parts else "（暂无前序分析结果）"


def critic_node(state: MarketState) -> dict:
    """LangGraph 节点函数：独立挑刺评审。"""
    ts_code = state.get("ts_code", "")
    stock_name = state.get("stock_name", ts_code)

    system_prompt = _load_prompt()
    prior_analysis = _format_prior_analysis(state)

    user_message = f"请对 {stock_name}（{ts_code}）的以下分析进行独立评审：\n\n{prior_analysis}"

    tier = get_tier_config("critic")
    response = call_kimi(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        **tier,
    )

    content = response["content"]
    try:
        start_idx = content.index("{")
        end_idx = content.rindex("}") + 1
        result = json.loads(content[start_idx:end_idx])
        if "score" in result:
            result["verdict"] = "pass" if result["score"] >= 60 else "reject"
    except (ValueError, json.JSONDecodeError):
        result = {
            "score": 50,
            "objections": ["Critic LLM 输出解析失败"],
            "worst_case": "无法评估",
            "verdict": "reject",
        }

    return {"critic_review": result}
