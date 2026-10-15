# -*- coding: utf-8 -*-
"""全局配置：路径、常量、本地时区、凭据读写。

路径约定（基于项目根目录）：
    <root>/config/tg_api.txt     凭据（api_id / api_hash），已被 .gitignore 忽略
    <root>/config/tg_scheduled.session   会话文件，已被 .gitignore 忽略
"""

import os
import sys
from datetime import datetime

# UTF-8 输出（Windows 控制台默认可能是 GBK，打印 ✔/✘/⚠ 会崩溃）
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 项目根目录：src/tg_sched/config.py -> 上溯三级到根
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIG_DIR = os.path.join(ROOT_DIR, "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "tg_api.txt")
SESSION_FILE = os.path.join(CONFIG_DIR, "tg_scheduled")

# 本地时区（供排期/显示复用）
LOCAL_TZ = datetime.now().astimezone().tzinfo

# 本地时间显示格式
LOCAL_TIME_FMT = "%Y-%m-%d %H:%M"

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

# 每次最多预排天数（避免触发 Telegram 频率限制）
MAX_DAYS = 365
# 计划队列条数经验上限，仅用于提醒
QUEUE_WARN_THRESHOLD = 100


def repeat_label(seconds):
    """把重复周期秒数转成人类可读文本"""
    if seconds in REPEAT_LABELS:
        return REPEAT_LABELS[seconds]
    days = seconds / 86400
    return "%d 秒 (约 %.2f 天)" % (seconds, days)


def load_or_ask_credentials():
    """从 config/tg_api.txt 读取凭据；不存在则交互询问并保存。"""
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
            print("已从 config/tg_api.txt 读取到 api_id / api_hash。")
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
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("api_id=%s\napi_hash=%s\n" % (api_id, api_hash))
        print("已保存到 config/tg_api.txt（下次自动读取）。")
    except Exception as e:
        print("（警告：无法保存凭据：%s，本次仍可继续）" % e)
    return int(api_id), api_hash
