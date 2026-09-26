# hwn 数字自我学习器

面向 AstrBot 4.24+ 的本地插件。它只采集配置的主人 QQ 用户 ID 发给机器人的合格文本消息，批量提炼稳定的表达/判断习惯，并更新本地 `hwn` Skill 与同名 AstrBot Persona。

## 安全边界

- `owner_user_id` 为空时不采集任何人。
- 自动蒸馏只更新表达和判断习惯，不推断身份、经历、关系或事实。
- 本人事实只能通过 `/hwn fact` 显式写入。
- 引用、转发、命令、纯链接和过短消息不会采集。
- 每条自动候选至少需要三条不同消息证据，并满足置信度阈值。
- 蒸馏失败不推进处理游标，原始观察和更新前备份保存在 `data/plugin_data/astrbot_plugin_hwn_learner/`。

## 安装与配置

1. 在 AstrBot WebUI 的“插件”页上传本插件 ZIP。
2. 在 QQ 中发送 `/hwn whoami`。
3. 打开插件配置，把返回的 User ID 填入 `owner_user_id`。
4. 选择蒸馏模型；留空则使用触发消息会话当前模型。
5. 在 QQ 中执行 `/hwn sync`，然后把配置文件的默认人格设为 `hwn`，或用 `/persona` 切换。

插件首次启动会把初始资料复制到 `data/skills/hwn/`，并创建或更新 ID 为 `hwn` 的 Persona。

## 命令

- `/hwn help`
- `/hwn whoami`
- `/hwn status`
- `/hwn distill`
- `/hwn feedback <纠正内容>`
- `/hwn fact <本人确认的事实>`
- `/hwn sync`
