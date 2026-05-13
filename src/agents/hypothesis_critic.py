"""Hypothesis Critic — 对假设驱动分析做结构化逻辑审查。"""
from __future__ import annotations

import json
from pathlib import Path

from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config

_PROMPT_PATH = Path(__file__).parent / "prompts" / "hypothesis_critic.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _extract_json(text: str) -> dict | None:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


def _format_critic_input(phase3: dict, phase1: dict | None = None) -> str:
    """将 Phase 3 输出格式化为 Critic 的输入文本。"""
    parts = []

    hypothesis = phase3.get("hypothesis", "")
    if hypothesis:
        parts.append(f"## 投资假设\n{hypothesis}")

    evidence_for = phase3.get("evidence_for", [])
    if evidence_for:
        items = "\n".join(f"- {e}" for e in evidence_for)
        parts.append(f"## 正面证据\n{items}")

    evidence_against = phase3.get("evidence_against", [])
    if evidence_against:
        items = "\n".join(f"- {e}" for e in evidence_against)
        parts.append(f"## 负面证据\n{items}")

    key_risks = phase3.get("key_risks", [])
    if key_risks:
        items = "\n".join(f"- {r}" for r in key_risks)
        parts.append(f"## 关键风险\n{items}")

    position_type = phase3.get("position_type", "")
    confidence = phase3.get("confidence", 0)
    suggestion = phase3.get("suggestion", "")
    parts.append(
        f"## 当前建议\n"
        f"- 建议仓位：{position_type}\n"
        f"- 置信度：{confidence}\n"
        f"- 建议理由：{suggestion}"
    )

    catalyst = phase3.get("catalyst", "")
    if catalyst:
        parts.append(f"## 催化剂\n{catalyst}")

    return "\n\n".join(parts)


_SAFE_FALLBACK = {
    "challenges": [],
    "fatal_flaws": [],
    "hypothesis_survives": True,
    "adjusted_confidence": 0.5,
    "recommendation": "watch",
    "review_summary": "Critic LLM 输出解析失败，保守通过",
}


def hypothesis_critic_node(hypothesis_result: dict) -> dict:
    """对假设驱动分析的结果做逻辑审查。

    输入：run_hypothesis_analysis 的输出（含 phase1, phase3 等）
    输出：critic 审查结果 dict
    """
    phase3 = hypothesis_result.get("phase3", {})
    phase1 = hypothesis_result.get("phase1", {})
    stock_name = hypothesis_result.get("stock_name", "")
    ts_code = hypothesis_result.get("ts_code", "")

    system_prompt = _load_prompt()
    critic_input = _format_critic_input(phase3, phase1)

    user_message = (
        f"请对以下关于 {stock_name}（{ts_code}）的投资假设进行逻辑审查：\n\n"
        f"{critic_input}"
    )

    tier = get_tier_config("hypothesis_critic")
    response = call_kimi(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        **tier,
    )

    content = response.get("content", "")
    result = _extract_json(content)

    if result is None:
        return dict(_SAFE_FALLBACK)

    defaults = {
        "challenges": [],
        "fatal_flaws": [],
        "hypothesis_survives": True,
        "adjusted_confidence": 0.5,
        "recommendation": "watch",
        "review_summary": "",
    }
    for k, v in defaults.items():
        if k not in result:
            result[k] = v

    critical_challenges = [
        c for c in result.get("challenges", [])
        if c.get("severity") == "critical"
    ]
    if critical_challenges and not result["fatal_flaws"]:
        result["fatal_flaws"] = [c["challenge"] for c in critical_challenges]

    if result["fatal_flaws"]:
        result["recommendation"] = "avoid"
        result["hypothesis_survives"] = False

    return result
