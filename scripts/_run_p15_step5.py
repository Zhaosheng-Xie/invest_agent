"""Step 5: 跑 hypothesis_engine 完整四阶段分析"""
import sys
import json
sys.path.insert(0, "src")

print("=" * 60)
print("STEP 5: 运行 hypothesis_engine (002428.SZ, 20260404)")
print("=" * 60)

from harness.hypothesis_engine import run_hypothesis_analysis

result = run_hypothesis_analysis(
    ts_code="002428.SZ",
    trade_date="20260404",
    stock_name="云南锗业",
    trigger_reason="重大公告: 关于实施高品质磷化铟单晶片建设项目的公告; InP衬底产能扩产计划"
)

# 保存结果
with open("data/demo_p15_yunnan_002428_20260404.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)

print("Saved to data/demo_p15_yunnan_002428_20260404.json")
print(f"\n--- Phase 1 ---")
print(f"hypothesis: {result.get('phase1', {}).get('hypothesis', 'N/A')[:200]}")
print(f"questions: {result.get('phase1', {}).get('questions', [])}")
print(f"stock_type: {result.get('phase1', {}).get('stock_type', 'N/A')}")
print(f"phase1_data_keys: {result.get('phase1_data_keys', [])}")

print(f"\n--- Phase 2 ---")
p2 = result.get('phase2', {})
print(f"tool_calls_made: {len(p2.get('tool_calls_made', []))}")
for tc in p2.get('tool_calls_made', []):
    print(f"  - {tc.get('name', '?')}({json.dumps(tc.get('args', {}), ensure_ascii=False)[:80]})")
verifications = p2.get('verifications', [])
for v in verifications:
    print(f"  Q: {v.get('question', '')[:80]}")
    print(f"    verdict={v.get('verdict')}, evidence={str(v.get('evidence',''))[:100]}")

print(f"\n--- Phase 3 ---")
p3 = result.get('phase3', {})
print(f"hypothesis_valid: {p3.get('hypothesis_valid')}")
print(f"confidence: {p3.get('confidence')}")
print(f"position_type: {p3.get('position_type')}")
print(f"suggestion: {str(p3.get('suggestion', ''))[:200]}")
print(f"evidence_for: {p3.get('evidence_for', [])}")
print(f"evidence_against: {p3.get('evidence_against', [])}")

print(f"\n--- Phase 4 (Critic) ---")
print(f"critic_recommendation: {result.get('critic_recommendation', 'N/A')}")
print(f"adjusted_confidence: {result.get('adjusted_confidence', 'N/A')}")
critic = result.get('critic', {})
print(f"hypothesis_survives: {critic.get('hypothesis_survives')}")
challenges = critic.get('challenges', [])
for c in challenges:
    print(f"  [{c.get('dimension')}] severity={c.get('severity')}: {str(c.get('challenge',''))[:80]}")

print(f"\n--- Data Sources ---")
print(f"data_sources: {result.get('data_sources', [])}")

# 检查错误
for key in ['phase1_error', 'phase2_error', 'phase3_error', 'critic_error', 'phase1_data_error']:
    if key in result:
        print(f"\n!!! {key}: {result[key]}")
