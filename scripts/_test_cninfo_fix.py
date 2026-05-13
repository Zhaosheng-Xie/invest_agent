"""验证 cninfo_client 修复后 002428 能查到公告。"""
import sys
sys.path.insert(0, "src")
from sandboxes.data.cninfo_client import query_announcements

r = query_announcements(stock="002428", start_date="20260401", end_date="20260410")
print(f"status={r['status']}, count={len(r['data'])}, total={r['total_count']}")
for d in r["data"][:5]:
    print(f"  [{d['ann_date']}] {d['title'][:60]}")
