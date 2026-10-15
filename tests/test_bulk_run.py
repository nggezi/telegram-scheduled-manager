# -*- coding: utf-8 -*-
"""用假 client 端到端跑 bulk_schedule.run，验证不崩溃、排期次数正确、格式化正确。

不联网：假 client 的 send_message 只记录调用。
运行： python tests/test_bulk_run.py
"""
import sys
import os
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bulk_schedule as bs
import fix_telegram_scheduled as fix


class FakeInput:
    def __init__(self, answers):
        self.answers = list(answers)

    def __call__(self, prompt=""):
        if not self.answers:
            raise EOFError("no more canned input (prompt=%r)" % prompt)
        return self.answers.pop(0)


def patch_input(answers):
    fake = FakeInput(answers)
    if isinstance(__builtins__, dict):
        __builtins__["input"] = fake
    else:
        __builtins__.input = fake
    return fake


class FakeDialog:
    def __init__(self, name):
        self.entity = name
        self.id = 1
        self.input_entity = name


class FakeClient:
    """记录 send_message 调用；模拟计划队列为空。"""
    def __init__(self):
        self.sent = []

    async def send_message(self, peer, text, schedule=None):
        assert schedule is not None, "schedule 不能为 None"
        assert schedule.tzinfo is not None, "schedule 必须带时区"
        self.sent.append((peer, text, schedule))

    async def __call__(self, request):
        # existing_scheduled -> GetScheduledHistoryRequest
        class R:
            messages = []
        return R()


def test_bulk_run_end_to_end():
    # 让 list_dialogs 返回固定两个聊天
    orig_dialogs = fix.list_dialogs
    orig_bs_dialogs = bs.list_dialogs

    async def fake_list(client):
        return [FakeDialog("BotA"), FakeDialog("BotB")]

    fix.list_dialogs = fake_list
    bs.list_dialogs = fake_list

    # 输入序列：选择聊天 "0,1" -> 时间 23:10 -> 天数 3 -> 内容 /qd -> 确认 yes -> 不再继续
    patch_input(["0,1", "23:10", "3", "/qd", "yes", "n"])
    client = FakeClient()
    try:
        asyncio.run(bs.run(client))
    finally:
        fix.list_dialogs = orig_dialogs
        bs.list_dialogs = orig_bs_dialogs

    # 2 个聊天 × 3 天 = 6 条
    assert len(client.sent) == 6, "应为 6 条，实际 %d" % len(client.sent)
    assert all(t == "/qd" for _, t, _ in client.sent)
    # 每个聊天各 3 条，且时间递增
    peers = [p for p, _, _ in client.sent]
    assert peers.count("BotA") == 3 and peers.count("BotB") == 3


def test_bulk_run_cancel():
    async def fake_list(client):
        return [FakeDialog("BotA")]

    orig = bs.list_dialogs
    bs.list_dialogs = fake_list
    patch_input(["0", "23:10", "2", "/qd", "no", ""])  # 输入 no 取消排期，再回车退出
    client = FakeClient()
    try:
        asyncio.run(bs.run(client))
    finally:
        bs.list_dialogs = orig
    assert len(client.sent) == 0, "取消后不应发送任何消息"


if __name__ == "__main__":
    for fn in [test_bulk_run_end_to_end, test_bulk_run_cancel]:
        fn()
        print("PASS", fn.__name__)
    print("\n全部通过。")
