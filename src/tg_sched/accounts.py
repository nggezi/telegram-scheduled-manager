# -*- coding: utf-8 -*-
"""多账号管理：账号列表、会话文件路径、增删与选择。

目录约定：
    config/tg_api.txt          共享的 api_id / api_hash
    config/accounts.json       账号名列表，例如 ["main", "work"]
    config/sessions/<name>.session   每个账号一个会话文件

向后兼容：若 accounts.json 不存在但存在旧的 config/tg_scheduled.session，
则自动迁移为名为 "default" 的账号。
"""

import os
import sys
import json
import re

from .config import CONFIG_DIR, SESSION_FILE as LEGACY_SESSION_FILE

ACCOUNTS_FILE = os.path.join(CONFIG_DIR, "accounts.json")
SESSIONS_DIR = os.path.join(CONFIG_DIR, "sessions")

# 账号名允许的字符：字母、数字、下划线、连字符（避免路径穿越）
_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def _ensure_dirs():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def session_path(name):
    """返回某账号的会话文件路径（不含 .session 后缀，Telethon 会自动加）。"""
    return os.path.join(SESSIONS_DIR, name)


def list_accounts():
    """返回账号名列表。首次调用时会自动迁移旧会话。"""
    _ensure_dirs()
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [n for n in data if isinstance(n, str) and _NAME_RE.match(n)]
        except Exception:
            pass
        return []

    # 迁移：旧的单账号会话 -> "default"
    if os.path.exists(LEGACY_SESSION_FILE + ".session"):
        save_accounts(["default"])
        try:
            os.replace(LEGACY_SESSION_FILE + ".session",
                       session_path("default") + ".session")
            print("检测到旧会话，已迁移为账号 'default'。")
        except Exception as e:
            print("（警告：迁移旧会话失败：%s）" % e)
        return ["default"]

    return []


def save_accounts(names):
    """写入账号名列表。"""
    _ensure_dirs()
    names = [n for n in names if _NAME_RE.match(n)]
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(names, f, ensure_ascii=False, indent=2)


def add_account(name):
    """新增账号名（重复则忽略）。返回 True 表示新增成功。"""
    if not _NAME_RE.match(name):
        raise ValueError("账号名只能是字母/数字/下划线/连字符，长度 1~32。")
    names = list_accounts()
    if name in names:
        return False
    names.append(name)
    save_accounts(names)
    return True


def remove_account(name):
    """从列表移除账号，并可删除其会话文件。返回 (是否移除, 会话是否删除)。"""
    names = list_accounts()
    if name not in names:
        return (False, False)
    names.remove(name)
    save_accounts(names)

    deleted = False
    p = session_path(name) + ".session"
    if os.path.exists(p):
        try:
            os.remove(p)
            deleted = True
        except Exception:
            pass
    return (True, deleted)


def choose_account(allow_new=True):
    """
    让用户选择一个账号，返回账号名；无账号或用户选择新建时进入新建流程。
    返回 None 表示取消。
    """
    while True:
        names = list_accounts()
        if names:
            print("\n可用账号：")
            print("-" * 64)
            for i, n in enumerate(names):
                logged = os.path.exists(session_path(n) + ".session")
                mark = "（已登录）" if logged else "（未登录，首次将走登录流程）"
                print("[%3d] %-20s %s" % (i, n, mark))
            if allow_new:
                print("[  n] 新建账号")
            print("-" * 64)

            raw = input("请选择账号编号（回车取消）: ").strip().lower()
            if raw == "":
                return None
            if allow_new and raw == "n":
                new = _ask_new_name()
                if new is None:
                    continue
                return new
            try:
                idx = int(raw)
                if 0 <= idx < len(names):
                    return names[idx]
            except ValueError:
                pass
            print("无效输入，请重新选择。")
        else:
            print("\n还没有任何账号，请先新建一个。")
            new = _ask_new_name()
            if new is None:
                continue
            return new


def _ask_new_name():
    """询问一个新账号名并写入列表。返回名字，或 None 表示放弃。"""
    while True:
        name = input("请输入新账号名（字母/数字/下划线/连字符，回车取消）: ").strip()
        if name == "":
            return None
        if not _NAME_RE.match(name):
            print("格式不对：只能是字母/数字/下划线/连字符，长度 1~32。")
            continue
        if name in list_accounts():
            print("该账号名已存在，请换一个。")
            continue
        add_account(name)
        print("已新建账号 '%s'，首次使用该账号时会要求手机号登录。" % name)
        return name
