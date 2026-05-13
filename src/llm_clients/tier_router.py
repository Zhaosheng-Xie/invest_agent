"""Tier-based model parameter router for Kimi K2.6 agents."""

from __future__ import annotations

TIER_CONFIG: dict[str, dict] = {
    "A": {"thinking": True, "max_tokens": 32768},
    "B_thinking": {"thinking": True, "max_tokens": 8192},
    "B_recall": {"thinking": False, "max_tokens": 8192},
}

AGENT_TIER_MAP: dict[str, str] = {
    "supervisor": "A",
    "critic": "A",
    "risk": "B_recall",
    "macro": "B_recall",
    "event": "B_recall",
    "flow_hot": "B_recall",
    "fund": "B_recall",
    "tech": "B_recall",
    "flow_inst": "B_recall",
    "backtest": "B_recall",
    "hypothesis_scan": "B_recall",
    "hypothesis_verify": "B_recall",
    "hypothesis_judge": "B_thinking",
    "hypothesis_critic": "A",
}

_DEFAULT_TIER = "B_recall"


def get_tier_config(agent_name: str) -> dict:
    """返回该 agent 对应的 Kimi 调用参数 {"thinking": bool, "max_tokens": int}"""
    tier = AGENT_TIER_MAP.get(agent_name, _DEFAULT_TIER)
    return dict(TIER_CONFIG[tier])
