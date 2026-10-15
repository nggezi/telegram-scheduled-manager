# -*- coding: utf-8 -*-
"""交互与显示：聊天名称、选择、各种输入校验、计划消息描述。"""

from datetime import timezone

from telethon.tl.types import Channel, Chat, User

from .config import LOCAL_TZ, MAX_DAYS, repeat_label


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


def choose_chat(dialogs, hint=None):
    """打印聊天列表并让用户选择，返回 Dialog 列表（空列表表示取消）。"""
    print("\n你的聊天列表：")
    print("-" * 64)
    for i, d in enumerate(dialogs):
        print("[%3d] %s" % (i, cjk_width_name(d.entity)))
    print("-" * 64)
    if hint:
        print("提示：%s" % hint)
    while True:
        raw = input("请输入要操作的聊天编号（可输入多个，用逗号分隔；直接回车取消）: ").strip()
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
    """询问预排天数（1 ~ MAX_DAYS）"""
    while True:
        raw = input("请输入要预排的天数（例如 30，最多 %d）: " % MAX_DAYS).strip()
        try:
            n = int(raw)
            if 1 <= n <= MAX_DAYS:
                return n
            if n > MAX_DAYS:
                print("为避免触发 Telegram 频率限制，最多 %d 天；请重新输入。" % MAX_DAYS)
                continue
        except ValueError:
            pass
        print("请输入一个 1 ~ %d 的整数。" % MAX_DAYS)


def ask_text():
    """询问要发送的内容"""
    return input("请输入要定时发送的内容（例如 /qd）: ").strip()


def ask_yes(prompt):
    """要求输入 yes 才返回 True"""
    return input(prompt).strip().lower() == "yes"


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
        # msg.date 一般是带时区的 UTC；若为 naive 则按 UTC 处理，最后统一转本地时区
        dt = msg.date
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(LOCAL_TZ)
        print("    下次发送时间: %s (本地时间)" % local.strftime("%Y-%m-%d %H:%M:%S"))
    if repeat:
        days = repeat / 86400.0
        if repeat == 86400:
            extra = "  <== 这就是每天重复的定时任务！"
        else:
            extra = "  (重复型，约 %.2f 天一次)" % days
        print("    >>> 重复周期  : %s%s" % (repeat_label(repeat), extra))
    else:
        print("    重复周期    : 无（一次性定时消息）")
