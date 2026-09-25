# bcat2nd

将个人聊天记录蒸馏成可持续更新的数字自我，并部署到 AstrBot / QQ Bot。

当前仓库包含：

- `hwn` 数字自我 Skill：个人事实记忆、表达风格和行为边界。
- AstrBot Persona 提示词：让普通 QQ 对话默认使用 hwn 的表达和判断方式。
- `astrbot_plugin_hwn_learner`：只从指定主人账号采集消息，按批次蒸馏稳定规律，并同步更新 Skill 与 Persona。

## 功能

- 仅采集配置的主人 QQ 用户 ID，不学习其他群成员。
- 自动跳过命令、引用、转发、纯链接和过短消息。
- 默认每积累 50 条合格消息执行一次后台蒸馏。
- 自动候选必须至少有 3 条不同消息作为证据，并达到置信度阈值。
- 自动学习只更新表达、沟通和判断习惯，不自行推断身份、经历或关系。
- 个人事实只能通过主人执行 `/hwn fact` 显式确认。
- 每次修改前自动备份画像文件；蒸馏失败不会推进处理游标。
- 画像变化后自动创建或刷新 AstrBot 中的 `hwn` Persona。

## 目录结构

```text
astrbot-hwn/
├─ astrbot_plugin_hwn_learner/       # AstrBot 插件源码
│  ├─ main.py                        # 消息采集、命令、蒸馏和 Persona 同步
│  ├─ learner.py                     # 文件存储、候选校验和画像更新
│  ├─ _conf_schema.json              # WebUI 可视化配置
│  ├─ metadata.yaml                  # AstrBot 插件元数据
│  ├─ seed_skill/hwn/                # 首次安装使用的初始画像
│  └─ tests/                         # 单元与集成测试
├─ astrbot_plugin_hwn_learner.zip    # 可直接上传的插件包
├─ hwn-astrbot-skill.zip             # 独立 Skill 安装包
└─ hwn-persona.txt                    # 独立 Persona 系统提示词
```

## 环境要求

- AstrBot `>= 4.24, < 5`
- 已配置可用的聊天模型提供商
- QQ 官方机器人、QQ 官方 Webhook 或 OneBot v11 适配器

插件不需要额外的 Python 第三方依赖。

## 安装

### 推荐：安装完整学习插件

1. 下载 [`astrbot_plugin_hwn_learner.zip`](astrbot-hwn/astrbot_plugin_hwn_learner.zip)。
2. 打开 AstrBot WebUI，进入“插件 → 插件 → 安装插件”。
3. 选择“文件上传”，上传 ZIP。
4. 安装后在 QQ 中发送：

   ```text
   /hwn whoami
   ```

5. 打开插件配置，将返回的 User ID 填入 `owner_user_id`。
6. 可选择专门用于蒸馏的模型提供商；留空则使用触发消息所在会话的当前模型。
7. 保存配置并重载插件。
8. 在 QQ Bot 使用的配置文件中，将默认人格设为 `hwn`。

插件首次加载会把种子画像安装到 AstrBot 的本地 Skills 目录，并创建或更新同名 Persona。

### 仅安装静态人格

如果不需要自动学习：

1. 在“插件 → 技能”上传 [`hwn-astrbot-skill.zip`](astrbot-hwn/hwn-astrbot-skill.zip)。
2. 在“人格设定”中新建 `hwn` Persona。
3. 将 [`hwn-persona.txt`](astrbot-hwn/hwn-persona.txt) 的内容粘贴为系统提示词。
4. 为 Persona 选择 `hwn` Skill，并将它设为 QQ Bot 的默认人格。

## 配置

| 配置项 | 默认值 | 说明 |
|---|---:|---|
| `enabled` | `true` | 是否启用自动采集与学习 |
| `owner_user_id` | 空 | 主人 QQ 用户 ID；为空时不采集任何人 |
| `distill_provider_id` | 空 | 蒸馏模型；为空时使用当前会话模型 |
| `persona_id` | `hwn` | 自动同步的 AstrBot Persona ID |
| `batch_size` | `50` | 自动蒸馏批量，最小为 3 |
| `minimum_confidence` | `0.8` | 自动候选的最低置信度 |
| `max_message_chars` | `1000` | 单条采集文本的最大长度 |
| `auto_sync_persona` | `true` | 画像变化后是否自动刷新 Persona |

## QQ 命令

```text
/hwn help
/hwn whoami
/hwn status
/hwn distill
/hwn feedback <表达或人格纠正>
/hwn fact <本人明确确认的事实>
/hwn sync
```

除 `help` 和 `whoami` 外，其余管理命令仅允许 `owner_user_id` 对应的账号执行。

## 数据与备份

安装后运行数据位于：

```text
data/skills/hwn/
data/plugin_data/astrbot_plugin_hwn_learner/
```

其中包括原始观察记录、处理进度、最近错误和每次画像修改前的备份。这些运行数据不会包含在本仓库中。

## 开发与测试

插件使用 AstrBot 自带的 Python 环境即可测试：

```powershell
$env:PYTHONPATH="C:\path\to\AstrBot\backend\app;$PWD\astrbot-hwn"
python -m unittest discover -s astrbot-hwn\astrbot_plugin_hwn_learner\tests -v
```

当前测试覆盖消息过滤、证据阈值、处理游标、画像备份、首次安装、模型蒸馏和 Persona 同步。

## 隐私提醒

`seed_skill/hwn/self.md` 和 `persona.md` 是个人数字画像，可能包含年龄、城市、关系和表达习惯等信息。Fork、公开发布或替换为自己的画像前，请先检查并删除不希望公开的内容。

自动学习产生的 QQ 原始消息保存在本机 `data/plugin_data`，默认不会提交到 Git。
