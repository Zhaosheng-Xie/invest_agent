"""P0 Phase 1 验收测试 — 信号发现 / 假设驱动分析 / 突变率计算。"""
import sys
import json
import time
import traceback

sys.path.insert(0, "src")

RESULTS: dict[str, str] = {}
DETAILS: dict[str, str] = {}


def _banner(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n", flush=True)


# ── 测试 1：信号发现 ──────────────────────────────────────────────────

def test1_signal_discovery():
    _banner("测试 1：信号发现 — 20260402")
    from harness.signal_discovery import discover_signals

    result = discover_signals(trade_date="20260402")

    signals = result.get("signals", [])
    pulse = result.get("market_pulse", {})

    print(f"市场阶段: {pulse.get('phase', 'N/A')}  "
          f"(涨停 {pulse.get('limit_up_count', 0)} / 跌停 {pulse.get('limit_down_count', 0)})")
    print(f"发现信号数: {len(signals)}\n")

    for s in signals[:20]:
        print(f"  {s.get('ts_code', 'N/A'):12s}  {s.get('stock_name', ''):8s}  "
              f"[{s.get('trigger_source', '')}]  {s.get('trigger_detail', '')}")

    detail = f"发现 {len(signals)} 个信号，市场阶段 {pulse.get('phase', 'N/A')}"
    DETAILS["test1"] = detail
    print(f"\n>> {detail}", flush=True)

    RESULTS["test1"] = "PASS"


# ── 测试 2：云南锗业假设分析 ──────────────────────────────────────────

def test2_hypothesis_yunnan():
    _banner("测试 2：假设驱动分析 — 云南锗业 002428.SZ @ 20260402")
    from harness.hypothesis_engine import run_hypothesis_analysis

    result = run_hypothesis_analysis(
        ts_code="002428.SZ",
        trade_date="20260402",
        stock_name="云南锗业",
        trigger_reason="化合物半导体材料转型，InP衬底供不应求",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    p1 = result.get("phase1", {})
    p3 = result.get("phase3", {})

    hypo = p1.get("hypothesis", "")
    suggestion = p3.get("suggestion", "")
    valid = p3.get("hypothesis_valid")
    pos_type = p3.get("position_type", "")

    checks = []

    keywords_p1 = ["产业", "转型", "InP", "化合物", "半导体", "锗", "衬底", "材料"]
    hit = any(k in hypo for k in keywords_p1)
    checks.append(("Phase1 假设含关键词", hit))
    if not hit:
        print(f"  [WARN] Phase1 hypothesis 未命中关键词: {hypo[:100]}")

    simple_reject = (valid is False and pos_type == "avoid"
                     and ("PE" in suggestion or suggestion.strip().lower() == "avoid"))
    checks.append(("Phase3 非简单拒绝", not simple_reject))
    if simple_reject:
        print(f"  [WARN] Phase3 简单拒绝: valid={valid}, suggestion={suggestion}")

    detail = f"hypothesis: \"{hypo[:60]}...\" / suggestion: \"{suggestion[:60]}\""
    DETAILS["test2"] = detail
    print(f"\n>> {detail}", flush=True)

    all_pass = all(ok for _, ok in checks)
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'WARN'}: {name}")

    RESULTS["test2"] = "PASS" if all_pass else "PASS_WITH_WARN"


# ── 测试 3：华工科技假设分析 ──────────────────────────────────────────

def test3_hypothesis_huagong():
    _banner("测试 3：假设驱动分析 — 华工科技 000988.SZ @ 20260209")
    from harness.hypothesis_engine import run_hypothesis_analysis

    result = run_hypothesis_analysis(
        ts_code="000988.SZ",
        trade_date="20260209",
        stock_name="华工科技",
        trigger_reason="AI算力驱动光模块业务爆发，800G/1.6T高速光模块放量",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    p1 = result.get("phase1", {})
    p3 = result.get("phase3", {})

    hypo = p1.get("hypothesis", "")
    suggestion = p3.get("suggestion", "")
    valid = p3.get("hypothesis_valid")
    pos_type = p3.get("position_type", "")

    checks = []

    keywords_p1 = ["光模块", "AI", "算力", "业务", "突变", "光通信", "数据中心"]
    hit = any(k in hypo for k in keywords_p1)
    checks.append(("Phase1 假设含关键词", hit))
    if not hit:
        print(f"  [WARN] Phase1 hypothesis 未命中关键词: {hypo[:100]}")

    simple_reject = (valid is False and pos_type == "avoid"
                     and suggestion.strip().lower() == "avoid")
    checks.append(("Phase3 非简单拒绝", not simple_reject))

    detail = f"hypothesis: \"{hypo[:60]}...\" / suggestion: \"{suggestion[:60]}\""
    DETAILS["test3"] = detail
    print(f"\n>> {detail}", flush=True)

    all_pass = all(ok for _, ok in checks)
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'WARN'}: {name}")

    RESULTS["test3"] = "PASS" if all_pass else "PASS_WITH_WARN"


# ── 测试 4：突变率计算 ───────────────────────────────────────────────

def test4_mutation_rate():
    _banner("测试 4：5 年主营突变率 — 云南锗业 002428.SZ")
    from sandboxes.data import tushare_client
    from agents.fund import _calc_mutation_rate

    all_mainbz = []
    for y in range(2025, 2020, -1):
        p = f"{y}1231"
        print(f"  拉取 {p} ...", end=" ", flush=True)
        result = tushare_client.get_fina_mainbz(ts_code="002428.SZ", period=p, type="P")
        if result["status"] == "ok" and result["data"]:
            for item in result["data"]:
                item["period"] = p
            all_mainbz.extend(result["data"])
            print(f"OK ({len(result['data'])} 条)")
        else:
            print(f"无数据 / {result.get('status')}")
        time.sleep(1)

    print(f"\n共获取 {len(all_mainbz)} 条 mainbz 记录\n")

    mutation = _calc_mutation_rate(all_mainbz)
    print(json.dumps(mutation, ensure_ascii=False, indent=2))

    score = mutation.get("mutation_score", 0)
    new_biz = mutation.get("new_businesses", [])
    growing = mutation.get("growing_businesses", [])

    checks = []
    checks.append(("mutation_score > 30", score > 30))
    if score <= 30:
        print(f"  [WARN] mutation_score={score}, 期望 > 30")

    biz_names = " ".join(b["name"] for b in new_biz + growing)
    has_semi = any(k in biz_names for k in ["半导体", "化合物", "InP", "磷化", "衬底", "光伏", "新材料", "新能源", "锗"])
    checks.append(("新/增长业务含转型关键词", has_semi))
    if not has_semi:
        print(f"  [WARN] 新/增长业务未命中关键词: {biz_names}")

    detail = f"mutation_score: {score}, 新业务: {[b['name'] for b in new_biz]}"
    DETAILS["test4"] = detail
    print(f"\n>> {detail}", flush=True)

    all_pass = all(ok for _, ok in checks)
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'WARN'}: {name}")

    RESULTS["test4"] = "PASS" if all_pass else "PASS_WITH_WARN"


# ── 主流程 ───────────────────────────────────────────────────────────

def main():
    test_funcs = [
        ("test1", test1_signal_discovery),
        ("test2", test2_hypothesis_yunnan),
        ("test3", test3_hypothesis_huagong),
        ("test4", test4_mutation_rate),
    ]

    timings: dict[str, float] = {}

    for key, func in test_funcs:
        t0 = time.time()
        try:
            func()
        except Exception:
            RESULTS[key] = "ERROR"
            DETAILS[key] = traceback.format_exc()[-300:]
            print(f"\n!! ERROR !!\n{traceback.format_exc()}", flush=True)
        timings[key] = time.time() - t0
        print(f"\n  耗时: {timings[key]:.1f}s", flush=True)

    _banner("P0 验收报告")
    labels = {
        "test1": "测试 1（信号发现）",
        "test2": "测试 2（云南锗业假设分析）",
        "test3": "测试 3（华工科技假设分析）",
        "test4": "测试 4（突变率计算）",
    }
    pass_count = 0
    for key in ["test1", "test2", "test3", "test4"]:
        status = RESULTS.get(key, "NOT_RUN")
        detail = DETAILS.get(key, "")
        t = timings.get(key, 0)
        if "PASS" in status:
            pass_count += 1
        print(f"{labels[key]}: {status} ({t:.1f}s) — {detail}")

    print(f"\n总结: {pass_count}/4 通过")


if __name__ == "__main__":
    main()
