# -*- coding: utf-8 -*-
"""
tg_scheduled.py
---------------
统一入口：Telegram 定时消息管理器（既能“加”也能“删”）。

  [1] 添加 —— 批量创建定时发送消息（一次性排期，模拟每天重复；无需 Premium）
  [2] 查看 / 删除 —— 查找并删除计划队列里的定时消息（含每天重复型）

两个功能各自也可单独运行：
  * 只加： python bulk_schedule.py
  * 只删： python fix_telegram_scheduled.py

它们共用同一目录下的 tg_api.txt 与 tg_scheduled_fix.session，只需登录一次。
"""

import sys
import asyncio

try:
    from telethon import TelegramClient
except ImportError:
    print("缺少依赖 telethon，请先运行：\n    pip install telethon")
    sys.exit(1)

from fix_telegram_scheduled import (
    SESSION_FILE,
    load_or_ask_credentials,
    login,
)
import fix_telegram_scheduled as remover
import bulk_schedule as adder


MENU = """
============================================================
 Telegram 定时消息管理器  ——  能删，也能加
============================================================
 [1] 添加：批量创建定时发送消息（模拟每天重复，无需 Premium）
 [2] 查看/删除：查找并删除计划队列里的定时消息
 [0] 退出
============================================================"""


async def main():
    api_id, api_hash = load_or_ask_credentials()
    client = TelegramClient(SESSION_FILE, api_id, api_hash)
    await login(client)

    try:
        while True:
            print(MENU)
            choice = input("请选择功能 [1/2/0]: ").strip()

            if choice == "1":
                await adder.run(client)
            elif choice == "2":
                await remover.run(client)
            elif choice in ("0", "q"):
                break
            elif choice == "":
                # 直接回车不退出，避免误触
                continue
            else:
                print("无效输入，请重新选择。")
    finally:
        await client.disconnect()
    print("\n完成。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n已中断。")
    except Exception as e:
        print("\n发生错误：%s" % e)
