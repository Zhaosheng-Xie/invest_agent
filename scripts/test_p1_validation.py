"""P1 集成验收脚本 — 验证 4 个 P1 模块协同工作"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def test_1_all_tools_registered():
    """验证所有 P1 新增工具都已注册"""
    from tools.agent_tools import ALL_TOOLS, TOOL_FUNCTIONS

    required_tools = [
        "search_reports_by_industry",
        "search_news_for_stock_tool",
        "get_industry_chain",
        "find_stocks_in_chain",
    ]
    for tool_name in required_tools:
        assert any(
            t["function"]["name"] == tool_name for t in ALL_TOOLS
        ), f"{tool_name} not in ALL_TOOLS"
        assert tool_name in TOOL_FUNCTIONS, f"{tool_name} not in TOOL_FUNCTIONS"
    print("PASS: 所有 P1 工具已注册")


def test_2_consensus_module():
    """验证卖方一致预期模块"""
    from tools.consensus import build_consensus

    result = build_consensus("999999.SZ", days=7)
    assert "coverage_count" in result
    print(f"PASS: consensus 模块可用，coverage={result['coverage_count']}")


def test_3_news_search_module():
    """验证新闻检索模块"""
    from tools.news_search import search_news_for_stock, extract_mainbz_keywords

    result = search_news_for_stock("999999.SZ", "测试股票")
    assert "news_count" in result
    print(f"PASS: news_search 模块可用，news_count={result['news_count']}")


def test_4_industry_map_module():
    """验证产业链映射模块"""
    from sandboxes.data.industry_map import get_stock_industries, find_related_stocks

    result = get_stock_industries("002428.SZ")
    assert "mainbz_keywords" in result
    print(f"PASS: industry_map 模块可用，keywords={result['mainbz_keywords']}")


def test_5_hypothesis_engine_has_all_phases():
    """验证 hypothesis_engine 包含 Phase 1-4"""
    import inspect
    import harness.hypothesis_engine as mod

    source = inspect.getsource(mod)
    assert "phase1" in source.lower() or "Phase 1" in source, "缺少 Phase 1"
    assert "build_consensus" in source, "缺少 consensus 调用"
    assert "search_news_for_stock" in source, "缺少 news 调用"
    assert "hypothesis_critic_node" in source, "缺少 Phase 4 Critic"
    assert "_run_phase2" in source, "缺少 Phase 2"
    assert "_run_phase3" in source, "缺少 Phase 3"
    print("PASS: hypothesis_engine 包含所有 4 个 Phase")


if __name__ == "__main__":
    tests = [
        test_1_all_tools_registered,
        test_2_consensus_module,
        test_3_news_search_module,
        test_4_industry_map_module,
        test_5_hypothesis_engine_has_all_phases,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__} — {e}")
            failed += 1
    print(f"\n集成验收：{passed} passed / {failed} failed")
