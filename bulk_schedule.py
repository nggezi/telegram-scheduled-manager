# -*- coding: utf-8 -*-
"""
bulk_schedule.py
----------------
【功能：批量“加”】批量创建 Telegram 服务器端「定时发送」消息（一次性排期），
用来模拟不存在的「每天重复」效果 —— 适用于**没有 Telegram Premium**的账号。

背景 / 为什么需要它：
  * 「每天重复发送」依靠计划消息上的字段 schedule_repeat_period = 86400。
  * 该字段是 **Telegram Premium 专属**：非 Premium 账号发送时带上它，服务端
    直接返回 PREMIUM_ACCOUNT_REQUIRED 拒绝。这是服务端限制，脚本无法绕过。
  * 于是退而求其次：一次性预排 N 天，每天一条同样的定时消息，到点服务器自动发。
    跨度用完后再跑一次补排即可（例如每月跑一次）。

用到的官方接口：
  * messages.sendMessage —— 带 schedule_date 参数即为「定时发送」
    （Telethon 高级封装 client.send_message(..., schedule=<带时区的 datetime>)）

安全说明：
  * 只往你**自己选定的聊天**排期，不发历史消息、不加群、不批量骚扰他人。
  * 删除这些排期用 fix_telegram_scheduled.py（或统一入口 tg_scheduled.py 的删除分支）。
"""

import asyncio
from datetime import datetime, timedelta

from telethon.tl.functions.messages import GetScheduledHistoryRequest

# 与 fix_telegram_scheduled.py 共用同一目录下的凭据 / 会话文件（同名），只需登录一次。
from fix_telegram_scheduled import (
    SESSION_FILE,
    cjk_width_name,
    load_or_ask_credentials,
    login,
    list_dialogs,
    choose_chat,
    LOCAL_TZ,
)

# 本地时间显示格式
LOCAL_TIME_FMT = "%Y-%m-%d %H:%M"


def ask_time():
    """询问每天的发送时间（本地时区），返回 (hour, minute)"""
    while True:
        raw = input("请输入每天发送时间（24 小时制 HH:MM，例如 23:10）: ").strip()
        try:
            hh, mm = raw.replace("：", ":").split(":")
            hh, mm = int(hh), int(mm)
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                return hh, mm
        except Exception:
            pass
        print("格式不对，请重新输入，例如 23:10")


def ask_days():
    """询问预排天数"""
    while True:
        raw = input("请输入要预排的天数（例如 30，最多 365）: ").strip()
        try:
            n = int(raw)
            if 1 <= n <= 365:
                return n
            if n > 365:
                print("为避免触发 Telegram 频率限制，最多 365 天；请重新输入。")
                continue
        except ValueError:
            pass
        print("请输入一个 1 ~ 365 的整数。")


def ask_text():
    return input("请输入要定时发送的内容（例如 /qd）: ").strip()


def build_schedule(hour, minute, days, start_today_if_possible=True):
    """
    生成未来 days 天的 UTC 时间列表。
    规则：从「今天该时刻」开始；若今天该时刻已过，则从明天开始顺延，
    保证全天数为 days 条，且都在未来。
    """
    now_local = datetime.now(LOCAL_TZ)
    today_at = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if start_today_if_possible and today_at > now_local:
        first = today_at
    else:
        first = today_at + timedelta(days=1)

    return [first + timedelta(days=i) for i in range(days)]


async def existing_scheduled(client, peer):
    """返回该聊天计划队列里的所有消息（可能为空）"""
    res = await client(GetScheduledHistoryRequest(peer=peer, hash=0))
    return list(res.messages)


async def run(client):
    """批量排期主流程。client 已登录。"""
    while True:
        dialogs = await list_dialogs(client)
        chosen = choose_chat(
            dialogs,
            hint="选择要批量排期定时消息的目标聊天（例如某个打卡 Bot 的私聊）。",
        )
        if not chosen:
            print("已取消。")
            return

        hour, minute = ask_time()
        days = ask_days()
        text = ask_text()
        if not text:
            print("内容为空，跳过。")
            continue

        plan = build_schedule(hour, minute, days)
        print("\n将为选定的 %d 个聊天，各排期 %d 条定时消息：" % (len(chosen), len(plan)))
        print("  内容    : %r" % text)
        print("  首条    : %s（本地时间）" % plan[0].astimezone(LOCAL_TZ).strftime(LOCAL_TIME_FMT))
        print("  末条    : %s（本地时间）" % plan[-1].astimezone(LOCAL_TZ).strftime(LOCAL_TIME_FMT))
        print("  间隔    : 每天同一时刻")

        # 排期前先看看每个目标聊天当前计划队列里已有多少条，避免叠加超限
        for d in chosen:
            try:
                existing = await existing_scheduled(client, d.input_entity)
            except Exception as e:
                print("  （提示：无法读取 %s 的现有计划队列：%s）" % (cjk_width_name(d.entity), e))
                continue
            total = len(existing) + len(plan)
            flag = "  ⚠ 叠加后可能超过计划队列上限！" if total > 100 else ""
            print("  %s：现有 %d 条，加上本次 %d 条 = %d 条%s"
                  % (cjk_width_name(d.entity), len(existing), len(plan), total, flag))

        confirm = input("\n确认创建？输入 yes 执行，其它任意键取消: ").strip().lower()
        if confirm != "yes":
            print("已取消，未创建任何消息。")
            continue

        for d in chosen:
            name = cjk_width_name(d.entity)
            print("\n" + "=" * 64)
            print("正在为聊天创建定时消息：%s   id=%s" % (name, d.id))
            print("=" * 64)
            ok = err = 0
            for dt in plan:
                try:
                    await client.send_message(d.input_entity, text, schedule=dt)
                    ok += 1
                    print("  ✔ 已排期 %s" % dt.astimezone(LOCAL_TZ).strftime(LOCAL_TIME_FMT))
                except Exception as e:
                    err += 1
                    print("  ✘ 排期失败 %s : %s" % (dt.astimezone(LOCAL_TZ).strftime(LOCAL_TIME_FMT), e))
                    if "PREMIUM" in str(e).upper():
                        print("  该账号无 Premium，请勿使用重复周期；本脚本本就只做一次性排期。")
                        break
                    if "FLOOD_WAIT" in str(e).upper():
                        print("  触发 Telegram 频率限制，建议等待一段时间后重试；已中止该聊天的剩余排期。")
                        break
            print("\n  完成：成功 %d 条，失败 %d 条。" % (ok, err))
            print("  提示：可用删除功能（fix_telegram_scheduled.py 或统一入口）查看/删除这些排期。")

        again = input("\n是否继续为其它聊天排期？(y/N): ").strip().lower()
        if again != "y":
            return


async def main():
    api_id, api_hash = load_or_ask_credentials()
    from telethon import TelegramClient
    client = TelegramClient(SESSION_FILE, api_id, api_hash)
    await login(client)
    try:
        await run(client)
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
