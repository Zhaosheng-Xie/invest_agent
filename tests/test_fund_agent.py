"""Tests for agents.fund — mock Kimi + mock tushare。"""
from unittest.mock import patch, MagicMock, call
import json

import pytest

from agents.fund import fund_node, _fetch_data, _calc_mutation_rate


@patch("agents.fund.time.sleep")
@patch("agents.fund.tushare_client")
def test_fetch_data(mock_ts, mock_sleep):
    """验证 _fetch_data 调用正确的接口。"""
    mock_ts.get_income.return_value = {"status": "ok", "data": [{"revenue": 1000}]}
    mock_ts.get_balancesheet.return_value = {"status": "ok", "data": []}
    mock_ts.get_cashflow.return_value = {"status": "ok", "data": []}
    mock_ts.get_fina_indicator.return_value = {"status": "ok", "data": []}
    mock_ts.get_forecast.return_value = {"status": "ok", "data": []}
    mock_ts.get_daily_basic.return_value = {"status": "ok", "data": []}
    mock_ts.get_fina_mainbz.return_value = {"status": "ok", "data": [{"bz_item": "test", "bz_sales": 100}]}
    mock_ts.get_stk_holdernumber.return_value = {"status": "ok", "data": [{"test": 1}]}
    mock_ts.get_research_report.return_value = {"status": "ok", "data": [{"test": 1}]}
    mock_ts.get_stk_surv.return_value = {"status": "ok", "data": [{"test": 1}]}
    mock_ts.get_moneyflow.return_value = {"status": "ok", "data": [{"test": 1}]}

    data = _fetch_data("000988.SZ", "20260430")
    assert "income" in data
    mock_ts.get_income.assert_called_once()
    assert mock_ts.get_fina_mainbz.call_count == 5


@patch("agents.fund.time.sleep")
@patch("agents.fund.run_agent_with_tools")
@patch("agents.fund.tushare_client")
def test_fund_node_success(mock_ts, mock_run, mock_sleep):
    """验证 fund_node 正常流程。"""
    for attr in [
        "get_income", "get_balancesheet", "get_cashflow",
        "get_fina_indicator", "get_forecast", "get_daily_basic",
        "get_fina_mainbz", "get_stk_holdernumber", "get_research_report",
        "get_stk_surv", "get_moneyflow",
    ]:
        getattr(mock_ts, attr).return_value = {"status": "ok", "data": [{"bz_item": "test", "bz_sales": 100}]}

    mock_run.return_value = {
        "content": json.dumps({
            "score": 75,
            "highlights": ["营收增长"],
            "risks": ["应收账款高"],
            "data_sources": ["income"],
            "summary": "基本面良好",
        }),
        "reasoning_content": None,
        "tool_calls_made": [],
    }

    state = {"ts_code": "000988.SZ", "trade_date": "20260430", "stock_name": "华工科技"}
    result = fund_node(state)

    assert "fundamental_score" in result
    assert result["fundamental_score"]["score"] == 75


@patch("agents.fund.time.sleep")
@patch("agents.fund.run_agent_with_tools")
@patch("agents.fund.tushare_client")
def test_fund_node_llm_parse_failure(mock_ts, mock_run, mock_sleep):
    """验证 LLM 输出非 JSON 时的降级处理。"""
    for attr in [
        "get_income", "get_balancesheet", "get_cashflow",
        "get_fina_indicator", "get_forecast", "get_daily_basic",
        "get_fina_mainbz", "get_stk_holdernumber", "get_research_report",
        "get_stk_surv", "get_moneyflow",
    ]:
        getattr(mock_ts, attr).return_value = {"status": "ok", "data": []}

    mock_run.return_value = {
        "content": "这不是一个 JSON 格式的响应",
        "reasoning_content": None,
        "tool_calls_made": [],
    }

    state = {"ts_code": "000988.SZ", "trade_date": "20260430"}
    result = fund_node(state)

    assert result["fundamental_score"]["score"] == 50
    assert "LLM 输出解析失败" in result["fundamental_score"]["risks"]


class TestCalcMutationRate:
    """_calc_mutation_rate 计算逻辑测试。"""

    def test_basic_mutation(self):
        """有新增业务+占比大幅变化时，mutation_score 应较高。"""
        data = [
            {"bz_item": "传统锗产品", "bz_sales": 800_000_000, "period": "20201231"},
            {"bz_item": "光伏新能源", "bz_sales": 200_000_000, "period": "20201231"},
            {"bz_item": "传统锗产品", "bz_sales": 500_000_000, "period": "20241231"},
            {"bz_item": "光伏新能源", "bz_sales": 300_000_000, "period": "20241231"},
            {"bz_item": "化合物半导体", "bz_sales": 200_000_000, "period": "20241231"},
        ]
        result = _calc_mutation_rate(data)
        assert result["mutation_score"] > 0
        assert result["years_covered"] == 2
        assert len(result["new_businesses"]) == 1
        assert result["new_businesses"][0]["name"] == "化合物半导体"
        assert result["new_businesses"][0]["latest_pct"] == pytest.approx(20.0, abs=0.1)
        assert "化合物半导体" in result["summary"]

    def test_no_change(self):
        """业务结构无变化时，score 应为 0。"""
        data = [
            {"bz_item": "业务A", "bz_sales": 500, "period": "20201231"},
            {"bz_item": "业务B", "bz_sales": 500, "period": "20201231"},
            {"bz_item": "业务A", "bz_sales": 500, "period": "20241231"},
            {"bz_item": "业务B", "bz_sales": 500, "period": "20241231"},
        ]
        result = _calc_mutation_rate(data)
        assert result["mutation_score"] == 0
        assert result["new_businesses"] == []
        assert result["growing_businesses"] == []
        assert result["declining_businesses"] == []
        assert "稳定" in result["summary"]

    def test_single_period(self):
        """只有一期数据时，无法计算突变率。"""
        data = [
            {"bz_item": "业务A", "bz_sales": 1000, "period": "20241231"},
        ]
        result = _calc_mutation_rate(data)
        assert result["mutation_score"] == 0
        assert result["years_covered"] == 1
        assert "数据不足" in result["summary"]

    def test_score_capped_at_100(self):
        """大量新增业务时，score 应 cap 在 100。"""
        data = [
            {"bz_item": "老业务", "bz_sales": 1000, "period": "20201231"},
        ]
        for i in range(10):
            data.append({"bz_item": f"新业务{i}", "bz_sales": 200, "period": "20241231"})
        result = _calc_mutation_rate(data)
        assert result["mutation_score"] <= 100

    def test_declining_business(self):
        """业务消失时应被记录为 declining。"""
        data = [
            {"bz_item": "将消失业务", "bz_sales": 500, "period": "20201231"},
            {"bz_item": "持续业务", "bz_sales": 500, "period": "20201231"},
            {"bz_item": "持续业务", "bz_sales": 1000, "period": "20241231"},
        ]
        result = _calc_mutation_rate(data)
        assert len(result["declining_businesses"]) == 1
        assert result["declining_businesses"][0]["name"] == "将消失业务"

    def test_fuzzy_match(self):
        """名称略有不同但前 4 字符相同的业务应做模糊匹配。"""
        data = [
            {"bz_item": "光伏组件销售", "bz_sales": 500, "period": "20201231"},
            {"bz_item": "光伏组件及配件", "bz_sales": 500, "period": "20241231"},
        ]
        result = _calc_mutation_rate(data)
        assert result["new_businesses"] == []


@patch("agents.fund.time.sleep")
@patch("agents.fund.tushare_client")
def test_fetch_data_5year_mainbz(mock_ts, mock_sleep):
    """验证 _fetch_data 取 5 年 fina_mainbz 数据。"""
    mock_ts.get_income.return_value = {"status": "ok", "data": []}
    mock_ts.get_balancesheet.return_value = {"status": "ok", "data": []}
    mock_ts.get_cashflow.return_value = {"status": "ok", "data": []}
    mock_ts.get_fina_indicator.return_value = {"status": "ok", "data": []}
    mock_ts.get_forecast.return_value = {"status": "ok", "data": []}
    mock_ts.get_daily_basic.return_value = {"status": "ok", "data": []}
    mock_ts.get_stk_holdernumber.return_value = {"status": "ok", "data": []}
    mock_ts.get_research_report.return_value = {"status": "ok", "data": []}
    mock_ts.get_stk_surv.return_value = {"status": "ok", "data": []}
    mock_ts.get_moneyflow.return_value = {"status": "ok", "data": []}

    def fake_mainbz(ts_code, period, type=""):
        return {"status": "ok", "data": [
            {"bz_item": "业务A", "bz_sales": 1000},
            {"bz_item": "业务B", "bz_sales": 500},
        ]}

    mock_ts.get_fina_mainbz.side_effect = fake_mainbz

    data = _fetch_data("002428.SZ", "20260430")

    assert mock_ts.get_fina_mainbz.call_count == 5
    expected_periods = ["20251231", "20241231", "20231231", "20221231", "20211231"]
    for p in expected_periods:
        mock_ts.get_fina_mainbz.assert_any_call(ts_code="002428.SZ", period=p, type="P")

    assert "fina_mainbz" in data
    assert len(data["fina_mainbz"]) == 10  # 5 years × 2 items
    assert all(item.get("period") for item in data["fina_mainbz"])
    assert "biz_mutation_rate" in data
    assert data["biz_mutation_rate"]["mutation_score"] == 0  # same structure each year

    assert mock_sleep.call_count == 5
