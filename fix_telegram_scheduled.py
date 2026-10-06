# -*- coding: utf-8 -*-
"""
fix_telegram_scheduled.py
-------------------------
查找并删除 Telegram 服务器端残留的“每天重复发送”定时消息（例如每天 23:10 自动发送 /qd）。

原理（基于 Telegram 官方 MTProto API，已核实）：
  * 定时消息保存在每个聊天各自的“schedule queue”（计划队列）中，与已发送的历史消息完全独立。
  * “每天重复”的消息在服务器上仍然是【一条】计划消息，只是带有一个字段
        message.schedule_repeat_period = 86400   (秒, = 每天)
    每次发送后，服务器会用【同一个计划消息 ID】自动重新安排下一次发送。
  * 因此只要把这条计划消息从计划队列里删除，重复任务就永久停止；
    删除已经发送出去的历史消息没有任何作用（这正是你之前删了没用、第二天又出现的原因）。

用到的官方接口：
  * messages.getScheduledHistory   —— 获取某聊天计划队列中的全部消息
  * messages.getScheduledMessages  —— 按 ID 获取计划队列中的指定消息
  * messages.deleteScheduledMessages —— 从计划队列中删除消息（不发送）

注意：重复定时消息是 Telegram Premium 功能，但“删除”计划消息不需要 Premium，
      只要是本账号自己的计划消息即可删除。
"""

import os
import sys
import asyncio
import unicodedata

try:
    from telethon import TelegramClient
    from telethon.tl.functions.messages import (
        GetScheduledHistoryRequest,
        GetScheduledMessagesRequest,
        DeleteScheduledMessagesRequest,
    )
    from telethon.tl.types import Channel, Chat, User
except ImportError:
    print("缺少依赖 telethon，请先运行：\n    pip install telethon")
    sys.exit(1)


SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_scheduled_fix")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_api.txt")

# 重复周期（秒）-> 人类可读
REPEAT_LABELS = {
    60: "每 60 秒 (仅测试服务器)",
    300: "每 300 秒 (仅测试服务器)",
    86400: "每天",
    7 * 86400: "每周",
    14 * 86400: "每两周",
    30 * 86400: "每月",
    91 * 86400: "每三个月",
    182 * 86400: "每半年",
    365 * 86400: "每年",
}


def repeat_label(seconds):
    if seconds in REPEAT_LABELS:
        return REPEAT_LABELS[seconds]
    days = seconds / 86400
    return "%d 秒 (约 %.2f 天)" % (seconds, days)


def cjk_width_name(entity):
    """给聊天起一个方便辨认的名字"""
    if entity is None:
        return "???"
    if isinstance(entity, User):
        name = " ".join(filter(None, [entity.first_name, entity.last_name])) or "(无名字)"
        if entity.bot:
            name += " [Bot]"
        if getattr(entity, "deleted", False):
            name += " [已注销]"
        return name
    if isinstance(entity, Chat):
        return entity.title + " [群组]"
    if isinstance(entity, Channel):
        tag = "频道" if entity.broadcast else "超级群"
        name = entity.title + " [" + tag + "]"
        if getattr(entity, "deleted", False):
            name += " [已注销]"
        return name
    return str(entity)


def load_or_ask_credentials():
    api_id = api_hash = None
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("api_id"):
                        api_id = line.split("=", 1)[1].strip()
                    elif line.startswith("api_hash"):
                        api_hash = line.split("=", 1)[1].strip()
        except Exception:
            pass
        if api_id and api_hash:
            print("已从 tg_api.txt 读取到 api_id / api_hash。")
            return int(api_id), api_hash

    print("=" * 64)
    print("首次使用，请填写 Telegram API 凭据（只需填一次）。")
    print("获取方法：")
    print("  1. 浏览器打开 https://my.telegram.org")
    print("  2. 用你的手机号登录 -> API development tools")
    print("  3. 创建一个应用，得到 api_id (数字) 和 api_hash (一串字母数字)")
    print("=" * 64)
    api_id = input("请输入 api_id  : ").strip()
    api_hash = input("请输入 api_hash: ").strip()
    try:
        int(api_id)
    except ValueError:
        print("api_id 必须是数字。")
        sys.exit(1)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("api_id=%s\napi_hash=%s\n" % (api_id, api_hash))
        print("已保存到 tg_api.txt（下次自动读取）。")
    except Exception as e:
        print("（警告：无法保存凭据：%s，本次仍可继续）" % e)
    return int(api_id), api_hash


async def login(client):
    print("\n正在连接 Telegram ...")
    await client.start()
    me = await client.get_me()
    print("登录成功：%s (@%s)  id=%s" % (
        " ".join(filter(None, [me.first_name, me.last_name])),
        me.username or "无",
        me.id,
    ))


async def list_dialogs(client):
    print("\n正在拉取聊天列表 ...")
    dialogs = []
    async for d in client.iter_dialogs():
        dialogs.append(d)
    return dialogs


def choose_chat(dialogs):
    print("\n你的聊天列表：")
    print("-" * 64)
    for i, d in enumerate(dialogs):
        print("[%3d] %s" % (i, cjk_width_name(d.entity)))
    print("-" * 64)
    print("提示：已注销账号通常显示为 [已注销]，名字可能是 'Deleted Account'。")
    while True:
        raw = input("请输入要检查的聊天编号（可输入多个，用逗号分隔；直接回车取消）: ").strip()
        if raw == "":
            return []
        try:
            idxs = [int(x.strip()) for x in raw.replace("，", ",").split(",") if x.strip() != ""]
        except ValueError:
            print("输入格式不对，请输入数字，例如 3 或 3,5,8")
            continue
        if all(0 <= i < len(dialogs) for i in idxs):
            return [dialogs[i] for i in idxs]
        print("编号超出范围，请重新输入。")


async def fetch_scheduled(client, peer):
    """返回该聊天计划队列中的所有消息（Message 对象）。"""
    res = await client(GetScheduledHistoryRequest(peer=peer, hash=0))
    return list(res.messages)


def describe_scheduled(msg):
    """打印一条计划消息的详细信息"""
    text = msg.message or "(无文本)"
    text_show = text.replace("\n", "\\n")
    if len(text_show) > 80:
        text_show = text_show[:80] + "..."

    repeat = getattr(msg, "schedule_repeat_period", None)
    print("    计划消息 ID : %s" % msg.id)
    print("    内容        : %r" % text_show)
    if msg.date:
        print("    下次发送时间: %s (UTC)" % msg.date.strftime("%Y-%m-%d %H:%M:%S"))
    if repeat:
        print("    >>> 重复周期  : %s  <== 这就是每天重复的定时任务！"
              % repeat_label(repeat))
    else:
        print("    重复周期    : 无（一次性定时消息）")


async def main():
    api_id, api_hash = load_or_ask_credentials()

    client = TelegramClient(SESSION_FILE, api_id, api_hash)
    await login(client)

    while True:
        dialogs = await list_dialogs(client)
        chosen = choose_chat(dialogs)
        if not chosen:
            print("已取消。")
            break

        for d in chosen:
            name = cjk_width_name(d.entity)
            print("\n" + "=" * 64)
            print("正在检查聊天：%s   id=%s" % (name, d.id))
            print("=" * 64)

            try:
                msgs = await fetch_scheduled(client, d.input_entity)
            except Exception as e:
                print("  查询计划队列失败：%s" % e)
                print("  （如果你不是该聊天的管理员，可能返回 CHAT_ADMIN_REQUIRED；"
                      "这种聊天你本来就无法保留个人计划任务）")
                continue

            if not msgs:
                print("  该聊天的计划队列为空 —— 这里没有服务器端定时消息。")
                print("  如果 /qd 仍在每天发送，说明它很可能不在这个账号的计划队列里，")
                print("  而是由第三方（例如某个仍然在线的机器人/服务）按计划发给你的，")
                print("  请看脚本末尾的【排查方法】。")
                continue

            print("  找到 %d 条计划消息：" % len(msgs))
            repeating = []
            for m in msgs:
                describe_scheduled(m)
                if getattr(m, "schedule_repeat_period", None):
                    repeating.append(m)

            if not repeating:
                print("\n  该聊天没有“重复型”定时消息，只有一次性任务，未做任何删除。")
                continue

            # 只针对重复任务，默认只删除内容包含 /qd 的
            targets = [m for m in repeating if m.message and "/qd" in m.message]
            if not targets:
                print("\n  有重复任务，但没有内容包含 '/qd' 的。")
                ans = input("  是否要手动指定要删除的重复任务 ID（回车跳过）: ").strip()
                if not ans:
                    continue
                try:
                    ids = [int(x) for x in ans.replace("，", ",").split(",") if x.strip()]
                except ValueError:
                    print("  输入无效，跳过。")
                    continue
                targets = [m for m in repeating if m.id in ids]
                if not targets:
                    print("  没有匹配到计划消息 ID，跳过。")
                    continue

            print("\n  将要删除以下【重复定时消息】（从计划队列永久移除，之后不再重复）：")
            for m in targets:
                print("    - ID=%s  周期=%s  内容=%r" % (
                    m.id, repeat_label(m.schedule_repeat_period), m.message))

            confirm = input("\n  确认删除？输入 yes 执行，其它任意键取消: ").strip().lower()
            if confirm != "yes":
                print("  已取消，未删除任何东西。")
                continue

            ids = [m.id for m in targets]
            try:
                await client(DeleteScheduledMessagesRequest(peer=d.input_entity, id=ids))
                print("  ✔ 已删除计划消息 ID: %s" % ids)
            except Exception as e:
                print("  ✘ 删除失败：%s" % e)

        again = input("\n是否继续检查其它聊天？(y/N): ").strip().lower()
        if again != "y":
            break

    await client.disconnect()
    print("\n完成。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n已中断。")
    except Exception as e:
        print("\n发生错误：%s" % e)
        print("排查方法见脚本顶部注释或 README。")
