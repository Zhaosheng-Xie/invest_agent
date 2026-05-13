"""Step 4: 跑 signal_discovery"""
import sys
import json
sys.path.insert(0, "src")

from harness.signal_discovery import discover_signals

DB = "data/duckdb/market.duckdb"

print("=" * 60)
print("STEP 4: 运行 signal_discovery('20260404')")
print("=" * 60)

result = discover_signals("20260404", db_path=DB)
print(f"Signals: {len(result['signals'])}")
print(f"Market pulse: {result['market_pulse']}")

# 检查 002428 是否被发现
found = [s for s in result["signals"] if "002428" in s.get("ts_code", "")]
if found:
    print(f"\n*** 002428.SZ FOUND! ***")
    for s in found:
        print(f"  source={s['trigger_source']}, priority={s['priority']}")
        print(f"  detail: {s['trigger_detail'][:200]}")
else:
    print("\n002428.SZ NOT found in signals")

# 打印所有信号
print(f"\n全部信号 (共 {len(result['signals'])} 个):")
for i, s in enumerate(result["signals"][:30]):
    print(f"  [{i+1}] {s['ts_code']} {s.get('stock_name','')} | source={s['trigger_source']} | priority={s['priority']}")
    print(f"       {s['trigger_detail'][:120]}")

# 保存信号结果
with open("data/demo_p15_signals_20260404.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n信号结果已保存到 data/demo_p15_signals_20260404.json")
