# -*- coding: utf-8 -*-
"""Telegram 客户端封装：登录、拉取对话、读取计划队列。"""

from telethon import TelegramClient
from telethon.tl.functions.messages import (
    GetScheduledHistoryRequest,
    DeleteScheduledMessagesRequest,
)

from .config import load_or_ask_credentials
from .accounts import session_path


async def login(client, account_name=None):
    """连接并登录，打印账号信息。"""
    label = ("账号 '%s'：" % account_name) if account_name else ""
    print("\n正在连接 Telegram ...%s" % (("（" + label.rstrip("：") + "）") if label else ""))
    await client.start()
    me = await client.get_me()
    if me is None:
        print("登录异常：无法获取账号信息，请重新运行并完成手机号登录。")
        raise RuntimeError("get_me() returned None")
    print("登录成功：%s (@%s)  id=%s%s" % (
        " ".join(filter(None, [me.first_name, me.last_name])),
        me.username or "无",
        me.id,
        ("  [%s]" % account_name) if account_name else "",
    ))
    if getattr(me, "premium", False):
        print("提示：检测到本账号是 Premium —— 你其实可以直接用官方「重复定时」，无需本工具。")
    else:
        print("提示：本账号非 Premium，重复定时不可用；「添加」会用预排 N 天一次性消息来模拟。")


async def list_dialogs(client):
    """拉取全部对话（Dialog 列表）。"""
    print("\n正在拉取聊天列表 ...")
    dialogs = []
    async for d in client.iter_dialogs():
        dialogs.append(d)
    return dialogs


async def fetch_scheduled(client, peer):
    """返回该聊天计划队列中的所有消息（Message 对象）。"""
    res = await client(GetScheduledHistoryRequest(peer=peer, hash=0))
    return list(res.messages)


async def delete_scheduled(client, peer, ids):
    """从计划队列中删除指定消息（不发送）。"""
    await client(DeleteScheduledMessagesRequest(peer=peer, id=ids))


def create_client(account_name):
    """为指定账号创建（未连接的）客户端。凭据共享自 config/tg_api.txt。"""
    api_id, api_hash = load_or_ask_credentials()
    return TelegramClient(session_path(account_name), api_id, api_hash)
