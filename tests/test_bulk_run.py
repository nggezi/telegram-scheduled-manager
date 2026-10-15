# -*- coding: utf-8 -*-
"""用假 client 端到端跑 bulk.run，验证不崩溃、排期次数正确、格式化正确。

不联网：假 client 的 send_message 只记录调用。
运行： python tests/test_bulk_run.py
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from tg_sched import bulk
from tg_sched.client import list_dialogs as real_list_dialogs


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
        class R:
            messages = []
        return R()


def _fake_list(client):
    async def _inner(c):
        return [FakeDialog("BotA"), FakeDialog("BotB")]
    return _inner


def test_bulk_run_end_to_end():
    orig = bulk.list_dialogs
    bulk.list_dialogs = _fake_list(None)
    patch_input(["0,1", "23:10", "3", "/qd", "yes", "n"])
    client = FakeClient()
    try:
        asyncio.run(bulk.run(client))
    finally:
        bulk.list_dialogs = orig

    assert len(client.sent) == 6, "应为 6 条，实际 %d" % len(client.sent)
    assert all(t == "/qd" for _, t, _ in client.sent)
    peers = [p for p, _, _ in client.sent]
    assert peers.count("BotA") == 3 and peers.count("BotB") == 3


def test_bulk_run_cancel():
    async def fake_list(c):
        return [FakeDialog("BotA")]

    orig = bulk.list_dialogs
    bulk.list_dialogs = fake_list
    patch_input(["0", "23:10", "2", "/qd", "no", ""])
    client = FakeClient()
    try:
        asyncio.run(bulk.run(client))
    finally:
        bulk.list_dialogs = orig
    assert len(client.sent) == 0, "取消后不应发送任何消息"


if __name__ == "__main__":
    for fn in [test_bulk_run_end_to_end, test_bulk_run_cancel]:
        fn()
        print("PASS", fn.__name__)
    print("\n全部通过。")
