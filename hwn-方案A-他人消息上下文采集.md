# hwn 学习器 · 方案 A（他人消息作为语境）规格与待办

- 记录时间：2026-09-26 18:18 (CST)
- 涉及插件：`astrbot_plugin_hwn_learner`
- **当前决定：暂不实施。** 平台侧拿不到「群消息全量接收」权限，方案收益接近零，代码保持原样。
- 本文用途：留档 + 待拍板清单。下次重启该议题时按此文档执行。

---

## 一、目标

让蒸馏能利用**他人消息作为语境**来消歧（例如判断 hwn 的一句攻击性表达是熟人互损还是真发火），
但**绝不把他人消息当作 hwn 本人表达习惯的证据**，避免污染画像。

---

## 二、关键约束（先读懂这三条，再谈方案）

### 约束 1：平台层只推 @ 消息

qq_official 适配器（`astrbot/core/platform/sources/qqofficial/qqofficial_platform_adapter.py`）注册的群消息入口：

| 事件 | 含义 | 当前是否生效 |
|---|---|---|
| `group_at_message_create` | 群内被 @ 才推送 | ✅ |
| `group_message_create` | 群消息全量接收 | ❌ 需 app 级「群消息」权限，未获得 |
| `c2c_message_create` | 私聊 | ✅ |

结论：**没 @ 的群消息根本不会产生事件**，插件层无法捕获。
已排除：QQ 开放平台的「添加协作者」属于应用管理层，不改变机器人能收到哪些事件。

### 约束 2：非 @ 群消息不会触发 LLM

`WakingCheckStage` 中 `is_at_or_wake_command` 只在三种情况置 True：

1. 命中唤醒前缀（当前 `wake_prefix = ["/"]`）
2. 被 @ / 被 @全体 / 被引用回复
3. 私聊（`friend_message_needs_wake_prefix = false`）

没有「群消息始终唤醒」这类配置项。
插件注册的 ALL 处理器会让 `is_wake = True`，但**不会**让 `is_at_or_wake_command` 变 True，
而 `ProcessStage` 调用 LLM 的前提是 `is_at_or_wake_command`。

结论：即使约束 1 解决，非 @ 群消息也**不会**触发 LLM 请求。

### 约束 3：当前采集挂在 `on_llm_request` 上

`capture_owner_message` 用 `@filter.on_llm_request(priority=10)` 注册，所以：

- 只有「触发 LLM 请求」的消息才会被采集
- 且当前有 `_is_owner(event)` 判断，他人消息直接被过滤掉

---

## 三、方案 A 规格（供确认，尚未实施）

### A1′ 采集点不换（已确认）

保持 `on_llm_request`。因此可采集的集合是：

| 消息 | 是否入库 | is_self |
|---|---|---|
| 主人 @ 机器人 | ✅ | true |
| 他人 @ 机器人 | ✅（需 `capture_others: true`） | false |
| 主人裸关键词（被 `keyword_command` 截走） | ❌ 不入库 | — |
| `/hwn ...` 命令 | ❌ 被 `normalize_message` 挡掉 | — |

### A2′ 上下文来源

从观察池按 `umo` 回溯最近 N 条 `is_self = false` 的消息，写入 `context_before`。

- 优点：自包含、语义清晰、不依赖 AstrBot 内部结构
- 缺点：池内只有「触发过 LLM 的消息」，上下文覆盖不全

### A3′ 数据模型（`observations.jsonl`）

```json
{"at": "...", "umo": "...", "message_id": "...",
 "is_self": false, "text": "帮我看看这个",
 "context_before": ["...", "..."]}
```

- 新增 `is_self`、`context_before`
- 向后兼容：旧条目无 `is_self` 字段时按 `true` 处理
- 不记录昵称、sender_id、头像等身份信息

### A4′ 蒸馏与硬校验

prompt 写死三条：

1. 只能从 `self: true` 的条目提炼候选
2. `context_before` 仅用于判断语气与场景，不得据其提炼任何规律
3. `evidence_indexes` 必须全部指向 `self: true` 的条目

`validate_traits` 增加硬校验：证据里只要有一条 `is_self = false`，整条候选丢弃。
原有门槛不变：至少 3 条**不同**本人消息、置信度 ≥ `minimum_confidence`（0.8）。

自动蒸馏触发条件改为：`pending` 中 `is_self = true` 的条数 ≥ `batch_size`（他人在池中只当语境，不计数）。
`processed` 游标语义不变（按总条数推进）。

### A5′ 配置项

| 键 | 默认 | 含义 |
|---|---|---|
| `capture_others` | `false` | 是否采集他人消息（关闭时行为与现状完全一致） |
| `context_window` | `5` | 每条本人消息附带的他人消息条数，0 表示关闭 |

### A6′ 改动文件

| 文件 | 改什么 |
|---|---|
| `learner.py` | `ObservationStore.append` 加字段；上下文配对；`build_distillation_prompt` 改 self/context 两栏；`validate_traits` 加 self 校验 |
| `main.py` | 采集逻辑按 `is_self` 分支；两个新开关；蒸馏触发计数改法 |
| `_conf_schema.json` + 配置文件 | 加 `capture_others`、`context_window` |
| `README.md` / `CHANGELOG_LOCAL.md` | 文档同步 |
| `tests/` | 他人消息不进候选、证据必须 self、旧条目兼容、上下文配对、`capture_others=false` 时行为不变 |

### A7′ 明确不做

- 他人消息永不写入 `persona.md` / `self.md`
- 他人消息永不作为候选证据（任何路径）
- 不采集白名单会话之外的消息

---

## 四、已确认项（2026-09-26）

- [x] 采集触发点**不换**，保持 `on_llm_request`
- [x] 关键词消息被 `keyword_command` 截走，不入库，不为此改动
- [x] `capture_others` 默认 `false`
- [x] `context_window = 5`
- [x] 接受他人消息以纯文本形式落盘在 `observations.jsonl`
- [x] 平台权限不来 → 本方案暂缓，代码不动

---

## 五、待拍板（若日后重启）

1. **他人消息的采集路径**
   加一条「只记他人」的 ALL 记录处理器（推荐，权限一旦开通即可吃到料）／
   坚持不碰 ALL（等价于放弃该方案，因为约束 2 决定了 `on_llm_request` 采不到非 @ 消息）
2. **上下文来源**
   观察池回溯最近 5 条 `is_self=false`（推荐）／`context_window = 0`，只留接口
3. **实施时机**
   现在就实施（`capture_others` 默认 false，零行为变化，推荐）／等权限落实再动手
4. **`distill` / `help` 是否也加裸关键词**
   建议不加（`distill` 会真烧一次模型调用）
5. **非主人的 `/hwn status` 等子指令**
   加 permission 过滤静默跳过 ／ 维持现状（回一句「只有配置的主人账号可以执行这个命令」）
6. **是否把本文档并入插件 `docs/`**（当前只放在桌面，未入库）

---

## 六、待操作

- [ ] **重载插件**（重要，尚未完成）
      当前运行实例仍是 17:33 那版，以下改动都还没生效：
      裸关键词触发（`feedback/fact/whoami/status/sync`）、`/hwn` 硬过滤（`HWN_COMMAND_PATTERN`）、
      蒸馏提示词里的 `/hwn` 忽略规则、`/hwn status` 的采集范围显示
- [ ] ~~申请 QQ 开放平台「群消息」权限~~ → 已判定拿不到，关闭
- [ ] 若将来迁移到 aiocqhttp 类适配器，约束 1 自动解除，方案 A 可随时启动

---

## 七、放弃 / 备选路径（留档）

| 方案 | 内容 | 结论 |
|---|---|---|
| 方案 B | 他人消息也进候选证据池 | 放弃：污染画像，不可逆，且把舍友口癖学成 hwn 的风险高 |
| 方案 C | 把画像目标改成「hwn + 熟人圈共同语境」 | 放弃：超出「本人数字镜像」的定位 |
| 换触发点 | 采集改挂 `EventMessageType.ALL` | 放弃：会打破现有「只记主人、关键词不入库」的语义 |
| 换适配器 | aiocqhttp / NapCat 类协议端 | 备选：能收全部群消息，但需要迁移平台配置 |

---

## 八、隐私提醒

群友并未同意自己的发言被用于画像训练。方案 A 虽然只把他人消息当语境、不写进 skill 文件，
但确实是**他人发言落盘到本地**。实施前请自行评估并决定。

---

## 九、基线快照（2026-09-26 18:18）

- `skills/hwn/`：`meta.json` v4，`corrections_count` 0；`persona.md` 的 Correction 记录为「暂无」；
  `self.md` 有 1 条用户确认事实（电竞赛事偏好）
- 观察池：`observations.jsonl` 0 字节，`state.json` `0 / 0`
- 采集白名单：1 个会话 `b猫bot:GroupMessage:FC4B8DA460A4FF8C86BFF04B338CEA07`（b猫bot养成群）
- 配置项：`enabled / owner_user_id / session_whitelist / distill_provider_id / persona_id /
  batch_size(200) / minimum_confidence(0.8) / max_message_chars(1000) / backup_keep(100) / auto_sync_persona`
- 已移除：`auto_feedback_prefix`（「人格更新：」前缀触发）
- 已入库但未生效（待重载）：裸关键词触发、`/hwn` 采集硬过滤、蒸馏提示词 `/hwn` 忽略规则
