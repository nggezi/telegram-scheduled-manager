# -*- coding: utf-8 -*-
"""
Telegram 定时消息管理器 —— 程序入口

    python main.py

流程：先选择账号（可多账号），再进入菜单：
    [1] 添加      —— 批量创建定时发送消息（模拟每天重复，无需 Premium）
    [2] 查看/删除 —— 查找并删除计划队列里的定时消息
    [3] 切换账号
    [4] 账号管理  —— 新增 / 删除账号
    [0] 退出

也支持直接进入某个功能（会先让你选账号）：
    python main.py add
    python main.py remove
"""

import os
import sys
import asyncio

# 让 `import tg_sched` 能找到 src/ 下的包
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from telethon import TelegramClient
    from tg_sched import __version__
    from tg_sched import client as tg_client
    from tg_sched import bulk, remover
    from tg_sched.accounts import (
        list_accounts, add_account, remove_account, choose_account, session_path,
    )
except ImportError as e:
    print("导入失败：%s" % e)
    print("请先安装依赖：pip install -r requirements.txt")
    sys.exit(1)


def print_menu(account_name):
    print("""
============================================================
 Telegram 定时消息管理器   v{ver}
 当前账号：{acc}
============================================================
 [1] 添加：批量创建定时发送消息（模拟每天重复，无需 Premium）
 [2] 查看/删除：查找并删除计划队列里的定时消息
 [3] 切换账号
 [4] 账号管理（新增 / 删除）
 [0] 退出
============================================================""".format(ver=__version__, acc=account_name))


def manage_accounts():
    """账号管理子菜单：新增 / 删除。"""
    while True:
        names = list_accounts()
        print("\n账号管理")
        print("-" * 64)
        if names:
            for i, n in enumerate(names):
                logged = "已登录" if os.path.exists(session_path(n) + ".session") else "未登录"
                print("[%3d] %-20s %s" % (i, n, logged))
        else:
            print("（当前没有账号）")
        print("-" * 64)
        print("输入： a=新增账号    d=删除账号    回车=返回")

        raw = input("请选择: ").strip().lower()
        if raw == "":
            return
        if raw == "a":
            _ui_add_account()
        elif raw == "d":
            _ui_remove_account(names)
        else:
            print("无效输入。")


def _ui_add_account():
    name = input("请输入新账号名（字母/数字/下划线/连字符，回车取消）: ").strip()
    if not name:
        return
    try:
        if add_account(name):
            print("已新增账号 '%s'。首次使用该账号时会要求手机号登录。" % name)
        else:
            print("账号 '%s' 已存在。" % name)
    except ValueError as e:
        print("新增失败：%s" % e)


def _ui_remove_account(names):
    if not names:
        print("没有可删除的账号。")
        return
    raw = input("请输入要删除的账号编号（回车取消）: ").strip()
    if not raw:
        return
    try:
        idx = int(raw)
        if not (0 <= idx < len(names)):
            print("编号超出范围。")
            return
    except ValueError:
        print("无效输入。")
        return
    name = names[idx]
    sure = input("确认删除账号 '%s'（含其登录会话）？输入 yes 确认: " % name).strip().lower()
    if sure != "yes":
        print("已取消。")
        return
    removed, deleted = remove_account(name)
    if removed:
        print("已删除账号 '%s'%s。" % (name, "（会话文件已删除）" if deleted else ""))
    else:
        print("删除失败。")


async def run_session(account_name, action=None):
    """登录指定账号并进入菜单。返回 (退出整个程序?, 切换到的账号名或None)。"""
    client = tg_client.create_client(account_name)
    await tg_client.login(client, account_name)
    try:
        if action == "add":
            await bulk.run(client)
            return (False, None)
        if action == "remove":
            await remover.run(client)
            return (False, None)

        while True:
            print_menu(account_name)
            choice = input("请选择功能 [1/2/3/4/0]: ").strip()
            if choice == "1":
                await bulk.run(client)
            elif choice == "2":
                await remover.run(client)
            elif choice == "3":
                new_acc = choose_account()
                if new_acc and new_acc != account_name:
                    return (False, new_acc)
            elif choice == "4":
                manage_accounts()
            elif choice in ("0", "q"):
                return (True, None)
            elif choice == "":
                continue
            else:
                print("无效输入，请重新选择。")
    finally:
        await client.disconnect()


async def main(action=None):
    account_name = choose_account()
    if not account_name:
        print("已取消。")
        return

    while True:
        quit_all, next_account = await run_session(account_name, action)
        action = None  # 只对首个账号生效
        if quit_all:
            break
        if next_account:
            account_name = next_account
            continue
        break
    print("\n完成。")


if __name__ == "__main__":
    action = sys.argv[1].lower() if len(sys.argv) > 1 else None
    try:
        asyncio.run(main(action))
    except KeyboardInterrupt:
        print("\n已中断。")
    except Exception as e:
        print("\n发生错误：%s" % e)
