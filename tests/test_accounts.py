# -*- coding: utf-8 -*-
"""多账号管理测试：账号名校验、增删、会话路径、选择流程。不联网。

会临时把 config 目录指到临时目录，避免污染真实配置。
运行： python tests/test_accounts.py
"""
import sys
import os
import json
import shutil
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))

# 用临时目录替换 config，隔离真实数据
tmp = tempfile.mkdtemp(prefix="tgsched_test_")
import tg_sched.accounts as accounts
accounts.CONFIG_DIR = tmp
accounts.ACCOUNTS_FILE = os.path.join(tmp, "accounts.json")
accounts.SESSIONS_DIR = os.path.join(tmp, "sessions")
accounts.LEGACY_SESSION_FILE = os.path.join(tmp, "tg_scheduled")


class FakeInput:
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
    return func()


def test_name_validation():
    for bad in ["", "a/b", "a b", "a.b", "x" * 33, "中文"]:
        try:
            accounts.add_account(bad)
            assert False, "应拒绝非法账号名: %r" % bad
        except ValueError:
            pass
    assert accounts.add_account("main") is True
    assert accounts.add_account("work-1") is True
    assert accounts.add_account("_ok_123") is True


def test_add_duplicate_and_list():
    names = accounts.list_accounts()
    assert "main" in names and "work-1" in names
    assert accounts.add_account("main") is False  # 重复


def test_session_path():
    p = accounts.session_path("main")
    assert p.endswith("main")
    assert "sessions" in p


def test_remove_account():
    accounts.add_account("todelete")
    removed, _ = accounts.remove_account("todelete")
    assert removed is True
    assert "todelete" not in accounts.list_accounts()
    # 删除不存在的
    removed2, _ = accounts.remove_account("nonexistent")
    assert removed2 is False


def test_remove_deletes_session_file():
    accounts.add_account("withsess")
    # 伪造一个会话文件
    os.makedirs(accounts.SESSIONS_DIR, exist_ok=True)
    sp = accounts.session_path("withsess") + ".session"
    with open(sp, "w") as f:
        f.write("x")
    removed, deleted = accounts.remove_account("withsess")
    assert removed and deleted
    assert not os.path.exists(sp)


def test_choose_account_select_existing():
    # 选择 "main"（此时列表含 main / work-1 / _ok_123）
    names = accounts.list_accounts()
    idx = names.index("main")
    got = run_with_inputs(accounts.choose_account, [str(idx)])
    assert got == "main"


def test_choose_account_cancel():
    got = run_with_inputs(accounts.choose_account, [""])
    assert got is None


def test_choose_account_new_inline():
    # 选 n -> 输入新名
    got = run_with_inputs(accounts.choose_account, ["n", "brand_new"])
    assert got == "brand_new"
    assert "brand_new" in accounts.list_accounts()


def test_choose_account_retries_bad_index():
    got = run_with_inputs(accounts.choose_account, ["999", "0"])
    assert got == accounts.list_accounts()[0]


def teardown():
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    fns = [test_name_validation, test_add_duplicate_and_list, test_session_path,
           test_remove_account, test_remove_deletes_session_file,
           test_choose_account_select_existing, test_choose_account_cancel,
           test_choose_account_new_inline, test_choose_account_retries_bad_index]
    try:
        for fn in fns:
            fn()
            print("PASS", fn.__name__)
        print("\n全部通过。")
    finally:
        teardown()
