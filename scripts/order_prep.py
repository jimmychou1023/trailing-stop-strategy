#!/usr/bin/env python3
"""移動停損停利策略 — 下單前置計算 (order prep).

依據持倉資料，計算槓桿型 ETF 波段操作的停損 / 停利價位，
邏輯與 index.html 完全一致：

  硬底線   floor  = 成本價 (停損永不低於成本)
  移動停損 stop   = max(最高收盤價 × (1 - 停損幅度), 成本價)
  移動停利 profit = 最高收盤價 × (1 + 停利幅度)

範例:
    python scripts/order_prep.py --et 0.25
    python scripts/order_prep.py --ticker 00631L --shares 1000 \\
        --cost 35.46 --high 41.32 --et 0.15 --pt 0.10
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass


def pct(value: str) -> float:
    """Parse a percentage that may be given as a fraction (0.25) or percent (25).

    Values <= 1 are treated as fractions, values > 1 as whole percents, so both
    ``--et 0.25`` and ``--et 25`` mean 25%.
    """
    v = float(value)
    if v < 0:
        raise argparse.ArgumentTypeError("百分比不可為負數")
    frac = v if v <= 1 else v / 100.0
    if frac > 1:
        raise argparse.ArgumentTypeError("百分比幅度不可超過 100%")
    return frac


@dataclass
class Position:
    ticker: str
    shares: int
    cost: float
    high: float


@dataclass
class Levels:
    floor: float          # 硬底線 = 成本
    stop: float           # 移動停損 (已套用硬底線保護)
    raw_stop: float       # 未套用硬底線前的原始停損
    profit: float         # 移動停利
    floored: bool         # 停損是否被成本價托住


def compute_levels(pos: Position, stop_pct: float, profit_pct: float) -> Levels:
    raw_stop = pos.high * (1 - stop_pct)
    stop = max(raw_stop, pos.cost)
    profit = pos.high * (1 + profit_pct)
    return Levels(
        floor=pos.cost,
        stop=stop,
        raw_stop=raw_stop,
        profit=profit,
        floored=stop > raw_stop,
    )


def pnl(price: float, cost: float, shares: int) -> tuple[float, float]:
    """回傳 (損益金額, 損益百分比)。"""
    amount = (price - cost) * shares
    pct_change = (price - cost) / cost * 100 if cost else 0.0
    return amount, pct_change


def fmt_pnl(price: float, pos: Position) -> str:
    amount, pct_change = pnl(price, pos.cost, pos.shares)
    sign = "+" if amount >= 0 else ""
    return f"{sign}{round(amount):,} ({sign}{pct_change:.1f}%)"


def render(pos: Position, stop_pct: float, profit_pct: float) -> str:
    lv = compute_levels(pos, stop_pct, profit_pct)
    lines: list[str] = []
    lines.append("=" * 44)
    lines.append("  移動停損停利策略 · 下單前置計算")
    lines.append("=" * 44)
    lines.append(f"  股票代號    {pos.ticker}")
    lines.append(f"  持倉股數    {pos.shares:,}")
    lines.append(f"  平均成本    {pos.cost:.2f}")
    lines.append(f"  最高收盤價  {pos.high:.2f}")
    lines.append(f"  停損幅度    {stop_pct * 100:.0f}%")
    lines.append(f"  停利幅度    {profit_pct * 100:.0f}%")
    lines.append("-" * 44)
    lines.append(f"  停損硬底線  {lv.floor:>8.2f}   {fmt_pnl(lv.floor, pos)}")
    floor_note = "  (硬底線托住)" if lv.floored else ""
    lines.append(f"  移動停損線  {lv.stop:>8.2f}   {fmt_pnl(lv.stop, pos)}{floor_note}")
    lines.append(f"  移動停利線  {lv.profit:>8.2f}   {fmt_pnl(lv.profit, pos)}")
    lines.append("-" * 44)
    lines.append("  情境試算 (最高收盤價變動時)")
    lines.append(f"  {'最高收盤':>8} {'停損線':>8} {'停利線':>8}")
    for mult in (1.0, 1.1, 1.2, 1.35):
        h = round(pos.high * mult) if mult != 1.0 else pos.high
        raw_s = h * (1 - stop_pct)
        s = max(raw_s, pos.cost)
        p = h * (1 + profit_pct)
        tag = "  ← 現在" if mult == 1.0 else ""
        lines.append(f"  {h:>8.2f} {s:>8.2f} {p:>8.2f}{tag}")
    lines.append("=" * 44)
    lines.append("  觸及任一條線 → 全數出清，當日執行。")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="計算槓桿 ETF 波段操作的停損 / 停利價位",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--ticker", default="00631L", help="股票代號")
    p.add_argument("--shares", type=int, default=1000, help="持倉股數")
    p.add_argument("--cost", type=float, default=35.46, help="每股平均成本")
    p.add_argument("--high", type=float, default=41.32, help="持有以來最高收盤價")
    p.add_argument(
        "--et",
        "--stop",
        dest="stop_pct",
        type=pct,
        default=0.15,
        help="停損幅度 (exit trailing)，從最高收盤價回落多少出場；接受 0.25 或 25",
    )
    p.add_argument(
        "--pt",
        "--profit",
        dest="profit_pct",
        type=pct,
        default=0.10,
        help="停利幅度，從最高收盤價上漲多少出場；接受 0.10 或 10",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cost <= 0 or args.high <= 0:
        raise SystemExit("成本與最高收盤價必須大於 0")
    if args.shares <= 0:
        raise SystemExit("持倉股數必須大於 0")
    pos = Position(
        ticker=args.ticker.strip() or "—",
        shares=args.shares,
        cost=args.cost,
        high=args.high,
    )
    print(render(pos, args.stop_pct, args.profit_pct))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
