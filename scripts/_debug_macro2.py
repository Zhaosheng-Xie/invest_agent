"""Debug: 测量 macro_node user_message 的数据量和 LLM 调用时间。"""
import sys, io, time, json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

TRADE_DATE = "20260402"

print("=== _fetch_data ===", flush=True)
t0 = time.time()
from agents.macro import _fetch_data, _load_prompt
data = _fetch_data(TRADE_DATE)
print(f"  time={time.time()-t0:.1f}s")
for k, v in data.items():
    if isinstance(v, list):
        print(f"  {k}: {len(v)} items")
    else:
        print(f"  {k}: {type(v)}")
sys.stdout.flush()

user_message = (
    f"请分析截至 {TRADE_DATE} 的宏观主题格局。\n\n"
    f"以下是数据：\n{json.dumps(data, ensure_ascii=False, default=str)}"
)
msg_len = len(user_message)
print(f"\n  user_message 长度: {msg_len} 字符 (~{msg_len//2} tokens)")
sys.stdout.flush()

print("\n=== call_kimi (macro 完整请求) ===", flush=True)
t0 = time.time()
from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config

system_prompt = _load_prompt()
tier = get_tier_config("macro")
print(f"  tier config: {tier}")

from tools.agent_tools import TOOL_SEARCH_POLICY, TOOL_SEARCH_NEWS, TOOL_GET_THEME
tools = [TOOL_SEARCH_POLICY, TOOL_SEARCH_NEWS, TOOL_GET_THEME]

try:
    response = call_kimi(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        tools=tools,
        tool_choice="auto",
        **tier,
    )
    elapsed = time.time() - t0
    content = response.get("content", "")
    tool_calls = response.get("tool_calls")
    print(f"  time={elapsed:.1f}s")
    print(f"  has_content={bool(content)}, len={len(content or '')}")
    print(f"  has_tool_calls={bool(tool_calls)}")
    if tool_calls:
        for tc in tool_calls:
            fn = tc.function.name if hasattr(tc, "function") else "?"
            print(f"    tool: {fn}")
    if content:
        print(f"  content[:300]: {content[:300]}")
except Exception as e:
    print(f"  FAIL ({time.time()-t0:.1f}s): {e}")
    import traceback
    traceback.print_exc()
sys.stdout.flush()

print("\nDone.")
