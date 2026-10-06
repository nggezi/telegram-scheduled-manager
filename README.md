# Telegram Repeating Scheduled Message Remover

一个交互式 Python 脚本，用来**查找并删除 Telegram 服务器端残留的“每天重复发送”定时消息**。

## 解决的场景

你对某个 Bot 设置过“每天重复发送一条消息”（例如每天 23:10 自动发送 `/qd`）。
后来这个 Bot 被注销（聊天顶部显示「已注销账号」），但消息**每天仍然照发**：

```
10月3日  /qd  23:10
10月4日  /qd  23:10
10月5日  /qd  23:10
```

Telegram Desktop / 手机端都找不到「已安排的消息」入口，删除已发送的历史消息也没用——第二天照样出现。

## 原理

基于 Telegram **官方 MTProto API**（不是外挂，正常官方用途）：

- 定时消息保存在每个聊天各自的 **schedule queue（计划队列）** 中，与已发送的历史消息**完全独立**。
- “每天重复”的消息在服务器上仍然是**一条**计划消息，只是带字段
  `message.schedule_repeat_period = 86400`（秒，= 每天）。
- 每次发送后，服务器用**同一个计划消息 ID** 自动重新安排下一次。
- 因此只要把这条计划消息从队列里删除，重复任务就**永久停止**；
  删除已发送的历史消息没有任何作用（这就是“删了第二天又出现”的原因）。

> 重复定时消息是 Telegram Premium 功能；但**删除**自己的计划消息不需要 Premium。

用到的官方接口：

| 官方接口 | Telethon 类 |
|---|---|
| `messages.getScheduledHistory` | `GetScheduledHistoryRequest` |
| `messages.getScheduledMessages` | `GetScheduledMessagesRequest` |
| `messages.deleteScheduledMessages` | `DeleteScheduledMessagesRequest` |

`getScheduledMessages` 只能按已知 ID 查，而脚本并不知道 ID，所以实际用
`getScheduledHistory` 拉取整个队列，再筛选出 `schedule_repeat_period` 非空且内容含 `/qd` 的重复任务。

## 环境要求

- Windows / macOS / Linux
- Python 3.8+
- [Telethon](https://github.com/LonamiWebs/Telethon)

## 安装

```bash
pip install telethon
```

## 运行

```bash
python fix_telegram_scheduled.py
```

运行流程：

1. 首次运行会让你输入 `api_id` 和 `api_hash`，保存到 `tg_api.txt`，下次自动读取。
2. 用手机号登录（验证码发到你的 Telegram App，不是短信）。
3. 列出你的聊天，输入要检查的聊天编号（可多个，逗号分隔）。
4. 脚本查询该聊天的计划队列，打印全部计划消息，并**高亮重复任务**。
5. **打印待删除任务明细，要求你输入 `yes` 确认**后才删除。
6. 只删除你选定聊天中内容含 `/qd` 的重复任务，不动其它聊天、不删历史消息。

### 获取 api_id / api_hash

1. 浏览器打开 <https://my.telegram.org>（必须用浏览器，不能在 App 内打开）。
2. 输入手机号（带国家代码，如 `+8613800138000`）→ Next。
3. 验证码会发到你的 **Telegram App**，填入。
4. 进入 **API development tools**，随便填应用信息（title/short name 等）后创建。
5. 页面顶部得到的 `api_id`（数字）和 `api_hash`（32 位字母数字）就是所需凭据。

### 手机号格式

- 带国家代码、带 `+`，例如 `+8613800138000`
- 不要有空格、横线、括号

## 安全与隐私

- `api_hash` 相当于密码，**不要外传**；`tg_api.txt` 与 `*.session` 已被 `.gitignore` 忽略，切勿提交或分享。
- 脚本只读写**你自己账号**的计划队列，不发消息、不加群、不批量操作。
- 建议不要高频重复运行脚本。正常一次操作即可。
- 登录后可在 Telegram App「设置 → 设备」里登出该 session。

## 排查方法

- **计划队列为空**：说明 `/qd` 不是本账号的计划消息，而是某个仍在运行的第三方 Bot/服务按时发给你。注销的 Bot 本身不会再发，需从其服务来源取消，API 无法删除别人的计划消息。
- **报 `CHAT_ADMIN_REQUIRED`**：你在该聊天不是管理员，无法读写其计划队列（你个人的定时消息一般在自己发起的私聊里，不会遇到）。
- **找不到 `schedule_repeat_period`**：账号无 Premium，重复任务可能已被降级/发成普通定时；脚本会提示无重复任务，不误删。
- **认不出「已注销账号」**：名字通常是 `Deleted Account`，会标 `[已注销]`；可多选几个编号一起查。
- **验证删除成功**：次日 23:10 前后再跑一次，计划队列里应不再出现该任务。

## 免责声明

本项目仅操作调用者本人账号的计划消息，用于清理自己设置过的重复定时任务。请遵守 Telegram 服务条款，自行承担使用风险。

## License

MIT
