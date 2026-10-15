# -*- coding: utf-8 -*-
"""针对交互函数的离线测试：不联网，用 monkeypatch 模拟 input。

运行： python tests/test_interactions.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from tg_sched import ui, bulk
from tg_sched.config import LOCAL_TZ
from datetime import datetime


class FakeInput:
    """按顺序返回预设输入，用完后抛 EOFError。"""
    def __init__(self, answers):
        self.answers = list(answers)

    def __call__(self, prompt=""):
        if not self.answers:
            raise EOFError("no more canned input")
        return self.answers.pop(0)


def run_with_inputs(func, inputs):
    fake = FakeInput(inputs)
    if isinstance(__builtins__, dict):
        __builtins__["input"] = fake
    else:
        __builtins__.input = fake
    try:
        return func()
    finally:
        pass


# ---- ask_time ----

def test_ask_time_valid_and_retry():
    assert run_with_inputs(ui.ask_time, ["abc", "25:00", "23:10"]) == (23, 10)
    assert run_with_inputs(ui.ask_time, ["00:00"]) == (0, 0)
    assert run_with_inputs(ui.ask_time, ["9：05"]) == (9, 5)  # 全角冒号


# ---- ask_days ----

def test_ask_days_bounds():
    assert run_with_inputs(ui.ask_days, ["0", "-3", "abc", "30"]) == 30
    assert run_with_inputs(ui.ask_days, ["9999", "365"]) == 365
    assert run_with_inputs(ui.ask_days, ["1"]) == 1


# ---- choose_chat ----

class FakeDialog:
    def __init__(self, name):
        self.entity = name
        self.id = 1
        self.input_entity = name


def test_choose_chat_cancel_and_select():
    dialogs = [FakeDialog("A"), FakeDialog("B"), FakeDialog("C")]
    assert run_with_inputs(lambda: ui.choose_chat(dialogs), [""]) == []
    got = run_with_inputs(lambda: ui.choose_chat(dialogs), ["0,2"])
    assert [d.entity for d in got] == ["A", "C"]


def test_choose_chat_out_of_range_retries():
    dialogs = [FakeDialog("A")]
    got = run_with_inputs(lambda: ui.choose_chat(dialogs), ["5", "0"])
    assert [d.entity for d in got] == ["A"]


def test_choose_chat_accepts_hint_kwarg():
    dialogs = [FakeDialog("A")]
    assert run_with_inputs(lambda: ui.choose_chat(dialogs, hint="x"), ["0"]) is not None


# ---- ask_yes ----

def test_ask_yes():
    assert run_with_inputs(lambda: ui.ask_yes("?"), ["yes"]) is True
    assert run_with_inputs(lambda: ui.ask_yes("?"), ["YES"]) is True
    assert run_with_inputs(lambda: ui.ask_yes("?"), ["no"]) is False


if __name__ == "__main__":
    fns = [test_ask_time_valid_and_retry, test_ask_days_bounds,
           test_choose_chat_cancel_and_select, test_choose_chat_out_of_range_retries,
           test_choose_chat_accepts_hint_kwarg, test_ask_yes]
    for fn in fns:
        fn()
        print("PASS", fn.__name__)
    print("\n全部通过。")
