"""Tests for agents.hypothesis_critic — 假设模式逻辑审查。"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest


_GOOD_CRITIC_JSON = json.dumps({
    "challenges": [
        {
            "dimension": "假设前提",
            "challenge": "光通信需求增长的核心驱动力是AI算力扩张，但AI资本开支周期可能在2027年见顶",
            "severity": "medium",
            "unverified": True,
        },
        {
            "dimension": "证据质量",
            "challenge": "营收从0到1.38亿的数据来自单一研报，未交叉验证",
            "severity": "minor",
            "unverified": False,
        },
        {
            "dimension": "竞争/替代",
            "challenge": "国内InP衬底竞争者包括中科晶电、通美晶体，技术壁垒需验证",
            "severity": "medium",
            "unverified": True,
        },
    ],
    "fatal_flaws": [],
    "hypothesis_survives": True,
    "adjusted_confidence": 0.55,
    "recommendation": "watch",
    "review_summary": "投资假设的产业逻辑基本成立，但3个关键前提未被充分验证",
})

_FATAL_FLAW_JSON = json.dumps({
    "challenges": [
        {
            "dimension": "假设前提",
            "challenge": "核心业务逻辑被证伪：公司声称的InP产能实际为代工模式",
            "severity": "critical",
            "unverified": False,
        },
    ],
    "fatal_flaws": ["核心业务逻辑被证伪"],
    "hypothesis_survives": False,
    "adjusted_confidence": 0.15,
    "recommendation": "avoid",
    "review_summary": "发现致命缺陷，建议回避",
})

_CRITICAL_WITHOUT_FATAL = json.dumps({
    "challenges": [
        {
            "dimension": "假设前提",
            "challenge": "财务数据存在造假嫌疑",
            "severity": "critical",
            "unverified": False,
        },
    ],
    "fatal_flaws": [],
    "hypothesis_survives": True,
    "adjusted_confidence": 0.3,
    "recommendation": "satellite",
    "review_summary": "存在严重问题",
})

_SAMPLE_HYPOTHESIS_RESULT = {
    "ts_code": "002428.SZ",
    "stock_name": "云南锗业",
    "trade_date": "20260402",
    "phase1": {
        "hypothesis": "云南锗业正从传统锗业向化合物半导体材料转型",
        "questions": ["化合物半导体营收增速？", "InP供需格局？", "锗价影响？"],
        "stock_type": "industry_logic",
    },
    "phase3": {
        "hypothesis": "云南锗业正从传统锗业向化合物半导体材料转型",
        "hypothesis_valid": True,
        "confidence": 0.65,
        "evidence_for": ["营收从0到1.38亿", "InP供不应求"],
        "evidence_against": ["扣非净利润亏损"],
        "key_risks": ["锗价波动"],
        "catalyst": "Q2 财报",
        "suggestion": "观察",
        "position_type": "watch",
    },
}


class TestHypothesisCriticNode:
    def test_happy_path(self):
        import agents.hypothesis_critic as mod
        with patch.object(mod, "call_kimi", return_value={"content": _GOOD_CRITIC_JSON}):
            result = mod.hypothesis_critic_node(_SAMPLE_HYPOTHESIS_RESULT)

        assert result["hypothesis_survives"] is True
        assert result["adjusted_confidence"] == 0.55
        assert result["recommendation"] == "watch"
        assert len(result["challenges"]) == 3
        assert not result["fatal_flaws"]

    def test_fatal_flaw_forces_avoid(self):
        import agents.hypothesis_critic as mod
        with patch.object(mod, "call_kimi", return_value={"content": _FATAL_FLAW_JSON}):
            result = mod.hypothesis_critic_node(_SAMPLE_HYPOTHESIS_RESULT)

        assert result["hypothesis_survives"] is False
        assert result["recommendation"] == "avoid"
        assert len(result["fatal_flaws"]) > 0

    def test_critical_severity_auto_populates_fatal_flaws(self):
        """severity=critical 的挑战应自动填充 fatal_flaws（如果 LLM 忘了填）。"""
        import agents.hypothesis_critic as mod
        with patch.object(mod, "call_kimi", return_value={"content": _CRITICAL_WITHOUT_FATAL}):
            result = mod.hypothesis_critic_node(_SAMPLE_HYPOTHESIS_RESULT)

        assert len(result["fatal_flaws"]) == 1
        assert result["recommendation"] == "avoid"
        assert result["hypothesis_survives"] is False

    def test_json_parse_failure_fallback_to_watch(self):
        """JSON 解析失败时 fallback 为 watch，不是 reject。"""
        import agents.hypothesis_critic as mod
        with patch.object(mod, "call_kimi", return_value={"content": "这不是JSON输出"}):
            result = mod.hypothesis_critic_node(_SAMPLE_HYPOTHESIS_RESULT)

        assert result["hypothesis_survives"] is True
        assert result["recommendation"] == "watch"
        assert result["adjusted_confidence"] == 0.5

    def test_fills_missing_keys(self):
        import agents.hypothesis_critic as mod
        partial = json.dumps({"hypothesis_survives": True, "adjusted_confidence": 0.7})
        with patch.object(mod, "call_kimi", return_value={"content": partial}):
            result = mod.hypothesis_critic_node(_SAMPLE_HYPOTHESIS_RESULT)

        assert "challenges" in result
        assert "fatal_flaws" in result
        assert "recommendation" in result
        assert "review_summary" in result

    def test_uses_tier_a(self):
        """验证 Critic 使用 Tier A（thinking 开 + max_tokens=32768）。"""
        import agents.hypothesis_critic as mod
        with patch.object(mod, "call_kimi", return_value={"content": _GOOD_CRITIC_JSON}) as mock_kimi:
            mod.hypothesis_critic_node(_SAMPLE_HYPOTHESIS_RESULT)
            call_kwargs = mock_kimi.call_args
            assert call_kwargs.kwargs.get("thinking") is True or \
                   call_kwargs[1].get("thinking") is True

    def test_empty_phase3(self):
        """phase3 为空时不崩溃。"""
        import agents.hypothesis_critic as mod
        empty_input = {"ts_code": "000001.SZ", "stock_name": "测试", "phase3": {}}
        with patch.object(mod, "call_kimi", return_value={"content": _GOOD_CRITIC_JSON}):
            result = mod.hypothesis_critic_node(empty_input)
        assert result["hypothesis_survives"] is True


class TestFormatCriticInput:
    def test_formats_all_sections(self):
        from agents.hypothesis_critic import _format_critic_input

        text = _format_critic_input(_SAMPLE_HYPOTHESIS_RESULT["phase3"])
        assert "投资假设" in text
        assert "正面证据" in text
        assert "负面证据" in text
        assert "关键风险" in text
        assert "当前建议" in text

    def test_handles_empty_phase3(self):
        from agents.hypothesis_critic import _format_critic_input

        text = _format_critic_input({})
        assert "当前建议" in text
