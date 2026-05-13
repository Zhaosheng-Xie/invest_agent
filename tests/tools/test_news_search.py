"""Tests for tools.news_search — 个股级新闻检索。"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from sandboxes.data import duckdb_store
from sandboxes.data.duckdb_store import upsert, _connections


@pytest.fixture(autouse=True)
def _clean_duckdb():
    """每个测试用例使用独立的 :memory: 数据库。"""
    _connections.pop(":memory:", None)
    yield
    _connections.pop(":memory:", None)


def _insert_news(rows: list[dict]) -> None:
    upsert("news", rows, ["title", "source"], db_path=":memory:")


class TestExtractMainbzKeywords:
    def test_basic_extraction(self):
        from tools.news_search import extract_mainbz_keywords

        data = [
            {"bz_item": "锗产品"},
            {"bz_item": "化合物半导体材料"},
            {"bz_item": "光伏组件"},
        ]
        kws = extract_mainbz_keywords(data)
        assert "锗产品" in kws
        assert "化合物半导体材料" in kws
        assert "光伏组件" in kws

    def test_filters_stop_words(self):
        from tools.news_search import extract_mainbz_keywords

        data = [
            {"bz_item": "其他"},
            {"bz_item": "合计"},
            {"bz_item": "锗产品"},
        ]
        kws = extract_mainbz_keywords(data)
        assert "其他" not in kws
        assert "合计" not in kws
        assert "锗产品" in kws

    def test_empty_input(self):
        from tools.news_search import extract_mainbz_keywords

        assert extract_mainbz_keywords([]) == []

    def test_splits_long_names(self):
        from tools.news_search import extract_mainbz_keywords

        data = [{"bz_item": "化合物半导体材料"}]
        kws = extract_mainbz_keywords(data)
        assert len(kws) > 1

    def test_deduplicates(self):
        from tools.news_search import extract_mainbz_keywords

        data = [{"bz_item": "锗产品"}, {"bz_item": "锗产品"}]
        kws = extract_mainbz_keywords(data)
        assert kws.count("锗产品") == 1


class TestSearchNewsForStock:
    def test_happy_path(self):
        from tools.news_search import search_news_for_stock

        _insert_news([
            {"title": "InP衬底涨价30%，化合物半导体景气上行", "time": "2099-01-01 10:00", "source": "cls"},
            {"title": "锗价格持续走高", "time": "2099-01-01 09:00", "source": "jin10"},
            {"title": "今日A股午评", "time": "2099-01-01 12:00", "source": "cls"},
        ])

        result = search_news_for_stock(
            ts_code="002428.SZ",
            stock_name="云南锗业",
            mainbz_keywords=["化合物半导体"],
            days=3650,
            db_path=":memory:",
        )

        assert result["ts_code"] == "002428.SZ"
        assert result["news_count"] >= 1
        assert len(result["keywords_used"]) >= 1
        titles = [n["title"] for n in result["news"]]
        assert any("化合物半导体" in t or "锗" in t for t in titles)

    def test_no_news_table(self):
        from tools.news_search import search_news_for_stock

        result = search_news_for_stock(
            ts_code="002428.SZ",
            stock_name="云南锗业",
            days=7,
            db_path=":memory:",
        )

        assert result["news_count"] == 0
        assert isinstance(result["news"], list)

    def test_empty_keywords(self):
        from tools.news_search import search_news_for_stock

        result = search_news_for_stock(
            ts_code="002428.SZ",
            stock_name="",
            mainbz_keywords=[],
            days=7,
            db_path=":memory:",
        )

        assert result["news_count"] == 0
        assert "无有效关键词" in result["summary"]

    def test_relevance_tagging(self):
        from tools.news_search import search_news_for_stock

        _insert_news([
            {"title": "云南锗业发布年报", "time": "2099-01-01 10:00", "source": "cls"},
            {"title": "锗价格波动", "time": "2099-01-01 09:00", "source": "jin10"},
        ])

        result = search_news_for_stock(
            ts_code="002428.SZ",
            stock_name="云南锗业",
            days=3650,
            db_path=":memory:",
        )

        high_news = [n for n in result["news"] if n["relevance"] == "high"]
        medium_news = [n for n in result["news"] if n["relevance"] == "medium"]
        assert any("云南锗业" in n["title"] for n in high_news)

    def test_deduplicates_across_keywords(self):
        from tools.news_search import search_news_for_stock

        _insert_news([
            {"title": "锗和化合物半导体行业报告", "time": "2099-01-01 10:00", "source": "cls"},
        ])

        result = search_news_for_stock(
            ts_code="002428.SZ",
            stock_name="云南锗业",
            mainbz_keywords=["化合物半导体"],
            days=3650,
            db_path=":memory:",
        )

        titles = [n["title"] for n in result["news"]]
        assert titles.count("锗和化合物半导体行业报告") == 1

    def test_summary_format(self):
        from tools.news_search import search_news_for_stock

        _insert_news([
            {"title": "云南锗业产品需求旺盛", "time": "2099-01-01 10:00", "source": "cls"},
        ])

        result = search_news_for_stock(
            ts_code="002428.SZ",
            stock_name="云南锗业",
            days=3650,
            db_path=":memory:",
        )

        assert "近" in result["summary"]
        assert result["news_count"] >= 1
