"""Tests for tools.consensus — 卖方一致预期。"""
from __future__ import annotations

import pytest

from sandboxes.data import duckdb_store
from sandboxes.data.duckdb_store import upsert


@pytest.fixture(autouse=True)
def _clean_duckdb():
    yield
    duckdb_store._connections.clear()


def _insert_reports(reports: list[dict], db_path: str = ":memory:"):
    upsert("research_report", reports, ["title", "trade_date"], db_path=db_path)


class TestBuildConsensus:
    def test_normal(self):
        _insert_reports([
            {"title": "云南锗业深度报告", "inst_csname": "中信证券", "trade_date": "20260510",
             "abstr": "维持买入评级，化合物半导体业务高增长", "ts_code": "002428.SZ", "name": "云南锗业", "ind_name": "半导体"},
            {"title": "云南锗业跟踪", "inst_csname": "东吴证券", "trade_date": "20260509",
             "abstr": "首次覆盖，给予增持评级", "ts_code": "002428.SZ", "name": "云南锗业", "ind_name": "半导体"},
            {"title": "云南锗业业绩点评", "inst_csname": "国盛证券", "trade_date": "20260508",
             "abstr": "业绩符合预期，中性评级", "ts_code": "002428.SZ", "name": "云南锗业", "ind_name": "半导体"},
        ])

        from tools.consensus import build_consensus
        result = build_consensus("002428.SZ", days=30, db_path=":memory:")

        assert result["ts_code"] == "002428.SZ"
        assert result["coverage_count"] == 3
        assert result["broker_count"] == 3
        assert "中信证券" in result["brokers"]
        assert "东吴证券" in result["brokers"]
        assert result["rating_distribution"]["买入"] == 1
        assert result["rating_distribution"]["增持"] == 1
        assert result["rating_distribution"]["中性"] == 1
        assert len(result["recent_reports"]) == 3
        assert "偏正面" in result["summary"]

    def test_no_reports(self):
        from tools.consensus import build_consensus
        result = build_consensus("999999.SZ", days=30, db_path=":memory:")

        assert result["coverage_count"] == 0
        assert result["broker_count"] == 0
        assert result["brokers"] == []
        assert result["rating_distribution"] == {}
        assert result["recent_reports"] == []
        assert "无券商覆盖" in result["summary"]

    def test_positive_tone(self):
        _insert_reports([
            {"title": "报告A", "inst_csname": "券商A", "trade_date": "20260510",
             "abstr": "强烈推荐，目标价50元", "ts_code": "002428.SZ", "name": "云南锗业", "ind_name": ""},
            {"title": "报告B", "inst_csname": "券商B", "trade_date": "20260510",
             "abstr": "维持买入，上调盈利预测", "ts_code": "002428.SZ", "name": "云南锗业", "ind_name": ""},
            {"title": "报告C", "inst_csname": "券商C", "trade_date": "20260510",
             "abstr": "增持评级不变", "ts_code": "002428.SZ", "name": "云南锗业", "ind_name": ""},
        ])

        from tools.consensus import build_consensus
        result = build_consensus("002428.SZ", days=30, db_path=":memory:")

        assert result["rating_distribution"]["买入"] == 2
        assert result["rating_distribution"]["增持"] == 1
        assert "偏正面" in result["summary"]

    def test_name_match(self):
        """ts_code 不含6位前缀但 name 字段包含时也能匹配。"""
        _insert_reports([
            {"title": "行业深度", "inst_csname": "中信证券", "trade_date": "20260510",
             "abstr": "买入", "ts_code": "", "name": "002428", "ind_name": "半导体"},
        ])

        from tools.consensus import build_consensus
        result = build_consensus("002428.SZ", days=30, db_path=":memory:")
        assert result["coverage_count"] == 1


class TestExtractRating:
    def test_all_ratings(self):
        from tools.consensus import _extract_rating

        assert _extract_rating("强烈推荐，目标价20元") == "买入"
        assert _extract_rating("维持买入评级") == "买入"
        assert _extract_rating("首次覆盖推荐") == "买入"
        assert _extract_rating("维持增持评级") == "增持"
        assert _extract_rating("谨慎推荐") == "增持"
        assert _extract_rating("中性评级") == "中性"
        assert _extract_rating("持有评级") == "中性"
        assert _extract_rating("下调至减持") == "减持"
        assert _extract_rating("卖出评级") == "卖出"
        assert _extract_rating("建议回避") == "卖出"

    def test_unrecognized(self):
        from tools.consensus import _extract_rating

        assert _extract_rating("业绩符合预期") == "未识别"
        assert _extract_rating("") == "未识别"
        assert _extract_rating(None) == "未识别"
