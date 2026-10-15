# -*- coding: utf-8 -*-
"""【功能：删】查找并删除计划队列里的定时消息（含每天重复型）。"""

from .client import list_dialogs, fetch_scheduled, delete_scheduled
from .ui import cjk_width_name, choose_chat, describe_scheduled, ask_yes
from .config import repeat_label


async def run(client):
    """删除主流程。client 已登录。"""
    while True:
        dialogs = await list_dialogs(client)
        chosen = choose_chat(
            dialogs,
            hint="已注销账号通常显示为 [已注销]，名字可能是 'Deleted Account'。",
        )
        if not chosen:
            print("已取消。")
            return

        for d in chosen:
            await _process_chat(client, d)

        again = input("\n是否继续检查其它聊天？(y/N): ").strip().lower()
        if again != "y":
            return


async def _process_chat(client, d):
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
        return

    if not msgs:
        print("  该聊天的计划队列为空 —— 这里没有服务器端定时消息。")
        print("  如果消息仍在每天发送，说明它很可能不在这个账号的计划队列里，")
        print("  而是由第三方（例如某个仍然在线的机器人/服务）按计划发给你的。")
        return

    print("  找到 %d 条计划消息：" % len(msgs))
    repeating = []
    for m in msgs:
        describe_scheduled(m)
        if getattr(m, "schedule_repeat_period", None):
            repeating.append(m)

    targets = _pick_targets(msgs, repeating)
    if targets is None:
        return

    print("\n  将要删除以下【计划消息】（从计划队列永久移除，之后不再发送）：")
    for m in targets:
        period = getattr(m, "schedule_repeat_period", None)
        kind = repeat_label(period) if period else "一次性"
        print("    - ID=%s  类型=%s  内容=%r" % (m.id, kind, m.message))

    if not ask_yes("\n  确认删除？输入 yes 执行，其它任意键取消: "):
        print("  已取消，未删除任何东西。")
        return

    ids = [m.id for m in targets]
    try:
        await delete_scheduled(client, d.input_entity, ids)
        print("  ✔ 已删除计划消息 ID: %s" % ids)
    except Exception as e:
        print("  ✘ 删除失败：%s" % e)


def _pick_targets(msgs, repeating):
    """
    选出要删除的目标：
      1) 默认内容包含 /qd 的消息（重复型或一次性都算）；
      2) 若没有匹配项，让用户手动输入计划消息 ID。
    返回消息列表，或 None 表示跳过。
    """
    targets = [m for m in msgs if m.message and "/qd" in m.message]
    if targets:
        return targets

    if repeating:
        print("\n  有重复任务，但没有内容包含 '/qd' 的。")
    else:
        print("\n  该聊天只有一次性定时消息，且没有内容包含 '/qd' 的。")
    ans = input("  是否要手动指定要删除的计划消息 ID（回车跳过）: ").strip()
    if not ans:
        return None
    try:
        ids = [int(x) for x in ans.replace("，", ",").split(",") if x.strip()]
    except ValueError:
        print("  输入无效，跳过。")
        return None
    targets = [m for m in msgs if m.id in ids]
    if not targets:
        print("  没有匹配到计划消息 ID，跳过。")
        return None
    return targets
