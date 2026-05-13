# 经验沉淀

每次子 agent 遇到的坑和解决方案记录在此。后续子 agent 启动前必读。

格式：`### YYYY-MM-DD 问题简述` + 正文描述问题和解决方案。

---

### 2026-05-02 pip install -e . 需要先执行才能跑测试

Phase 0a 子 agent 创建完代码后，首次运行 pytest 报 `ModuleNotFoundError: No module named 'tenacity'`。原因是 pyproject.toml 声明了依赖但没有执行 `pip install -e ".[dev]"`。后续每次 Phase 新增依赖后，必须重新执行安装。

### 2026-05-02 PowerShell 不支持 bash 语法

Windows 环境下 PowerShell 不支持 `mkdir -p`、`&&` 等 bash 语法。目录创建用 `New-Item -ItemType Directory -Force`，命令串联用 `;` 而不是 `&&`。

### 2026-05-02 控制台中文编码

PowerShell 输出中文会乱码（GBK vs UTF-8），但不影响实际功能。如果需要看中文输出，用 `python script.py` 重定向到文件再读。

### 2026-05-02 pytest 找不到 src 下的包

**问题**：`pyproject.toml` 通过 `[tool.setuptools.package-dir] "" = "src"` 把 src 作为包根，但 `pytest` 直接运行时无法 import `vault` 等包，报 `ModuleNotFoundError`。

**解决**：在 `[tool.pytest.ini_options]` 中添加 `pythonpath = ["src"]`，让 pytest 自动把 src 加入 `sys.path`。

### 2026-05-02 python-decouple 需要显式安装

**问题**：`pyproject.toml` 声明了 `python-decouple` 依赖，但如果没做 `pip install -e .`，直接 `python -m pytest` 会因缺少 decouple 失败。

**解决**：确保运行测试前已 `pip install python-decouple`（或 `pip install -e .[dev]`）。

### 2026-05-02 router 路由表不能用模块级静态函数引用

**问题**：`router.py` 如果在模块加载时用 `_ROUTES = {"get_daily": tushare_client.get_daily}` 保存函数引用，测试中 `patch("sandboxes.data.tushare_client.get_daily")` 无法影响已存入字典的引用，导致 mock 失效。

**解决**：路由表只存字符串名称，`execute()` 中用 `getattr(tushare_client, api_name)` 动态获取，这样 patch 模块属性就能生效。

### 2026-05-02 PowerShell 不支持 && 连接符

**问题**：Windows PowerShell（非 pwsh 7+）不支持 `&&` 连接命令，会报 `InvalidEndOfLine` 错误。

**解决**：用分号 `;` 分隔命令，或升级到 PowerShell 7+。

### 2026-05-02 tenacity 需要显式安装

**问题**：`pyproject.toml` 声明了 `tenacity` 依赖，但如果没做 `pip install -e .`，直接跑 pytest 会因缺少 tenacity 失败。

**解决**：确保 `pip install tenacity`（或 `pip install -e .`）。与 python-decouple 同理，所有 pyproject.toml 中声明的运行时依赖在首次环境搭建时都需要安装。

### 2026-05-02 PowerShell 不支持 && 连接符

**问题**：在 PowerShell 中使用 `cd xxx && python -m pytest` 会报 `InvalidEndOfLine` 错误。

**解决**：在 PowerShell 中用分号 `;` 分隔命令，或者使用 Shell 工具的 `working_directory` 参数指定工作目录。

### 2026-05-02 akshare 财联社快讯接口名变更

**问题**：任务文档中指定的 `ak.stock_zh_a_alerts_cls()` 在当前版本 akshare 中不存在，运行时报 `AttributeError`。

**解决**：用 `dir(ak)` 搜索发现正确接口名为 `ak.stock_info_global_cls()`（对应财联社电报 https://www.cls.cn/telegraph）。akshare 接口名会随版本变化，使用前应先通过 `dir()` 或 `help()` 确认实际可用的函数名。

### 2026-05-02 批量扩展 tushare_client 遵循模板复制模式

**经验**：扩展 tushare_client.py 时，12 个新函数严格复制 get_income 的模式（@retry 装饰器 + _get_pro() 在 try 外 + 统一返回格式），无需发明新抽象。测试同样复制已有 test 的 mock 模式（autouse fixture 重置 _pro + patch get_credential + patch ts.pro_api）。保持模式一致性比 DRY 更重要——后续维护者能一眼看懂每个函数。

### 2026-05-02 DuckDB SQL 列名不能用单引号

**问题**：在 DuckDB 的 INSERT 语句中，列名用 Python `repr()` 生成的单引号 `'col_name'` 会报 `ParserException`，DuckDB 要求标识符用双引号 `"col_name"`。

**解决**：列名引用统一用 `f'"{col}"'` 格式化，不要用 `repr()` 或 `!r`。

### 2026-05-02 akshare 返回的 DataFrame 列名是中文

**问题**：`ak.stock_zh_a_alerts_cls()` 返回的列名是 `['标题', '内容', '发布日期', '发布时间']`，不是英文。DuckDB upsert 时 key_columns 必须匹配实际列名，否则报 BinderException。

**解决**：在入库前检查实际列名，或统一做列名映射。Phase 0b 暂时用中文列名作为 key。

### 2026-05-02 akshare 无金十快讯专用接口

**问题**：任务要求用 `ak.js_news` 获取金十快讯，但当前版本 akshare 中不存在该接口。`dir(ak)` 中 `js_` 前缀的函数只有 `crypto_js_spot`、`stock_js_weibo_nlp_time`、`stock_js_weibo_report`、`stock_zyjs_ths`，均非金十快讯。

**解决**：`get_jin10_news` 函数内部用 `hasattr(ak, "js_news")` 做防御检查，不存在时 fallback 到 `ak.stock_info_global_sina()`（新浪全球快讯，列名为 `时间/内容`）。如果后续 akshare 版本新增金十接口，代码会自动优先使用。

### 2026-05-02 多源新闻聚合需做字段映射

**问题**：CLS 财联社返回列名 `['标题', '内容', '发布日期', '发布时间']`，Sina 新浪返回列名 `['时间', '内容']`，列名不同且均为中文。直接合并会导致字段不一致。

**解决**：在 `news_aggregator.py` 中为每个源定义映射字典（如 `_CLS_FIELD_MAP`、`_SINA_FIELD_MAP`），统一映射到英文字段 `title/content/time/date/source`。缺失字段（如 Sina 无 title）从 content 截取前 60 字符填充。

### 2026-05-02 tushare get_npr 只传非空参数

**问题**：`pro.npr()` 如果传空字符串参数（如 `org=""`），tushare 可能按空字符串过滤导致结果为空。

**解决**：在 `get_npr` 内用条件判断，只把非空参数放入 kwargs 字典再 `**kwargs` 展开传给 API，而不是把所有参数都传过去。这个模式适用于所有可选参数的 tushare 接口。

### 2026-05-02 DuckDB :memory: 连接池需清理

**问题**：`duckdb_store` 使用 `_connections` 字典缓存连接。测试用 `:memory:` 时，如果不在 fixture 中清理 `_connections`，后续测试可能拿到已被关闭或已有数据的连接，导致测试不隔离。

**解决**：在 `autouse` fixture 的 yield 后执行 `duckdb_store._connections.clear()`，确保每个测试用例使用全新的内存数据库。

### 2026-05-02 StrReplace 追加代码时必须匹配文件真正的末尾

**问题**：`tushare_client.py` 在其他 Phase 子 agent 并行扩展后，文件末尾比当前 agent 首次读取时更长（多了 Research Report / Policy Agent 部分）。用 StrReplace 匹配旧末尾位置追加代码，结果代码被插到了中间而非真正的文件末尾，导致 `import` 时找不到新函数。

**解决**：追加代码前，重新 Read 文件确认实际末尾内容，用文件真正最后一段代码作为 `old_string` 来做 StrReplace。

### 2026-05-02 Batch API 测试用 monkeypatch 替换模块常量

**问题**：`kimi_batch.py` 用模块级 `_BATCH_DIR` 控制 JSONL 存储路径，测试中需要写临时目录。

**解决**：用 `monkeypatch.setattr(_mod, "_BATCH_DIR", tmp_path / "batch_jobs")` 替换路径常量，比 mock Path 更简洁且覆盖真实文件 I/O。同样适用于 `_MAX_LINES` 等数值常量的边界测试。

### 2026-05-02 Session events 测试需清理 duckdb_store._connections

**问题**：`session/events.py` 通过 `_get_conn(":memory:")` 获取 DuckDB 内存连接。测试 fixture 只清理了 `_INITIALIZED` 字典，但 `duckdb_store._connections` 中缓存的 `:memory:` 连接未清理，导致多个测试共享同一内存数据库，`test_get_events_filter` 因前序测试残留数据而失败（期望 1 条 llm_call 事件，实际拿到 2 条）。

**解决**：在 `autouse` fixture 的 setup 和 teardown 中同时执行 `duckdb_store._connections.pop(":memory:", None)`，确保每个测试用例拿到独立的内存数据库连接。这与之前 DuckDB `:memory:` 连接池清理的经验一致。

### 2026-05-02 Langfuse 可观测性接入需要模块级状态重置

**问题**：`langfuse_client.py` 使用模块级全局变量 `_langfuse` 和 `_disabled` 做懒加载和降级标记。测试之间如果不重置这两个变量，前一个测试的降级状态会污染后续测试。

**解决**：在 `autouse` fixture 的 setup 和 teardown 中显式重置 `mod._langfuse = None` 和 `mod._disabled = False`。这是模块级单例/缓存的通用测试模式。

### 2026-05-02 langfuse 4.x SDK 安装会带入 opentelemetry 依赖树

**经验**：`pip install langfuse` (v4.5.1) 会额外安装 `opentelemetry-api/sdk/exporter-otlp-proto-http`、`protobuf`、`googleapis-common-protos`、`wrapt`、`backoff` 等依赖。如果项目有 protobuf 版本冲突需注意。目前无冲突。

### 2026-05-02 DuckDB ORDER BY ts 在快速连续插入时排序不稳定

**问题**：`time.time()` 精度有限，极快连续调用 `emit_event` 时多条记录的 `ts` 值相同，导致 `ORDER BY ts DESC LIMIT 1` 返回不确定的行。`wake` 函数的 `last_event_type` / `last_agent` 因此不可靠。

**解决**：在 ORDER BY 中加 `rowid DESC` 作为 tiebreaker：`ORDER BY ts DESC, rowid DESC LIMIT 1`。DuckDB 的 `rowid` 按插入顺序递增，保证相同 `ts` 时仍能取到最后插入的行。

### 2026-05-02 Fundamental Agent mock 模式：patch 模块而非函数引用

**经验**：`fund.py` 中用 `tushare_client.get_income(...)` 而非 `from sandboxes.data.tushare_client import get_income` 直接导入函数。这样测试中 `@patch("agents.fund.tushare_client")` 可以一次 mock 整个模块，所有 `getattr(mock_ts, "get_xxx")` 自动生效。如果改为导入具体函数，则需要逐个 `@patch("agents.fund.get_income")`，更繁琐且容易遗漏。这与 learnings 中 "router 路由表不能用模块级静态函数引用" 的经验一脉相承。

### 2026-05-02 Critic Agent JSON 解析需强制覆盖 verdict

**问题**：LLM 返回的 JSON 中 `verdict` 字段可能与 `score` 不一致（例如 score=35 但 LLM 写了 verdict="pass"）。

**解决**：解析 JSON 后，根据 `score >= 60` 强制重算 `verdict`，不信任 LLM 自行判断的 verdict 值。这是 GAN 模式下的防御性编程——Critic 的通过/拒绝阈值必须由代码控制，不能让 LLM 自由发挥。

### 2026-05-02 LangGraph StateGraph + TypedDict 兼容性良好

**经验**：LangGraph 的 `StateGraph` 可以直接接受 `TypedDict(total=False)` 作为 state schema，无需额外适配。`graph.compile()` 返回可执行图，`graph.invoke(initial_state)` 传入初始状态后返回完整的最终状态（含所有节点写入的 key）。Phase 1a 最简编排 `fund -> critic -> END` 只需 5 行核心代码。测试时 mock 各节点的外部依赖（tushare_client、call_kimi）即可，不需要 mock LangGraph 本身。

### 2026-05-02 Batch Agent 创建严格复制 fund.py 模式

**经验**：创建 Macro/Tech/Event 三个 agent 时，严格复制 `fund.py` 的代码结构（_PROMPT_PATH + _load_prompt + _fetch_data + xxx_node）效率最高。区别仅在于：(1) Macro agent 不需要 ts_code 参数，只需 trade_date；(2) 多数据源 agent（如 Macro）同时 import tushare_client 和 akshare_client；(3) 测试中对多模块 mock 用 `@patch` 叠加装饰器，注意参数顺序与装饰器顺序相反。

### 2026-05-02 Batch 2 Agent（Flow/Risk/Backtest）同样复制 fund.py 模式

**经验**：第二批 4 个 agent（flow_institutional、flow_hot_money、risk、backtest）严格复制相同模式，零障碍一次通过。关键区别：(1) flow_institutional 的 `_fetch_data` 中 `get_moneyflow_hsgt` 不需要 ts_code，只传 start_date/end_date；(2) risk agent 调三个接口（pledge_stat + stk_holdertrade + share_float），fallback 中需包含 position_suggestion 默认值避免下游 KeyError；(3) backtest agent 用 trade_date 减 600 天覆盖约 120 个交易日，比精确计算交易日历更简洁。

### 2026-05-03 Sprint Contract 复用 handoff.py 的文件 I/O 模式

**经验**：`sprint_contract.py` 的 `generate_contract` / `load_contract` 完全复用 `handoff.py` 的 `save_handoff` / `load_handoff` 模式——Pydantic model + `model_dump_json` 写入 + `json.loads` 读回 + `contract_dir` 可注入参数（测试用 `tmp_path`）。LLM 返回 JSON 解析用 `content.index("{")` / `content.rindex("}")` 提取 JSON 子串，失败时降级到默认值。这个"提取 JSON + 降级 fallback"的模式可复用到后续所有需要 LLM 输出结构化数据的场景。

### 2026-05-03 slice_data 缺失字段默认行为需显式排除

**问题**：`slice_data` 用 `r.get(date_field, "")` 时，缺少 date_field 的记录会得到空字符串 `""`，而 `"" <= "20250510"` 为 True，导致缺失日期的记录被保留——这是 look-ahead 漏洞。

**解决**：改用 `r.get(date_field) is not None` 前置检查，None 时直接排除。`slice_financial` 同理。凡是做时间截断的过滤器，都必须把缺失字段视为"不可信数据"丢弃而非保留。

### 2026-05-03 safe_run_node 降级模式无需 mock LangGraph

**经验**：`fallback.py` 的 `safe_run_node` 是纯函数包装器（接收 node_func + state + fallback_key），与 LangGraph 编排解耦。测试时直接传入普通函数即可，无需 mock StateGraph 或 compile。pass^k 测试中 mock `tools.pass_k.run_analysis`（即 mock 导入处）而非 `harness.orchestrator.run_analysis`（定义处），符合 "patch where it's looked up" 原则。

### 2026-05-03 Dashboard 聚合查询复用 session events 的 :memory: 连接

**经验**：`dashboard.py` 的 `generate_daily_report` 直接通过 `_get_conn(db_path)` 访问 DuckDB，与 `session/events.py` 共享连接池。测试中先用 `emit_event(..., db_path=":memory:")` 写入数据，再用 `generate_daily_report(..., db_path=":memory:")` 读取，两者通过 `_connections` 字典拿到同一个内存连接，无需额外 setup。清理 fixture 同时清 `_connections` 和 `_INITIALIZED`。

### 2026-05-03 浮点精度断言用 pytest.approx

**问题**：`(0.8 + 0.6 + 0.7 + 0.5) / 4` 在 Python 中不严格等于 `0.65`（浮点精度），导致 `assert result == expected` 失败。

**解决**：用 `pytest.approx(0.65, abs=1e-9)` 做近似比较。所有涉及浮点运算的断言都应使用 `pytest.approx`。

### 2026-05-05 SQLite :memory: 每次 connect 产生独立数据库

**问题**：与 DuckDB 不同，`sqlite3.connect(":memory:")` 每次调用都会创建一个全新的独立内存数据库。如果多个函数各自调 `_get_conn(":memory:")`，它们拿到的是不同数据库，跨函数写入/读取无法共享数据，导致测试中 `get_portfolio` 读不到 `update_portfolio` 写入的数据。

**解决**：测试中改用 `tmp_path / "test.sqlite"` 临时文件作为 `db_path`，pytest 的 `tmp_path` fixture 自动清理。这比实现连接缓存更简单，且与生产环境（文件型 SQLite）行为一致。

### 2026-05-05 pnl_report.py 模块级 import 需要在测试中提前 mock

**问题**：`pnl_report.py` 有 `from sandboxes.data import tushare_client`，虽然函数体内未使用，但模块加载时会触发 tushare_client 的初始化链。测试中若不 mock，会因缺少 `.env` 中的 tushare token 而失败。

**解决**：在 `test_pnl_report.py` 中用 `with patch("tools.pnl_report.tushare_client"):` 包裹 import 语句，在模块加载前拦截。这种 "patch-before-import" 模式适用于所有带副作用模块级 import 的测试场景。

### 2026-05-05 daily_runner 中 mock 外部调用的正确位置

**经验**：`daily_runner.py` 导入了 `run_analysis`、`emit_event`、`write_note` 等多个外部函数。测试中 patch 的目标是 `harness.daily_runner.run_analysis`（导入处）而非 `harness.orchestrator.run_analysis`（定义处）。所有 7 个外部依赖全部 patch 后测试秒过，无需真实数据库或 API。

### 2026-05-06 V2-A 批量扩展 tushare_client 第三批 13 个接口

**经验**：第三批扩展（moneyflow_ind_ths/cnt_ths、fina_mainbz、stk_holdernumber、forecast_vip、express_vip、limit_list_d、margin/margin_detail、hsgt_top10、top10_holders、moneyflow、index_daily）继续严格复制已有模式，一次通过。可选参数函数用 kwargs 构造 + 只传非空值的模式已成标准做法。测试中为可选参数函数额外写一个 `_no_optional_success` 用例，验证不传可选参数时 kwargs 中不含该 key。

### 2026-05-06 V2-A Task 1-5 增强 5 个 Agent 数据接入

**经验**：批量增强 agent 的 `_fetch_data` 时，所有新增数据调用必须用 `try/except` 包裹（即使 tushare_client 本身已有错误处理），因为 agent 层面任一数据源失败不应影响其他数据源。`_fetch_data` 需要 state 参数时（如过滤研报需要 stock_name），添加 `state: dict | None = None` 可选参数，保持向后兼容。flow_institutional 新增 akshare_client import 后，测试需要在 `@patch` 装饰器中额外 mock akshare_client，且注意装饰器参数顺序（与函数参数顺序相反）。所有新增 mock 返回 `{"status": "ok", "data": [{"test": 1}]}` 即可满足测试。

### 2026-05-07 str(int(trade_date) - N) 日期计算是跨月 bug

**问题**：8 个 agent 文件中用 `str(int(trade_date) - 100)` 做日期回溯，当 trade_date 为 `"20260101"` 时得到 `"20260001"`（不存在的日期），跨月/跨年场景全部出错。

**解决**：统一用 `datetime.strptime + timedelta` 做日期运算。在各 `_fetch_data` 内定义本地 `_subtract_days` 辅助函数，避免修改模块级 API。涉及文件：event.py / fund.py / flow_institutional.py / macro.py / tech.py / backtest.py / risk.py（共 8 处替换）。

### 2026-05-07 DuckDB :memory: 在同一 pytest session 中跨测试类共享

**经验**：`duckdb_store._connections` 缓存 `:memory:` 连接。多个测试类（如 TestSearchReports 和 TestMatchHotMoney）在同一 session 中通过 `_setup_table` 写入 `:memory:`，它们实际共享同一个内存数据库。这反而有利于 agent_tools 测试：可以在不同类中累积表数据。但 `autouse` fixture 在 yield 后 `.clear()` 确保下次运行时干净。

### 2026-05-07 tool_executor 测试中 tool_calls 用 dict 而非 OpenAI 对象

**经验**：`tool_executor.py` 通过 `hasattr(tc, "function")` 同时兼容 OpenAI SDK 返回的对象和 dict 两种形式。测试中直接用 dict 构造 mock tool_calls（`{"id": "tc_1", "function": {"name": "...", "arguments": "..."}}`），比构造 MagicMock 模拟 OpenAI 对象更简洁。`run_agent_with_tools` 会走 `tc.get("function", {}).get("name", "")` 的 dict 分支。

### 2026-05-08 Agent 改造从 call_kimi 到 run_agent_with_tools 的标准模式

**经验**：5 个 agent（fund/event/macro/flow_institutional/flow_hot_money）从直接调 `call_kimi` 改为通过 `run_agent_with_tools` 间接调用，改造步骤完全一致：(1) 替换 import：去掉 `from llm_clients.kimi_sync import call_kimi`，加 `from tools.agent_tools import TOOL_XXX, func_xxx` + `from tools.tool_executor import run_agent_with_tools`；(2) `_fetch_data` 完全不动；(3) `xxx_node` 中把 `call_kimi(messages=[...], **tier)` 替换为 `run_agent_with_tools(system_prompt=, user_message=, tools=, tool_functions=, tier_config=, max_rounds=3)`，返回值从 `response["content"]` 取即可。测试中 mock 目标从 `agents.xxx.call_kimi` 改为 `agents.xxx.run_agent_with_tools`，返回值格式从 `{"content":..., "tool_calls":None, "usage":MagicMock()}` 改为 `{"content":..., "reasoning_content":None, "tool_calls_made":[]}`。test_orchestrator.py 中需额外注意 @patch 装饰器顺序与函数参数顺序相反。

### 2026-05-12 fund.py 多年 fina_mainbz + 业务结构突变率

**经验**：`_fetch_data` 从取 1 期改为循环取 5 期年报的 `fina_mainbz`，需要注意：(1) 每次调用间加 `time.sleep(0.5)` 防 tushare 限流；(2) 测试中必须 mock `time.sleep`（`@patch("agents.fund.time.sleep")`），否则测试耗时 2.5s+；(3) 已有测试的 `@patch` 装饰器栈需要同步增加 `time.sleep` mock，且注意参数顺序与装饰器顺序相反；(4) `_calc_mutation_rate` 中 `bz_item` 名称跨年份可能不一致（如"光伏组件销售"vs"光伏组件及配件"），用前 4 字符做模糊匹配 key 是简单有效的策略；(5) `mutation_score` 计算公式为 `新增业务数×20 + 占比变化>10pct 业务数×15 + 最大单业务占比变化×1`，cap 到 100。

### 2026-05-12 tests/harness/ 子目录不能有 __init__.py

**问题**：`tests/harness/__init__.py` 会创建一个名为 `harness` 的包，与 `src/harness/`（通过 `pythonpath = ["src"]` 加入路径）冲突。pytest 解析 `from harness.signal_discovery import ...` 时优先找到 `tests/harness/` 包，报 `ModuleNotFoundError`。`@patch("harness.signal_discovery.tushare_client")` 也因同一原因失败。

**解决**：删除 `tests/harness/__init__.py`。pytest 不需要 `__init__.py` 就能发现子目录中的测试文件（`testpaths = ["tests"]` 会递归收集）。通用规则：当 `tests/` 子目录名与 `src/` 下的包同名时，测试子目录**不能有 `__init__.py`**。

### 2026-05-12 signal_discovery 信号发现 pipeline 开发模式

**经验**：`signal_discovery.py` 的 5 信号源 + 1 市场温度函数的开发模式：(1) 每个信号源独立 `try/except` 包裹，单个失败不影响整体；(2) 涉及 tushare API 调用（如 get_ths_member）的地方必须 `time.sleep(1)` 防限流；(3) DuckDB 中所有值被 upsert 统一转成 VARCHAR，SQL 比较数值时用 `CAST("col" AS DOUBLE)`；(4) 合并去重逻辑用 ts_code 做 key，空 ts_code（如 news_cluster）不参与合并；(5) 测试中直接用 `:memory:` DuckDB + `upsert` 写入测试数据，比 mock query 更真实；(6) `@patch("harness.signal_discovery.tushare_client")` mock 整个模块而非单个函数。

### 2026-05-12 tests/harness/ 下的测试 mock 须用 patch.object 而非字符串路径

**问题**：`tests/harness/` 目录有 `__init__.py` 使其成为 Python package，与 `src/harness/` 命名冲突。pytest 解析 `patch("harness.hypothesis_engine.xxx")` 时会优先找到 `tests/harness/`（因为 pytest rootdir 在 sys.path 中），导致 `AttributeError: module 'harness' has no attribute 'hypothesis_engine'`。

**解决**：在测试中先 `import harness.hypothesis_engine as mod`（此时 pytest 的 pythonpath 已生效，能正确找到 src 下的模块），然后用 `patch.object(mod, "tushare_client")` 代替 `patch("harness.hypothesis_engine.tushare_client")`。`patch.object` 绕过了字符串路径解析，直接操作已导入的模块对象，不受命名冲突影响。

### 2026-05-12 hypothesis_engine 三阶段分析架构经验

**经验**：假设驱动分析引擎的三阶段设计要点：(1) Phase 1 数据拉取要轻量（只取 fina_indicator 最新 1 期 + daily_basic 最新 1 条 + 板块信息），板块查询 API 调用成本高（每个板块需查成分股），应限制查询数量（max 200 板块 x get_ths_member）；(2) Phase 2 直接复用 `run_agent_with_tools` + `ALL_TOOLS`，LLM 自主决定调哪些 tool；(3) Phase 3 是纯 LLM 判断不需要 tools；(4) 每个 phase 都有独立 fallback（JSON 解析失败时返回安全默认值），且 Phase 1 失败会 short-circuit 直接返回 avoid，Phase 2 失败仍会继续执行 Phase 3（用空验证结果）；(5) tier_router 中 hypothesis_judge 用 B_thinking（需要深度推理），其余用 B_recall；(6) `_extract_json` 用 `index("{")` / `rindex("}")` 提取 JSON 子串是项目通用模式。

### 2026-05-12 fina_mainbz 必须传 type="P" 过滤产品分类

**问题**：tushare `fina_mainbz` 接口不传 `type` 参数时返回所有分类维度的数据，包括按产品（P）、按地区（D）和按渠道的混合结果。`bz_item` 中出现"直销""经销""国内""境外"等渠道/地区名称，`_calc_mutation_rate` 会将其误判为新业务。

**解决**：(1) `tushare_client.get_fina_mainbz` 新增 `type` 可选参数，默认空串（向后兼容）；(2) `fund.py` 的 `_fetch_data` 调用时传 `type="P"` 只获取产品分类；(3) `_calc_mutation_rate` 入口处用 `_NON_PRODUCT_KEYWORDS` 黑名单做二次防御，过滤明显的渠道/地区条目（直销、经销、国内、境外、华东等）。双重保险，即使 API 层面过滤不完整也能兜底。

### 2026-05-12 DuckDB 历史数据回填需用 trade_cal 判断交易日

**问题**：`daily_data_prep.run_daily_prep(trade_date)` 只处理单个日期，回填历史数据时需要知道日期范围内哪些是交易日（非交易日调用会浪费 API 配额且无数据返回）。

**解决**：创建 `scripts/backfill_data.py`，通过 tushare `trade_cal` 接口获取交易日列表，逐日调用 `run_daily_prep`，每天间隔 sleep 5 秒防限流。回填 7 天数据约需 5-8 分钟。tushare API 有时会超时，`_get_trade_dates` 需加重试逻辑。

### 2026-05-12 DuckDB 表不存在时 query 抛异常的防御模式

**问题**：`signal_discovery._scan_news_cluster` 和 `agent_tools.search_news` 查询 `news` 表，但如果 akshare 快讯数据从未写入过，表不存在，`duckdb_store.query` 会抛 `CatalogException`。

**解决**：这两个函数已有 try/except 包裹，异常被捕获后返回空结果或友好错误提示。关键经验：所有查询 DuckDB 共享表（research_report、news、policy 等）的代码都必须用 try/except 包裹，因为表是否存在取决于 daily_data_prep 是否运行过。`agent_tools.search_news` 额外判断异常消息中是否含"does not exist"来返回更有针对性的提示。

### 2026-05-12 行业研报搜索需用 ind_name 字段而非标题匹配

**问题**：`fund.py` 用 `ts_code[:6] in title` 做研报匹配，行业研报标题通常不含股票代码（如"光通信行业深度"不会匹配到 002428），导致大量相关行业研报被遗漏。

**解决**：新增 `search_reports_by_industry` 工具，双维度查询 DuckDB `research_report` 表：(1) 按 `ind_name LIKE '%行业%'` 搜行业研报；(2) 按 ts_code 前 6 位匹配 `ts_code/name/title` 搜个股研报。两者合并按 title 去重。测试中必须先创建表（`_setup_table`）后再查询，否则表不存在会走异常分支。

### 2026-05-12 评级关键词匹配顺序：长词在前短词在后

**问题**：`_extract_rating` 用关键词列表顺序匹配评级，"谨慎推荐"应映射到"增持"，但如果"推荐"排在"谨慎推荐"前面，会先命中"推荐"→"买入"。同理"强烈推荐"必须排在"推荐"前面。

**解决**：匹配列表按从具体到笼统排序：强烈推荐 → 买入 → 谨慎推荐 → 推荐 → 增持 → ...。通用规则：关键词匹配时，长词/特殊词排前面，短词/通用词排后面，避免子串误匹配。

### 2026-05-12 卖方一致预期 consensus 独立于 agent 作为数据层工具

**经验**：`build_consensus` 放在 `tools/consensus.py` 而非 agent 内部，原因：(1) hypothesis_engine 的 `_fetch_phase1_data` 直接调用它作为数据输入，不需要 LLM 参与；(2) 未来其他 agent（如 fund_node）也可复用；(3) 独立模块便于单元测试（直接用 DuckDB `:memory:` + upsert 注入数据）。consensus 结果作为 Phase 1 数据的一部分传给 LLM，让 LLM 在形成假设时就能参考卖方观点。

### 2026-05-12 产业链映射 MVP 用 hardcode 字典 + fina_mainbz 关键词匹配

**经验**：`industry_map.py` 的 MVP 实现要点：(1) tushare 没有"给定个股查所属板块"的直接接口，最简 MVP 是 hardcode `_INDUSTRY_CHAIN_MAP` 字典（关键词→产业链位置），从 `fina_mainbz` 的 `bz_item` 提取关键词做匹配；(2) 可选增强：在 DuckDB 中建 `ths_index_cache` + `ths_member_cache` 表做反查（由 daily_data_prep 预计算），但表可能不存在，必须 try/except；(3) `find_related_stocks` 查 DuckDB 的 `ths_index_cache` 找包含关键词的板块，再通过 `get_ths_member` 获取成分股，每次 API 调用间 `time.sleep(1)` 防限流；(4) 测试中 mock `time.sleep` 避免实际等待，mock `tushare_client` 整个模块；(5) `tests/sandboxes/data/` 子目录不能有 `__init__.py`（与 `src/sandboxes/` 同名冲突）。

### 2026-05-12 Hypothesis Critic 逻辑审查模式替代分数审查

**经验**：将 Critic 从"分数审查"（0-100分 + reject/pass）改为"逻辑审查"（4维度挑战 + hypothesis_survives），关键设计决策：(1) 新建 `hypothesis_critic.py` 与原 `critic.py` 并存，不修改旧流程，避免回归风险；(2) JSON 解析失败时 fallback 为 `hypothesis_survives=True, recommendation="watch"`（保守通过），而非旧模式的 `verdict="reject"`——这是核心行为变更，解决了 11/11 全 reject 的问题；(3) LLM 可能在 `challenges` 中标记 `severity="critical"` 但忘记填 `fatal_flaws`，代码需自动从 critical challenges 中提取并填充 `fatal_flaws`，同时强制 `recommendation="avoid"` 和 `hypothesis_survives=False`；(4) Critic 用 Tier A（thinking 开 + max_tokens=32768），因为逻辑审查需要深度推理；(5) 在 `hypothesis_engine.py` 中作为 Phase 4 接入，失败时 fallback 保留 Phase 3 的原始 confidence 和 position_type，不影响整体流程；(6) 端到端测试中 mock `hypothesis_critic_node` 而非增加 `call_kimi` 的 side_effect 次数，保持测试简洁。

### 2026-05-12 个股级新闻检索下沉到 hypothesis_engine

**经验**：`news_search.py` 从 DuckDB news 表按关键词检索与个股相关的行业快讯，关键设计决策：(1) 关键词三来源：`_extract_stock_name_keywords` 从股票名称拆分（去地名前缀/通用后缀，如"云南锗业"→"锗业"）、`extract_mainbz_keywords` 从 fina_mainbz 的 bz_item 提取（自动拆分长名称如"化合物半导体材料"→子串）、以及外部传入的 mainbz_keywords；(2) `timedelta(days=N)` 当 N 过大（如 999999）会 `OverflowError`，需 `min(days, 3650)` 做 cap，测试中避免使用极端天数；(3) news 表不存在时 DuckDB query 抛异常，在每个关键词循环内 try/except 静默跳过——这比在最外层 catch 更好，因为表可能中途被创建；(4) 跨关键词去重用 `seen_titles` set，同一新闻可能被多个关键词命中；(5) 在 `hypothesis_engine._fetch_phase1_data` 中接入时，增加 `stock_name` 参数（默认空串，向后兼容），调 `get_fina_mainbz(type="P")` 取关键词后调 `search_news_for_stock`，新闻数据写入 `data["related_news"]`；(6) 同时在 `agent_tools.py` 注册 `search_news_for_stock_tool` 供 Phase 2 LLM tool calling 用，tool 入口将 mainbz_keywords 从逗号分隔字符串转 list；(7) 测试中需要同时 mock `search_news_for_stock` 和 `extract_mainbz_keywords`（用 `patch.object(mod, ...)`），否则测试会实际查 DuckDB。

### 2026-05-12 DuckDB 参数化查询 query_safe 防 SQL 注入

**问题**：所有 DuckDB 查询都用 f-string 拼接用户可控值（ts_code、keyword、industry 等），`.replace("'", "")` 不够安全，存在 SQL 注入风险。同时 `search_news` 用 `SELECT * LIMIT N` + 内存过滤，当 news 表数据量大时大部分匹配丢失。

**解决**：(1) 在 `duckdb_store.py` 新增 `query_safe(sql, params, db_path)` 函数，使用 DuckDB 原生参数化（`$1, $2, ...` 占位符），与旧 `query()` 并存保持向后兼容；(2) 5 个文件（consensus.py、news_search.py、agent_tools.py、industry_map.py、signal_discovery.py）中共 15+ 处 f-string SQL 全部改为 `query_safe` + `$N` 参数；(3) LIKE 模式的 `%` 在参数值中拼好（如 `[f"%{keyword}%"]`），不在 SQL 中拼；(4) `search_news` 从 `SELECT * LIMIT N` + 内存过滤改为 `WHERE title LIKE $1 ORDER BY time DESC LIMIT $2`，由数据库引擎做过滤；(5) 修复过程中发现 3 个测试（TestSearchReports、TestSearchPolicy、TestMatchHotMoney）的测试数据列名/表名与实际 SQL 不匹配（之前靠 `:memory:` 共享连接凑巧通过），一并修正了测试数据；(6) 新增 `tests/sandboxes/data/test_duckdb_store.py` 覆盖 query_safe 的基本查询、参数化等值/LIKE、多参数、写操作拒绝、SQL 注入防御等场景。

### 2026-05-13 signal_discovery 新增"重大公告"信号源

**经验**：新增 `_scan_major_announcements` 作为第 6 个信号源，查 DuckDB `announcements` 表按分类 + 标题关键词识别重大公告。关键设计决策：(1) announcements 表可能不存在（新建数据库），`query_safe` 调用放在 try/except 中，异常时返回空列表；(2) 同一股票多条重大公告在函数内部用 `seen_codes` dict 合并（拼接 trigger_detail），避免向 `_merge_signals` 传入大量重复 ts_code；(3) ts_code 6 位码标准化：0/3 开头 → `.SZ`，6 开头 → `.SH`，其余默认 `.SZ`；(4) 关键词列表 15 个 + 高价值分类 3 个，分类优先于关键词匹配（category 命中则不再查关键词）；(5) 测试直接用 `:memory:` DuckDB + `upsert` 写入 announcements 表，与现有 5 个信号源的测试模式一致，无需额外 mock。

### 2026-05-13 P1.5 Task 2 — 5 个实时数据工具 + Phase 1 公告注入

**经验**：批量新增 5 个 tool（search_announcements / fetch_stock_reports / fetch_stock_news / search_policy_content / fetch_announcement_content）的关键模式：(1) DuckDB 查询工具（search_announcements、search_policy_content）必须在 except 中判断 `"does not exist" in str(e)` 来区分"表不存在"和"其他错误"，返回更友好的提示；(2) 实时 API 工具（fetch_stock_reports、fetch_stock_news）不依赖 DuckDB 预入库，直接调 tushare/akshare 客户端，测试中用 `@patch("tools.agent_tools.tushare_client")` mock 整个模块；(3) akshare `stock_news_em` 返回中文列名（新闻标题/发布时间/新闻来源），代码中用 `r.get("新闻标题", r.get("title", ...))` 做双语兼容；(4) cninfo_client.py 简化版用 requests + pdfplumber，`fetch_announcement_text` 在 pdfplumber 未安装时返回 error 而非抛异常；(5) hypothesis_engine Phase 1 注入公告数据时，`query_safe` 需要局部 import（`from sandboxes.data.duckdb_store import query_safe`）因为 hypothesis_engine 不在模块顶层 import duckdb_store；(6) 所有 5 个新工具严格遵循"函数实现 + TOOL schema + ALL_TOOLS 注册 + TOOL_FUNCTIONS 注册"四步走模式，与现有工具结构一致。

### 2026-05-13 P1.5 Task 1 — 公告全量入库 + 政策正文入库

**经验**：(1) `cninfo_client.py` 已有旧版本（简化版，只支持 `stock` + `search_key` 参数），覆盖时必须清除 `__pycache__`，否则 Python 会加载旧的 `.pyc` 缓存，导致新函数签名不生效；(2) 新版 `query_announcements` 改为全参数（stock/start_date/end_date/category/page_num/page_size），日期格式自动转换（`20260401` → `2026-04-01`），用 `~` 拼接 seDate 参数；(3) `extract_text_from_pdf` 使用延迟 `import pdfplumber`，测试中不能用 `@patch("module.pdfplumber", create=True)` mock——延迟 import 走的是 `sys.modules` 而非模块属性，正确做法是 `patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber})`；(4) tenacity `@retry` 装饰后的函数如果内部 try/except 全捕获了（不 reraise），异常不会触发 retry，测试中直接调用即可（不需要 `.retry.call()`）；(5) `get_npr` 升级加 `fields` 参数时保持向后兼容——默认值为空串，为空时填入含 `content_html` 的完整字段列表；(6) `daily_data_prep.py` 中处理 `content_html` → 纯文本用 `re.sub(r'<[^>]+>', '', html)` + 截断到 10000 字符防止单条过大；(7) pyproject.toml 需新增 `pdfplumber` 依赖。

### 2026-05-13 P1.5 Task 3+4 — LanceDB 语义知识库 + search_knowledge 工具

**经验**：(1) `lancedb` + `sentence-transformers` 安装会带入 `torch`（~115MB wheel on Windows）、`transformers`、`pyarrow`、`scipy`、`scikit-learn` 等大量依赖，首次安装耗时较长（2-3分钟），后续项目 CI 需预缓存；(2) `knowledge_store.py` 的 `_model` 模块级缓存避免了重复加载 SentenceTransformer 模型（~90MB），但测试中必须在 `autouse` fixture 里重置 `mod._model = None`，否则测试间 mock 状态泄漏；(3) LanceDB `table.search(vector).where(filter)` 的 filter 语法类似 SQL 但不支持参数化占位符，目前用 f-string 拼接——仅用于内部 ts_code/source_type 过滤，不直接暴露给用户输入；(4) `daily_data_prep.py` 步骤 10 依赖步骤 9 的 `anns` 变量，必须在步骤 9 的 `try` 块外预初始化 `anns = []`，否则步骤 9 异常时步骤 10 会 `NameError`；(5) 测试 `knowledge_store` 时用 `numpy.random.rand` 生成 mock embedding（384维），比 mock `encode` 返回固定向量更真实；(6) `search_knowledge` 工具的异常处理区分"Table not found"（知识库暂无数据）和其他异常（检索失败），给 LLM 更有针对性的错误提示；(7) `_chunk_text` 的 overlap 参数确保语义连续性，测试中验证了 `result[0][-overlap:] == result[1][:overlap]` 的重叠正确性。

### 2026-05-13 P1.5 验收 — 跨模块接口一致性是最大风险

**问题**：P1.5 开发跨 5 个子任务（Task 1-4 + 2b），由不同子 agent 独立完成。验收时发现 3 个 Critical 级接口不匹配：(1) `agent_tools.fetch_announcement_content` 调用 `cninfo_client.query_announcements` 传了不存在的 `search_key` 参数（`query_announcements` 的参数是 `stock/start_date/end_date/category/page_num/page_size`）；(2) 同一函数期望 `fetch_announcement_text` 返回 `{"status": "ok", "text": "..."}` 字典，但实际返回纯 `str`；(3) LanceDB `where` 子句中 `source_type` 参数来自 LLM tool calling 输入，用 f-string 拼接存在注入风险。

**解决**：(1) 去掉 `search_key` 参数，改为先拉全量再在代码中按 `title_keyword` 过滤；(2) 改为直接检查返回字符串的 `len(text) > 50`；(3) 对 `source_type` 做白名单校验（只允许 announcement/report/policy），`ts_code` 做字符清理。

**教训**：多子 agent 并行开发时，**函数签名和返回值类型是最容易出错的接缝**。每个子 agent 完成后应立即做 mock 集成测试验证调用链，而非等全部完成再验收。

### 2026-05-13 P1.5 验收 — cninfo_client retry 装饰器与内层 try/except 冲突

**问题**：`cninfo_client.query_announcements` 有 `@retry(stop=stop_after_attempt(3))` 装饰器，但内层 `try/except Exception` 捕获了所有异常并返回 error dict，异常不会 re-raise，导致 retry 永远不触发。

**解决**：将网络请求部分的异常分两层处理——网络类异常（`IOError/ConnectionError/TimeoutError/RequestException`）re-raise 让 retry 生效，其他异常（如 JSON 解析）在内层捕获返回 error dict。这是项目通用的 "retry + try/except" 模式。

### 2026-05-13 P1.5 验收 — 测试文件同名冲突

**问题**：`tests/test_duckdb_store.py`（旧）和 `tests/sandboxes/data/test_duckdb_store.py`（P1.5 新增）同名但在不同目录。pytest 收集时报 `import file mismatch`，因为两者都会被 import 为 `test_duckdb_store` 模块。

**解决**：将旧文件重命名为 `test_duckdb_store_basic.py`。通用规则：跨目录的测试文件名不能重复，否则 pytest 无法区分模块。新增测试文件前应先 `find tests/ -name "test_xxx.py"` 检查是否已有同名。

### 2026-05-13 P1.5 验收 — daily_data_prep 测试需要 mock 延迟 import

**问题**：`daily_data_prep.py` 步骤 9-10 使用 `from sandboxes.data.cninfo_client import query_all_announcements` 和 `from sandboxes.data.knowledge_store import ingest_announcement` 的延迟 import。测试中 `@patch("harness.daily_data_prep.tushare_client")` 无法拦截这些延迟 import，导致测试尝试真实调用巨潮 API。

**解决**：在测试的 `@patch` 装饰器栈中添加 `@patch("sandboxes.data.cninfo_client.query_all_announcements", return_value=[])` 和 `@patch("sandboxes.data.cninfo_client.fetch_announcement_text", return_value="")` 和 `@patch("sandboxes.data.knowledge_store.ingest_announcement", return_value=1)`，直接 patch 源模块而非延迟 import 的目标位置。

### 2026-05-13 Phase 2 JSON 解析失败的三层防御

**问题**：`run_agent_with_tools` 多轮 tool calling 后，LLM 最终返回的 content 常包含 markdown code fence（` ```json ... ``` `）、分析文字或不规范 JSON，导致 `_extract_json` 用 `text.index("{")` / `text.rindex("}")` 提取失败。Phase 2 的 9 次工具调用成功获取了投资 18,856 万元、年产 45 万片 InP 等关键数据，但全部丢失——3/3 verifications 均变成 inconclusive。

**解决**：三层防御策略：
1. **增强 `_extract_json`**：依次尝试 (a) 提取 ` ```json ... ``` ` code fence 内容；(b) 最外层 `{ ... }` 匹配；(c) 逐字符配对大括号找含关键 key（verifications/hypothesis/confidence）的最大合法 JSON 块。
2. **Phase 2 fallback**：JSON 解析失败但有 tool_calls_made 时，调 LLM 做一次"总结+结构化"，将原始 content + tool 证据转成 verifications JSON。结构化也失败时，构建包含 `raw_tool_evidence` 的默认结果。
3. **Phase 3 注入**：当所有 verifications 为 inconclusive 或存在 `raw_tool_evidence` 时，将 tool_calls_made 的结果作为补充证据追加到 Phase 3 的 user_message 中，确保 LLM 判断时能看到原始工具返回的数据。

**效果**：v2 跑通后 Phase 2 tool_calls 从 9 次增至 11 次，第一个问题 verdict 从 inconclusive 变为 partially_supported（含投资 18,856 万元、年产 45 万片、IRR 49.51%等具体数据），Phase 3 confidence 从 0.35 提升到 0.5，position_type 从 avoid 变为 watch。

### 2026-05-13 Phase 2 prompt 需列出全部可用工具

**问题**：`hypothesis_phase2.md` 只列了 7 个基础工具（search_reports, search_news 等），但实际 `ALL_TOOLS` 有 17 个工具。LLM 不知道有 search_knowledge、fetch_announcement_content、search_reports_by_industry 等更强大的工具可用，倾向于只调基础工具，数据深度不够。

**解决**：在 prompt 中列出全部 17 个工具并标注优先级。search_knowledge 排第一（语义检索公告正文最有深度）、fetch_announcement_content 排前列（可获取完整公告 PDF）。使用策略也更新为优先语义检索。

### 2026-05-13 DuckDB `_ensure_table` 需要 schema migration

**问题**：`get_npr` 新增了 `content_html`、`url` 字段（7 列），但 DuckDB `policy` 表之前只建了 5 列。`CREATE TABLE IF NOT EXISTS` 不会修改已有表结构，`upsert` 的 `INSERT INTO qt SELECT * FROM qtmp` 当 temp 表比目标表多列时会失败。

**解决**：(1) `_ensure_table` 新增 schema migration：`DESCRIBE` 获取现有列名，对比新列定义，缺失的用 `ALTER TABLE ADD COLUMN` 补上；(2) `upsert` 的 `INSERT INTO qt SELECT * FROM qtmp` 改为显式列名 `INSERT INTO qt (col1, col2) SELECT col1, col2 FROM qtmp`，避免列数不匹配。

### 2026-05-13 fetch_announcement_content 三级 fallback

**问题**：手动插入 DuckDB 的公告缺少 `pdf_url`，导致 `fetch_announcement_content` 无法下载 PDF。原实现只查巨潮 API，如果巨潮也查不到就返回"未查到"，但 LanceDB 中已有公告正文。

**解决**：三级 fallback：(1) 先查 DuckDB announcements 表找 pdf_url；(2) DuckDB 没有则查巨潮 API；(3) 两者都无 pdf_url 时，fallback 到 LanceDB 语义搜索 `semantic_search(query, ts_code, source_type="announcement")`。v2 验证中 4 次 `fetch_announcement_content` 调用有 3 次走了 LanceDB fallback 路径，成功返回了公告正文关键段落。

**注意**：测试中需要 mock `semantic_search` 防止真实调用 LanceDB，并使用 `db_path=":memory:"` 隔离 DuckDB 查询。
