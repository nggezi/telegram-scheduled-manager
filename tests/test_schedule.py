# -*- coding: utf-8 -*-
"""简单测试 build_schedule 的时间计算（不联网、不需要账号）。

运行： python tests/test_schedule.py
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bulk_schedule as bs


def test_count_and_spacing():
    plan = bs.build_schedule(23, 10, 30)
    assert len(plan) == 30, "天数应为 30"
    assert all(p.tzinfo is not None for p in plan), "必须带时区"
    for a, b in zip(plan, plan[1:]):
        assert (b - a) == timedelta(days=1), "相邻间隔必须是 1 天"


def test_all_future():
    plan = bs.build_schedule(23, 10, 5)
    now = datetime.now(bs.LOCAL_TZ)
    assert all(p > now for p in plan), "所有排期都必须在未来"


def test_passed_time_rolls_to_tomorrow():
    now = datetime.now(bs.LOCAL_TZ)
    if now.hour == 0 and now.minute == 0:
        return  # 边界时刻跳过，避免干扰
    plan = bs.build_schedule(0, 0, 3)
    first_local = plan[0].astimezone(bs.LOCAL_TZ)
    assert first_local.date() == (now + timedelta(days=1)).date(), "已过的时刻应顺延到明天"


def test_hh_mm_preserved():
    plan = bs.build_schedule(23, 10, 3)
    for p in plan:
        lp = p.astimezone(bs.LOCAL_TZ)
        assert (lp.hour, lp.minute) == (23, 10), "HH:MM 必须保持"


if __name__ == "__main__":
    for fn in [test_count_and_spacing, test_all_future,
               test_passed_time_rolls_to_tomorrow, test_hh_mm_preserved]:
        fn()
        print("PASS", fn.__name__)
    print("\n全部通过。")
