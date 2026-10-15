# Work Log — Telegram 定时消息「能删能加」改造

按根目录 `readme.txt` 规范，本文件夹记录本次任务。

## 任务目标

原有仓库只能**删除**服务端残留的“每天重复”定时消息。本次为它增加**批量创建定时
消息**的能力，使其成为「能删能加」的定时消息管理器，并按规范重组目录结构。

## 做了什么

### 1. 功能：加（bulk）

- 非 Premium 号无法创建「一条永久重复」（`schedule_repeat_period` 是 Premium 专属，
  服务端返回 `PREMIUM_ACCOUNT_REQUIRED`），改用「预排 N 天、每天同一时刻」近似。
- 输入本地时间，自动换算 UTC；今天该时刻已过则从明天顺延。
- 排期前显示每个聊天「现有 X 条 + 本次 Y 条」，避免叠加超限。

### 2. 功能：删（remover）

- 从计划队列删除定时消息（含每天重复型，也含一次性）。
- 默认匹配内容含 `/qd` 的消息；无匹配时允许手动输入 ID。
- 时间显示统一转本地时区。

### 3. 目录规范化（本次）

从「根目录一堆脚本」改为标准 Python 项目结构：

```
main.py                 入口（替代 tg_scheduled.py，支持 main.py add/remove）
src/tg_sched/
  config.py             路径/常量/凭据读写/时区/REPEAT_LABELS
  client.py             登录、对话列表、计划队列读写
  ui.py                 聊天选择、输入校验、显示
  bulk.py               功能：加
  remover.py            功能：删
config/
  config.example.txt    凭据模板
  tg_api.txt            实际凭据（git 忽略）
tests/                  离线单元测试
requirements.txt
start.bat               Windows 双击启动（CRLF 编码）
```

### 4. 修复的问题（自审）

| 严重度 | 问题 | 修复 |
|---|---|---|
| 崩溃 | Windows GBK 控制台打印 ✔/✘/⚠ 抛 UnicodeEncodeError | 启动时 stdout/stderr 重配 UTF-8 |
| 崩溃 | `astimezone(格式串)` 误用 | 改 `.astimezone(LOCAL_TZ).strftime(...)` |
| 逻辑 | 「删」只处理重复型，删不掉「加」出来的一次性消息 | 目标改为遍历全部计划消息 |
| 显示 | 计划时间按 UTC 直接显示，误导 | 统一转本地时区 |
| 安全 | `ask_days` 无上限，可能触发 flood/封号 | 限制 1~365 天 |
| 健壮 | `main()` 异常时不断连 | try/finally |
| 健壮 | `get_me()` 返回 None 时崩溃 | 加判断 |
| 体验 | 菜单空回车误退出 | 空回车继续 |
| 体验 | 排期前不知队列已有多少条 | 排期前读取并提示 |
| 限流 | `FLOOD_WAIT` 静默失败 | 明确提示并中止剩余排期 |

## 验证

- `python -m py_compile`：全部源码 + 测试编译通过。
- `python tests/test_schedule.py` / `test_interactions.py` / `test_bulk_run.py`：全 PASS。
- `python main.py`：能读取 `config/tg_api.txt` 并进入登录流程（联网验证需真实账号）。
- `start.bat`：CRLF 编码，双击可运行。

> 未做真实联网排期验证，建议先给自己/Saved Messages 排 2~3 天试跑。
