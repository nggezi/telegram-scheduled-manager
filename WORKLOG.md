# Work Log — Telegram 定时消息「能删能加」改造

按根目录 `readme.txt` 规范，本文件夹记录本次任务。

## 任务目标

原有仓库 `telegram-scheduled-fix` 只能**删除**服务端残留的“每天重复”定时消息。
本次为它增加**批量创建定时消息**的能力，使其成为「能删能加」的定时消息管理器，
并把本地文件夹重命名为 `telegram-scheduled-manager`。

## 目录

- `telegram-scheduled-manager/` —— 改造后的仓库（本地文件夹已改名，**remote 未动**，
  仍指向 `https://github.com/nggezi/telegram-scheduled-fix.git`）

## 改了什么

### 新增文件

| 文件 | 作用 |
|---|---|
| `tg_scheduled.py` | 统一入口：`[1] 添加` / `[2] 查看删除` / `[0] 退出` |
| `bulk_schedule.py` | 「加」的模块：批量创建一次性定时消息，非 Premium 号用 N 天预排模拟每天重复 |
| `tests/test_schedule.py` | `build_schedule` 的离线单元测试（不联网、不需账号） |

### 修改文件

| 文件 | 改动 |
|---|---|
| `fix_telegram_scheduled.py` | 1) 新增 `LOCAL_TZ` 供复用；2) 把删除主流程抽成 `run(client)`，供统一入口调用（独立运行行为不变） |
| `README.md` | 顶部改为「定时消息管理器」定位；新增「功能二：批量创建定时消息」完整文档 |

### 本地改名

`telegram-scheduled-fix/` → `telegram-scheduled-manager/`（仅本地文件夹名；
git remote 与 GitHub 仓库名保持不变）。

## 关键设计说明

- **非 Premium 无法创建“一条永久重复”任务**：`schedule_repeat_period` 是 Premium 专属，
  服务端会返回 `PREMIUM_ACCOUNT_REQUIRED`。脚本改用「一次性预排 N 天、每天同一时刻」
  来近似，跨度到期后再跑一次补排。
- **时区处理**：用户按本地时间输入 `HH:MM`，脚本换算为带时区的 UTC 交给 Telethon。
- **时间规则**：若“今天该时刻”已过则从明天顺延，保证所有排期都在未来。
- **共用登录**：三个脚本共用同目录的 `tg_api.txt` 与 `tg_scheduled_fix.session`。
- **安全**：只操作本账号计划队列；`tg_api.txt` / `*.session` 仍由 `.gitignore` 忽略。

## 验证情况

- `python -m py_compile`：三个脚本均编译通过。
- `python -c "import ..."`：模块互相导入正常。
- `python tests/test_schedule.py`：4 项测试全部 PASS。
- 时区换算抽查：本地 23:10 (UTC+8) → UTC 15:10，`timestamp()` 均为未来时间。

> 未做真实联网排期验证（需真实账号登录），建议先在小范围（如给自己 / Saved Messages）
> 排 2~3 天试跑，确认无误再放大跨度。
