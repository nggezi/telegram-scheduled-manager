# -*- coding: utf-8 -*-
"""
Telegram 定时消息管理器 —— 程序入口

    python main.py

菜单：
    [1] 添加      —— 批量创建定时发送消息（模拟每天重复，无需 Premium）
    [2] 查看/删除 —— 查找并删除计划队列里的定时消息

也支持直接进入某个功能：
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
    from tg_sched import __version__
    from tg_sched.config import load_or_ask_credentials
    from tg_sched import client as tg_client
    from tg_sched import bulk, remover
except ImportError as e:
    print("导入失败：%s" % e)
    print("请先安装依赖：pip install -r requirements.txt")
    sys.exit(1)


MENU = """
============================================================
 Telegram 定时消息管理器   v{ver}   ——  能删，也能加
============================================================
 [1] 添加：批量创建定时发送消息（模拟每天重复，无需 Premium）
 [2] 查看/删除：查找并删除计划队列里的定时消息
 [0] 退出
============================================================""".format(ver=__version__)


async def main(action=None):
    api_id, api_hash = load_or_ask_credentials()
    from telethon import TelegramClient
    from tg_sched.config import SESSION_FILE

    client = TelegramClient(SESSION_FILE, api_id, api_hash)
    await tg_client.login(client)

    try:
        if action == "add":
            await bulk.run(client)
            return
        if action == "remove":
            await remover.run(client)
            return

        while True:
            print(MENU)
            choice = input("请选择功能 [1/2/0]: ").strip()
            if choice == "1":
                await bulk.run(client)
            elif choice == "2":
                await remover.run(client)
            elif choice in ("0", "q"):
                break
            elif choice == "":
                continue
            else:
                print("无效输入，请重新选择。")
    finally:
        await client.disconnect()
    print("\n完成。")


if __name__ == "__main__":
    action = sys.argv[1].lower() if len(sys.argv) > 1 else None
    try:
        asyncio.run(main(action))
    except KeyboardInterrupt:
        print("\n已中断。")
    except Exception as e:
        print("\n发生错误：%s" % e)
