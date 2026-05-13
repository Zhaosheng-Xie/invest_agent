"""数据回填脚本 — 对指定日期范围调用 daily_data_prep 回填 DuckDB。

用法:
    python scripts/backfill_data.py --start 20260326 --end 20260402
    python scripts/backfill_data.py --start 20260203 --end 20260209
"""
from __future__ import annotations

import argparse
import sys
import time

sys.path.insert(0, "src")

from sandboxes.data import tushare_client
from harness.daily_data_prep import run_daily_prep


def _get_trade_dates(start: str, end: str, retries: int = 3) -> list[str]:
    """通过 tushare trade_cal 获取日期范围内的交易日列表。"""
    for attempt in range(retries):
        try:
            pro = tushare_client._get_pro()
            df = pro.trade_cal(
                exchange="SSE", start_date=start, end_date=end, is_open="1"
            )
            dates = sorted(df["cal_date"].tolist())
            return dates
        except Exception as e:
            print(f"  trade_cal 第 {attempt+1} 次失败: {e}", flush=True)
            if attempt < retries - 1:
                time.sleep(10)
    raise RuntimeError("trade_cal 多次重试失败")


def main():
    parser = argparse.ArgumentParser(description="回填 DuckDB 历史数据")
    parser.add_argument("--start", required=True, help="起始日期 YYYYMMDD")
    parser.add_argument("--end", required=True, help="结束日期 YYYYMMDD")
    parser.add_argument("--sleep", type=int, default=5, help="每天之间 sleep 秒数")
    args = parser.parse_args()

    print(f"获取 {args.start} ~ {args.end} 交易日历...", flush=True)
    trade_dates = _get_trade_dates(args.start, args.end)
    print(f"共 {len(trade_dates)} 个交易日: {trade_dates}\n", flush=True)

    for i, td in enumerate(trade_dates):
        print(f"[{i+1}/{len(trade_dates)}] 回填 {td} ...", flush=True)
        try:
            stats = run_daily_prep(td)
            print(f"  完成: {stats}", flush=True)
        except Exception as e:
            print(f"  失败: {e}", flush=True)

        if i < len(trade_dates) - 1:
            print(f"  sleep {args.sleep}s ...", flush=True)
            time.sleep(args.sleep)

    print("\n回填完成。", flush=True)


if __name__ == "__main__":
    main()
