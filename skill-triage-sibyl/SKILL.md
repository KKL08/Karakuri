---
name: skill-triage-sibyl
description: 为当前 agent 的 skill 库做体检，找出会让自己调用混乱的描述、统计使用频率、给出可回退的处置建议（archive / rewrite / keep / defer）。当用户提到 skill 装得太多太乱、agent 总挑错 skill、想看哪些 skill 没被用过 / 闲置 / 装了没用上、想清理冗余 skill、想检查 skill 之间定位重叠或触发边界模糊时触发——包括「我装的 skill 是不是太乱了」「skill 多得我都不记得有啥了」「agent 调错 skill 了」「不该用的 skill 又被触发」「看看 skill 使用频率」「哪些 skill 闲置」「清理没用的 skill」「skill 体检」「skill 诊断」「skill 重叠分析」「audit installed skills」「skill cleanup recommendations」「my skill library is getting messy」「trim / declutter skills」「which skills are unused」「spot-check skills」「skill overlap analysis」等表述。即使用户只是说「帮我看看我的 skill」且上下文涉及定位、重叠、触发或频率，也应触发。会扫描当前 runtime 的 skill 列表 + 本地使用频率，识别定位重叠、触发边界重叠、边界吹大、边界写小、定位缺失五类问题，所有改动有 git 快照可回退。NOT for crafting a single new skill (use skill-creator instead); NOT for reducing permission prompts (use fewer-permission-prompts).
---

# Skill Triage: Sibyl Scope

帮当前 agent 给自己的 skill 库做体检：找出会让自己调用混乱的 description，结合使用频率给出处置建议，所有改动都可回退。

## 核心原则

1. **看清再动手**：所有改动前先出报告，让用户逐项决定，不批量执行
2. **可回退优先**：任何文件改动都有 git 快照 + 内容哈希双重兜底
3. **尊重用户判断**：上次被用户明确选成 keep 的 skill，本次同等条件下不再提
4. **只看当前 runtime**：只扫当前 agent 自己看到的 skill 空间，不跨 runtime

## 工作流

下面命令里 `SKILL_ROOT` 替换为本 skill 目录的绝对路径，`RUN_ID` 用 `YYYY-MM-DD-HHMMSS` 形式的时间戳，`RUN_DIR` 用 `$CLAUDE_PLUGIN_DATA/skill-triage-sibyl/runs/$RUN_ID/`。

### Step 0 · 首次使用引导

Run:

```bash
PYTHONPATH=$SKILL_ROOT/scripts python3 -c "from sibyl.config import is_first_run; print('first' if is_first_run() else 'returning')"
```

如果返回 `first`，用 AskUserQuestion 一次性确认两件事：

- **巡检模式**：仅出报告 / 出报告后让我提议执行（推荐）/ 报告后自动执行（不推荐）
- **节奏**：手动触发 / 每月一次

把结果写入 `$CLAUDE_PLUGIN_DATA/skill-triage-sibyl/config.json`，`onboarding_completed_at` 设为当前时间。后续触发跳过这步。

### Step 1 · 识别当前 runtime

你最清楚自己在哪个 agent 里跑：Claude Code → `--runtime claude-code`，Codex → `--runtime codex`。如果上下文不明确，问一次用户。

### Step 2 · 采集事实

```bash
mkdir -p "$RUN_DIR"
PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.inventory --runtime $RUNTIME --output $RUN_DIR/inventory.json
PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.usage --runtime $RUNTIME --inventory $RUN_DIR/inventory.json --window-days 30 --output $RUN_DIR/usage.json
```

先读 `references/usage-interpretation.md` 搞清调用次数怎么算进判断，再去看两份 JSON。

### Step 3 · 读偏好

读 `$CLAUDE_PLUGIN_DATA/skill-triage-sibyl/preferences.json`（不存在就当空）。按 `references/preference-merge.md` 的规则筛出仍生效的条目；那里写明了五类诊断各自的失效判定。description_hash 未变的 `user_kept` 是最强信号 —— 这类 skill 这轮直接跳过。

### Step 4 · Agent 诊断（两层筛选）

诊断分两层做：第一层粗扫挑候选，第二层精读做判断。两层都是你（agent）来做，区别在深度。这样既不浪费 token 给每对 skill 都做深入分析（91 个 skill 两两就 4000+ 对），也避免一轮粗筛下结论的偏见。

读 `references/diagnosis-rubric.md` 拿到五类问题的判定细则。

**Layer 1 · 候选筛选（粗扫）**

把 `inventory.json` 里所有 skill 的 description 全文摆进 context，按以下三个维度做 mental 分组：

- **服务对象**（飞书 / 本地文件 / 网络 / 代码仓库 / 媒体 / ...）
- **主要动词**（管理 / 生成 / 搜索 / 改写 / 体检 / ...）
- **触发场景**（用户在什么情景下会自然想到它）

输出候选清单：
- 哪几组 skill 落在同一「服务对象 + 主要动词」语义簇（potential positioning_overlap）
- 哪几对触发场景词显著相交（potential trigger_boundary_overlap）
- 哪些 description < 60 字或全是宽泛词（potential positioning_unclear）
- 哪些 description 用「manages all / supports many / handles various」这类大词（potential boundary_inflation）

这一步只做粗判，不要给最终结论，也不要 Read 完整 SKILL.md。被 `user_kept` 偏好且 hash 未变的 skill 在这层就排除掉，不进 Layer 2。

**Layer 2 · 候选深入（精读）**

对 Layer 1 标出的每组候选，做实质判断。按需 Read 完整 SKILL.md —— 特别是 boundary_inflation / boundary_deflation 必须读 body（body_snippet 600 字看不全）。

每条诊断按下面**固定四段式**写，**判断 → 证据 → 推荐动作 → 原因**（顺序不能乱）：

1. **判断**：问题类型（五类之一）+ 涉及的 skill_id + 使用频率摘要（从 usage.json 取）
2. **证据**：引用 description / body 里的具体短语
3. **推荐动作**：archive / rewrite / keep（中文写出来，给用户最直观）
4. **原因**：为什么这么推荐

「推荐动作」和「原因」是给用户看的核心信息 —— 用户决定怎么处置就靠这两条。不要藏在长段落里，必须独立成行、加粗标出。

**关键判断**：「相似 ≠ 混淆」。两个 skill 在服务对象、数据来源、运行时、provider、任务阶段任一维度上有清晰边界，agent 拿到具体请求仍能挑对 —— 判 keep + 报告里标「已确认无混淆」，不要列进 overlap。

### Step 5 · 写报告

按 `templates/report.md` 填，写到 `$RUN_DIR/report.md`。措辞要明确，同时给用户留改判余地，参考 `references/action-flow.md`。

### Step 6 · 与用户对齐决定

用 AskUserQuestion 让用户逐项选 archive / rewrite / keep / defer（多 skill 一轮多选）。

**rewrite 的额外要求**：如果 skill 出现在某条 `positioning_overlap` 诊断里，起草新 description 时把这条 overlap 涉及的所有对手 description 一起读进来，用「Use when X. NOT when Y / Z (use sibling A / sibling B instead)」的互斥句式。起草完先把 diff 给用户看，二次确认再执行。

**同组 `positioning_overlap` 涉及 ≥ 3 个 skill 时的合并提问**（详见 `references/action-flow.md` 的 N+ overlap 章节）：

1. AskUserQuestion 一次性问场景区分：「其实重复 / 有场景区分 / 暂时不决定」
2. 「其实重复」 → 按使用频率推荐保留次数最多的一个，其余整批走 archive 的二次确认
3. 「有场景区分」 → 对组内每个 skill 都走 rewrite + 互斥要求；先整组 diff 给用户看互斥措辞自洽，再逐个二次确认 + apply
4. 「暂时不决定」 → 整组 defer，本次不写偏好

不主动建议做「统一入口的 router skill」。用户主动问时再解释代价（多一跳、维护翻倍、可能拖累命中率），交给用户判断。v1 不直接创建 router。

### Step 7 · 执行（仅 review_mode != report_only 时）

逐项执行，每次先在脑子里 dry-run 一遍：要 mv 哪个目录、要覆盖哪个文件，再发命令。回退语义见 `references/rollback-model.md`。

```bash
# archive
PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.apply archive --run-id $RUN_ID --skill-path <path> --runtime $RUNTIME

# rewrite
echo -n "$NEW_TEXT" > $RUN_DIR/proposed-<name>.md
PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.apply rewrite --run-id $RUN_ID --skill-md-path <skill_md> --new-text-file $RUN_DIR/proposed-<name>.md
```

完成后写 `$RUN_DIR/decisions.json`，记录每项 `recommended_action` vs `user_choice` 的对照。

### Step 8 · 沉淀偏好

把「建议被驳回」和「建议被采纳」的信号 append 到 `preferences.json`。每条 entry 必须带 `diagnosis_type` 和对应的 at_decision 字段（见下表，漏填会让下次失效检测算错）：

| diagnosis_type | 必填 at_decision 字段 |
|---|---|
| positioning_unclear / trigger_boundary_overlap | description_hash_at_decision |
| boundary_inflation / boundary_deflation | description_hash_at_decision、version_at_decision、body_word_count_at_decision、body_h2_count_at_decision（都从本次 inventory.json 取） |
| positioning_overlap | description_hash_at_decision、adversaries_at_decision（同组所有对手的 skill_id + description_hash） |

`signal` 取 `user_kept`（最强信号 —— 建议清理但用户保留）/ `user_archived` / `user_rewrote` / `user_deferred`。

```python
from sibyl import preferences
preferences.append([entry, ...])  # 按四元组去重 + 累加 occurrences
```

### Step 9 · 收尾

告诉用户：

- run 目录路径
- 回退命令：`PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.apply rollback --run-id <run-id>`
- 若 `config.schedule` 仍是 manual 且本次是第 2 次或更晚的运行，问一次「要不要每月自动巡检一次」。同意则按 `references/scheduling-setup.md` 给的命令设置（Claude Code 用 CronCreate，Codex 用 codex schedule create 或 automations toml）

## 什么时候不该用

- 想从头打磨单个 skill 的写法 → 用 `skill-creator`
- 想减少 Claude Code 权限弹窗 → 用 `fewer-permission-prompts`
- 想看 skill 调用日志细节、调试单次 trigger 失败 → 这是 debug 任务，不是体检

## 安全边界

| 场景 | 建议做法 | 原因 |
|---|---|---|
| 插件托管 skill（`managed: true`） | 只生成建议，不直接 archive/rewrite | 插件下次更新会覆盖本地改动；正确做法是去插件源 fork 或反馈给维护者 |
| 项目级 skill（`.claude/skills/` 在项目内） | 提示用户「这是项目内 skill，改动会影响协作者」 | 团队共享的 skill 改动属于团队决定，不该由单机巡检自行处理 |
| 自身 skill（skill-triage-sibyl） | 跳过，不对自己做诊断 | 避免循环；要测试本 skill 走 `skill-triage-sibyl/tests/` 下的单元测试 |
| 用户在执行后手动改过文件 | rollback 时报 conflict、不覆盖；用户加 `--force` 才覆盖 | 默认保护用户的手工修改 |

## 进一步阅读

- `references/diagnosis-rubric.md` —— 五类问题的判定信号、正例反例
- `references/usage-interpretation.md` —— 调用次数与近期窗口怎么用
- `references/preference-merge.md` —— 偏好怎么读怎么写、三档失效规则
- `references/action-flow.md` —— archive / rewrite / keep / defer 的措辞与 N+ overlap 子流程
- `references/rollback-model.md` —— 快照与冲突检测语义
- `references/scheduling-setup.md` —— 定时巡检接入命令
