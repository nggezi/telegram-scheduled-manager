# -*- coding: utf-8 -*-
"""【功能：加】批量创建定时发送消息（一次性排期），模拟每天重复效果。

适用于**没有 Telegram Premium**的账号：重复字段 schedule_repeat_period 是
Premium 专属，非 Premium 号发送时会被服务端拒绝；于是改为预排 N 天、每天一条。
"""

from datetime import datetime, timedelta

from .client import list_dialogs, fetch_scheduled
from .ui import cjk_width_name, choose_chat, ask_time, ask_days, ask_text, ask_yes
from .config import LOCAL_TZ, LOCAL_TIME_FMT, QUEUE_WARN_THRESHOLD


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


def _fmt(dt):
    return dt.astimezone(LOCAL_TZ).strftime(LOCAL_TIME_FMT)


async def run(client):
    """排期主流程。client 已登录。"""
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
        print("  首条    : %s（本地时间）" % _fmt(plan[0]))
        print("  末条    : %s（本地时间）" % _fmt(plan[-1]))
        print("  间隔    : 每天同一时刻")

        # 排期前先看看每个目标聊天当前计划队列里已有多少条，避免叠加超限
        for d in chosen:
            try:
                existing = await fetch_scheduled(client, d.input_entity)
            except Exception as e:
                print("  （提示：无法读取 %s 的现有计划队列：%s）" % (cjk_width_name(d.entity), e))
                continue
            total = len(existing) + len(plan)
            flag = "  ⚠ 叠加后可能超过计划队列上限！" if total > QUEUE_WARN_THRESHOLD else ""
            print("  %s：现有 %d 条，加上本次 %d 条 = %d 条%s"
                  % (cjk_width_name(d.entity), len(existing), len(plan), total, flag))

        if not ask_yes("\n确认创建？输入 yes 执行，其它任意键取消: "):
            print("已取消，未创建任何消息。")
            continue

        for d in chosen:
            await _schedule_chat(client, d, plan, text)

        again = input("\n是否继续为其它聊天排期？(y/N): ").strip().lower()
        if again != "y":
            return


async def _schedule_chat(client, d, plan, text):
    name = cjk_width_name(d.entity)
    print("\n" + "=" * 64)
    print("正在为聊天创建定时消息：%s   id=%s" % (name, d.id))
    print("=" * 64)
    ok = err = 0
    for dt in plan:
        try:
            await client.send_message(d.input_entity, text, schedule=dt)
            ok += 1
            print("  ✔ 已排期 %s" % _fmt(dt))
        except Exception as e:
            err += 1
            print("  ✘ 排期失败 %s : %s" % (_fmt(dt), e))
            if "PREMIUM" in str(e).upper():
                print("  该账号无 Premium，请勿使用重复周期；本工具本就只做一次性排期。")
                break
            if "FLOOD_WAIT" in str(e).upper():
                print("  触发 Telegram 频率限制，建议等待一段时间后重试；已中止该聊天的剩余排期。")
                break
    print("\n  完成：成功 %d 条，失败 %d 条。" % (ok, err))
    print("  提示：可用「查看/删除」功能查看或删除这些排期。")
