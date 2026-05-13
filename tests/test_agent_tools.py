"""Tests for tools/agent_tools.py — 7 个 tool 各 1 个 mock 测试。"""
from unittest.mock import patch, MagicMock
import pytest

from sandboxes.data import duckdb_store
from sandboxes.data.duckdb_store import upsert


@pytest.fixture(autouse=True)
def _clean_duckdb():
    yield
    duckdb_store._connections.clear()


def _setup_table(table_name, records, keys, db_path=":memory:"):
    """向 :memory: 数据库写入测试数据。"""
    upsert(table_name, records, keys, db_path=db_path)


class TestSearchReports:
    def test_found(self):
        _setup_table("research_report", [
            {"title": "光模块行业深度", "inst_csname": "中信证券", "report_type": "行业",
             "trade_date": "20260505", "abstr": "看好光模块", "name": "", "ts_code": ""},
        ], ["title", "trade_date"])
        from tools.agent_tools import search_reports
        result = search_reports("光模块", db_path=":memory:")
        assert "光模块" in result
        assert "中信证券" in result


class TestSearchReportsByIndustry:
    def test_industry_only(self):
        _setup_table("research_report", [
            {"title": "光通信行业深度", "inst_csname": "中信证券", "report_type": "行业",
             "trade_date": "20260510", "abstr": "看好光通信", "name": "", "ts_code": "",
             "ind_name": "光通信"},
        ], ["title", "trade_date"])
        from tools.agent_tools import search_reports_by_industry
        result = search_reports_by_industry("光通信", db_path=":memory:")
        assert "光通信" in result
        assert "中信证券" in result

    def test_industry_plus_stock(self):
        _setup_table("research_report", [
            {"title": "光通信行业深度", "inst_csname": "中信证券", "report_type": "行业",
             "trade_date": "20260510", "abstr": "看好光通信", "name": "", "ts_code": "",
             "ind_name": "光通信"},
            {"title": "云南锗业深度", "inst_csname": "东吴证券", "report_type": "个股",
             "trade_date": "20260509", "abstr": "增持", "name": "云南锗业", "ts_code": "002428.SZ",
             "ind_name": "半导体"},
        ], ["title", "trade_date"])
        from tools.agent_tools import search_reports_by_industry
        result = search_reports_by_industry("光通信", ts_code="002428.SZ", db_path=":memory:")
        assert "光通信" in result
        assert "云南锗业" in result

    def test_dedup(self):
        _setup_table("research_report", [
            {"title": "重复报告", "inst_csname": "券商A", "report_type": "行业",
             "trade_date": "20260510", "abstr": "内容", "name": "002428",
             "ts_code": "002428.SZ", "ind_name": "光通信"},
        ], ["title", "trade_date"])
        from tools.agent_tools import search_reports_by_industry
        result = search_reports_by_industry("光通信", ts_code="002428.SZ", db_path=":memory:")
        assert result.count("重复报告") == 1

    def test_no_match(self):
        _setup_table("research_report", [
            {"title": "占位", "inst_csname": "", "report_type": "",
             "trade_date": "20200101", "abstr": "", "name": "", "ts_code": "",
             "ind_name": "占位"},
        ], ["title", "trade_date"])
        from tools.agent_tools import search_reports_by_industry
        result = search_reports_by_industry("不存在的行业", db_path=":memory:")
        assert "未找到" in result


class TestSearchPolicy:
    def test_found(self):
        _setup_table("policy", [
            {"title": "半导体产业支持政策", "puborg": "工信部", "pubtime": "20260501", "ptype": "产业政策"},
        ], ["title", "pubtime"])
        from tools.agent_tools import search_policy
        result = search_policy("半导体", db_path=":memory:")
        assert "半导体" in result
        assert "工信部" in result


class TestMatchHotMoney:
    def test_match(self):
        _setup_table("top_inst", [
            {"ts_code": "000001.SZ", "trade_date": "20260506", "exalter": "华泰深圳",
             "buy": "5000", "sell": "100", "net_buy": "4900"},
        ], ["ts_code", "trade_date", "exalter"])
        _setup_table("hm_list", [
            {"name": "赵老哥", "orgs": "华泰深圳,其他营业部"},
        ], ["name"])
        from tools.agent_tools import match_hot_money
        result = match_hot_money("20260506", db_path=":memory:")
        assert "赵老哥" in result
        assert "买入" in result


@patch("tools.agent_tools.akshare_client")
class TestGetNorthIndividual:
    def test_ok(self, mock_ak):
        mock_ak.get_north_flow_individual.return_value = {
            "status": "ok",
            "data": [
                {"date": "20260505", "shareholding": 100000, "close_amt": 500},
                {"date": "20260504", "shareholding": 99000, "close_amt": 490},
            ],
        }
        from tools.agent_tools import get_north_individual
        result = get_north_individual("000988.SZ")
        assert "持股" in result
        assert "20260505" in result


class TestSearchNews:
    def test_found(self):
        _setup_table("news", [
            {"title": "央行降息", "time": "10:30", "source": "cls"},
            {"title": "美股大涨", "time": "11:00", "source": "jin10"},
        ], ["source"])
        from tools.agent_tools import search_news
        result = search_news("央行", db_path=":memory:")
        assert "央行" in result


@patch("tools.agent_tools.tushare_client")
class TestGetThemeMembers:
    def test_ok(self, mock_ts):
        mock_ts.get_ths_index.return_value = {
            "status": "ok",
            "data": [{"ts_code": "THS001", "name": "CPO概念"}],
        }
        mock_ts.get_ths_member.return_value = {
            "status": "ok",
            "data": [{"code": "002475", "name": "立讯精密"}],
        }
        from tools.agent_tools import get_theme_members
        result = get_theme_members("CPO")
        assert "CPO" in result
        assert "立讯精密" in result


@patch("tools.agent_tools.classify_events.__module__", "tools.agent_tools")
class TestClassifyEvents:
    @patch("sandboxes.data.events_db.classify_events")
    def test_ok(self, mock_classify):
        mock_classify.return_value = [
            {"ann_date": "20260501", "event_type": "业绩预告", "strength": 0.8, "detail": "净利润同比+50%"},
        ]
        from tools.agent_tools import classify_events
        result = classify_events("000001.SZ", days=30)
        assert "业绩预告" in result


class TestSearchAnnouncements:
    def test_found(self):
        _setup_table("announcements", [
            {"ts_code": "002428.SZ", "ann_date": "20260510", "title": "关于公司回购股份的公告", "category": "公司治理"},
            {"ts_code": "002428.SZ", "ann_date": "20260509", "title": "2025年年度报告", "category": "定期报告"},
        ], ["ts_code", "ann_date", "title"])
        from tools.agent_tools import search_announcements
        result = search_announcements("002428.SZ", db_path=":memory:")
        assert "回购" in result
        assert "年度报告" in result

    def test_table_not_exist(self):
        from tools.agent_tools import search_announcements
        duckdb_store._connections.clear()
        result = search_announcements("002428.SZ", db_path=":memory:")
        assert "暂无数据" in result or "无公告" in result


@patch("tools.agent_tools.tushare_client")
class TestFetchStockReports:
    def test_ok(self, mock_ts):
        mock_ts.get_research_report_by_stock.return_value = {
            "status": "ok",
            "data": [
                {"trade_date": "20260510", "inst_csname": "中信证券", "title": "云南锗业深度报告", "abstr": "看好锗材料前景"},
                {"trade_date": "20260508", "inst_csname": "东吴证券", "title": "半导体材料跟踪", "abstr": "化合物半导体持续景气"},
            ],
        }
        from tools.agent_tools import fetch_stock_reports
        result = fetch_stock_reports("002428.SZ")
        assert "中信证券" in result
        assert "云南锗业" in result

    def test_empty(self, mock_ts):
        mock_ts.get_research_report_by_stock.return_value = {"status": "ok", "data": []}
        from tools.agent_tools import fetch_stock_reports
        result = fetch_stock_reports("002428.SZ")
        assert "无个股研报" in result


@patch("tools.agent_tools.akshare_client")
class TestFetchStockNews:
    def test_ok(self, mock_ak):
        mock_ak.get_stock_news_em.return_value = {
            "status": "ok",
            "data": [
                {"新闻标题": "云南锗业拟投资10亿元扩产", "发布时间": "2026-05-10 09:30", "新闻来源": "东方财富"},
                {"新闻标题": "半导体材料板块集体走强", "发布时间": "2026-05-09 14:00", "新闻来源": "东方财富"},
            ],
        }
        from tools.agent_tools import fetch_stock_news
        result = fetch_stock_news("002428.SZ")
        assert "云南锗业" in result
        assert "扩产" in result

    def test_error(self, mock_ak):
        mock_ak.get_stock_news_em.return_value = {"status": "error", "message": "网络错误"}
        from tools.agent_tools import fetch_stock_news
        result = fetch_stock_news("002428.SZ")
        assert "无个股新闻" in result


class TestSearchPolicyContent:
    def test_found(self):
        _setup_table("policy", [
            {"title": "半导体产业支持政策", "puborg": "工信部", "pubtime": "20260501",
             "ptype": "产业政策", "content": "为推动半导体产业高质量发展，现提出以下意见..." * 10},
        ], ["title", "pubtime"])
        from tools.agent_tools import search_policy_content
        result = search_policy_content("半导体", db_path=":memory:")
        assert "半导体" in result
        assert "正文摘要" in result
        assert "工信部" in result

    def test_no_match(self):
        _setup_table("policy", [
            {"title": "占位", "puborg": "", "pubtime": "20200101", "ptype": "", "content": "占位内容"},
        ], ["title", "pubtime"])
        from tools.agent_tools import search_policy_content
        result = search_policy_content("绝对找不到的关键词XYZ", db_path=":memory:")
        assert "未找到" in result


@patch("tools.agent_tools.cninfo_client")
class TestFetchAnnouncementContent:
    def test_ok_via_cninfo(self, mock_cninfo):
        """巨潮 API 返回有 pdf_url 的公告，成功提取正文。"""
        mock_cninfo.query_announcements.return_value = {
            "status": "ok",
            "data": [
                {"title": "关于业绩预告的公告", "ann_date": "20260510",
                 "pdf_url": "http://example.com/test.pdf", "type": "业绩预告"},
            ],
        }
        mock_cninfo.fetch_announcement_text.return_value = (
            "经公司初步测算，预计2025年度实现归母净利润5000万元，同比增长50%。"
            "公司持续加大研发投入，新产品线贡献营收占比显著提升，市场竞争力不断增强。"
        )
        from tools.agent_tools import fetch_announcement_content
        # 用空 DuckDB 确保走巨潮 API 路径
        result = fetch_announcement_content("999999.SZ", "业绩预告", db_path=":memory:")
        assert "归母净利润" in result

    @patch("sandboxes.data.knowledge_store.semantic_search", return_value=[])
    def test_pdf_fail_fallback_to_list(self, mock_search, mock_cninfo):
        """无 pdf_url 且 LanceDB 无数据时，返回公告列表。"""
        mock_cninfo.query_announcements.return_value = {
            "status": "ok",
            "data": [
                {"title": "年度报告", "ann_date": "20260510", "pdf_url": "", "type": "定期报告"},
            ],
        }
        from tools.agent_tools import fetch_announcement_content
        result = fetch_announcement_content("999999.SZ", db_path=":memory:")
        assert "公告列表" in result or "年度报告" in result

    @patch("sandboxes.data.knowledge_store.semantic_search", return_value=[])
    def test_no_match(self, mock_search, mock_cninfo):
        """DuckDB 和巨潮 API 均无数据时，返回"未查到"。"""
        mock_cninfo.query_announcements.return_value = {"status": "ok", "data": []}
        from tools.agent_tools import fetch_announcement_content
        result = fetch_announcement_content("999999.SZ", "不存在的关键词", db_path=":memory:")
        assert "未查到" in result


@patch("tools.agent_tools.search_knowledge.__module__", "tools.agent_tools")
class TestSearchKnowledge:
    @patch("sandboxes.data.knowledge_store.semantic_search")
    def test_ok(self, mock_search):
        mock_search.return_value = [
            {"ts_code": "002428.SZ", "title": "高品质磷化铟单晶片建设项目",
             "text": "拟投资建设高品质磷化铟单晶片产线", "source_type": "announcement",
             "ann_date": "20260401", "score": 0.15},
        ]
        from tools.agent_tools import search_knowledge
        result = search_knowledge("InP 产能 扩产")
        assert "磷化铟" in result
        assert "announcement" in result

    @patch("sandboxes.data.knowledge_store.semantic_search")
    def test_empty(self, mock_search):
        mock_search.return_value = []
        from tools.agent_tools import search_knowledge
        result = search_knowledge("完全找不到的内容")
        assert "未找到" in result

    @patch("sandboxes.data.knowledge_store.semantic_search")
    def test_exception_table_not_found(self, mock_search):
        mock_search.side_effect = Exception("Table knowledge not found")
        from tools.agent_tools import search_knowledge
        result = search_knowledge("任意查询")
        assert "暂无数据" in result

    @patch("sandboxes.data.knowledge_store.semantic_search")
    def test_exception_other(self, mock_search):
        mock_search.side_effect = Exception("网络异常")
        from tools.agent_tools import search_knowledge
        result = search_knowledge("任意查询")
        assert "检索失败" in result
