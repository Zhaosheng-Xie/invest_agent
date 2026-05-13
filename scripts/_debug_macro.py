"""Debug: 逐步测试 macro_node 的哪个阶段卡住。"""
import sys, io, time, json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

TRADE_DATE = "20260402"

print("=== Test 1: akshare get_cls_news ===", flush=True)
t0 = time.time()
try:
    from sandboxes.data.akshare_client import get_cls_news
    r = get_cls_news(count=10)
    print(f"  status={r['status']}, rows={len(r.get('data', []))}, time={time.time()-t0:.1f}s")
except Exception as e:
    print(f"  FAIL ({time.time()-t0:.1f}s): {e}")
sys.stdout.flush()

print("\n=== Test 2: akshare get_jin10_news ===", flush=True)
t0 = time.time()
try:
    from sandboxes.data.akshare_client import get_jin10_news
    r = get_jin10_news(count=10)
    print(f"  status={r['status']}, rows={len(r.get('data', []))}, time={time.time()-t0:.1f}s")
except Exception as e:
    print(f"  FAIL ({time.time()-t0:.1f}s): {e}")
sys.stdout.flush()

print("\n=== Test 3: tushare get_ths_index ===", flush=True)
t0 = time.time()
try:
    from sandboxes.data.tushare_client import get_ths_index
    r = get_ths_index()
    print(f"  status={r['status']}, rows={len(r.get('data', []))}, time={time.time()-t0:.1f}s")
except Exception as e:
    print(f"  FAIL ({time.time()-t0:.1f}s): {e}")
sys.stdout.flush()

print("\n=== Test 4: macro _fetch_data ===", flush=True)
t0 = time.time()
try:
    from agents.macro import _fetch_data
    data = _fetch_data(TRADE_DATE)
    print(f"  keys={list(data.keys())}, time={time.time()-t0:.1f}s")
except Exception as e:
    print(f"  FAIL ({time.time()-t0:.1f}s): {e}")
sys.stdout.flush()

print("\n=== Test 5: simple call_kimi ===", flush=True)
t0 = time.time()
try:
    from llm_clients.kimi_sync import call_kimi
    r = call_kimi("你好，请回复'测试成功'三个字。", max_tokens=64)
    print(f"  content={r['content'][:100]}, time={time.time()-t0:.1f}s")
except Exception as e:
    print(f"  FAIL ({time.time()-t0:.1f}s): {e}")
sys.stdout.flush()

print("\nDone.")
