"""云南锗业 002428.SZ 完整分析：预拉取 + 逐步 10 agent 运行（带进度日志）。"""
import sys, io, json, time, os, traceback
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

TS_CODE = "002428.SZ"
STOCK_NAME = "云南锗业"
TRADE_DATE = "20260402"

# ---- Step 1: 预拉取（如果 DuckDB 不存在才拉） ----
print("=" * 60)
print(f"  Step 1: 预拉取 {TRADE_DATE} 全市场数据")
print("=" * 60)
sys.stdout.flush()
t0 = time.time()

db_path = "data/duckdb/market.duckdb"
if os.path.exists(db_path):
    print(f"  DuckDB 已存在，跳过预拉取")
else:
    from harness.daily_data_prep import run_daily_prep
    stats = run_daily_prep(TRADE_DATE)
    for table, count in stats.items():
        print(f"  {table}: {count}")
print(f"  预拉取完成 ({time.time()-t0:.1f}s)")
sys.stdout.flush()

# ---- Step 2: 逐步运行 10 agent ----
from agents.state import MarketState
from agents.macro import macro_node
from agents.fund import fund_node
from agents.tech import tech_node
from agents.event import event_node
from agents.flow_institutional import flow_inst_node
from agents.flow_hot_money import flow_hot_node
from agents.risk import risk_node
from agents.backtest import backtest_node
from agents.critic import critic_node
from agents.supervisor import supervisor_node

AGENT_PIPELINE = [
    ("Macro", "macro_themes", macro_node),
    ("Fundamental", "fundamental_score", fund_node),
    ("Technical", "technical_score", tech_node),
    ("Event", "event_analysis", event_node),
    ("FlowInst", "flow_institutional", flow_inst_node),
    ("FlowHot", "flow_hot_money", flow_hot_node),
    ("Risk", "risk_assessment", risk_node),
    ("Backtest", "backtest_result", backtest_node),
    ("Critic", "critic_review", critic_node),
    ("Supervisor", "supervisor_signal", supervisor_node),
]

state: MarketState = {
    "ts_code": TS_CODE,
    "trade_date": TRADE_DATE,
    "stock_name": STOCK_NAME,
}

print()
print("=" * 60)
print(f"  Step 2: 运行 {STOCK_NAME}({TS_CODE}) 完整 10 agent 分析")
print(f"  日期: {TRADE_DATE}")
print("=" * 60)
sys.stdout.flush()

total_start = time.time()

import signal

class TimeoutError(Exception):
    pass

for i, (name, key, node_fn) in enumerate(AGENT_PIPELINE, 1):
    if i > 1:
        print(f"  (等待 5s 避免频率限制...)", flush=True)
        time.sleep(5)
    print(f"\n[{i}/10] {name} agent 开始...", end="", flush=True)
    t_agent = time.time()
    try:
        result = node_fn(state)
        state.update(result)
        elapsed_agent = time.time() - t_agent
        agent_data = result.get(key, {})
        score = agent_data.get("score", agent_data.get("direction", "N/A"))
        print(f" 完成 ({elapsed_agent:.1f}s) score={score}")
    except Exception as e:
        elapsed_agent = time.time() - t_agent
        print(f" 失败 ({elapsed_agent:.1f}s): {e}")
        traceback.print_exc()
        state[key] = {"score": 0, "summary": f"Error: {e}", "error": str(e)}
    sys.stdout.flush()

total_elapsed = time.time() - total_start

# ---- Step 3: 输出结果 ----
print()
print("=" * 60)
print(f"  分析结果 (总计 {total_elapsed:.1f}s)")
print("=" * 60)

AGENTS = [
    ("宏观主题", "macro_themes"),
    ("基本面", "fundamental_score"),
    ("技术面", "technical_score"),
    ("事件分析", "event_analysis"),
    ("机构资金", "flow_institutional"),
    ("游资动向", "flow_hot_money"),
    ("风险评估", "risk_assessment"),
    ("回测结果", "backtest_result"),
    ("Critic", "critic_review"),
    ("Supervisor", "supervisor_signal"),
]

for name, key in AGENTS:
    agent_out = state.get(key, {})
    print(f"\n--- {name} ({key}) ---")
    if key == "critic_review":
        print(f"  Score: {agent_out.get('score', 'N/A')}")
        print(f"  Verdict: {agent_out.get('verdict', 'N/A')}")
        objections = agent_out.get("objections", [])
        if isinstance(objections, list):
            for j, obj in enumerate(objections[:5], 1):
                print(f"  反对{j}: {str(obj)[:200]}")
        print(f"  Worst Case: {str(agent_out.get('worst_case', ''))[:300]}")
    elif key == "supervisor_signal":
        print(f"  Direction: {agent_out.get('direction', 'N/A')}")
        print(f"  Confidence: {agent_out.get('confidence', 'N/A')}")
        print(f"  Position: {agent_out.get('position_pct', 'N/A')}%")
        print(f"  Stop Loss: {agent_out.get('stop_loss', 'N/A')}")
        print(f"  Reasons: {json.dumps(agent_out.get('reasons', []), ensure_ascii=False)[:400]}")
        print(f"  Summary: {str(agent_out.get('summary', ''))[:500]}")
    else:
        print(f"  Score: {agent_out.get('score', 'N/A')}")
        print(f"  Summary: {str(agent_out.get('summary', ''))[:500]}")
        highlights = agent_out.get("highlights", [])
        risks = agent_out.get("risks", [])
        if highlights:
            print(f"  Highlights: {json.dumps(highlights, ensure_ascii=False)[:300]}")
        if risks:
            print(f"  Risks: {json.dumps(risks, ensure_ascii=False)[:300]}")
        if agent_out.get("data_sources"):
            print(f"  Data sources: {agent_out['data_sources']}")

out_path = f"data/result_{TS_CODE.replace('.', '_')}_{TRADE_DATE}.json"
Path(out_path).parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2, default=str)
print(f"\n完整结果已保存: {out_path}")
