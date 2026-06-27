# Skill Triage: Sibyl Scope

[English](./README.en.md)

为安装了大量 skill 的 Claude Code / Codex agent 做 description 质量巡检。

## 解决什么问题

装了几十个 skill 之后，agent 的「调对率」会肉眼可见地往下掉：

- 两个 skill 描述太像，agent 二选一靠运气
- 某 skill description 吹得过宽，把不该接的请求接了
- 某 skill 实际能力比 description 写得多，agent 看不见、永远调不到
- 装了忘了用，长期 0 调用躺着
- description 太短没说清「什么时候用」，agent 直接想不起它

## 核心功能

- **五类语义诊断**：agent 直接读 description 全文做语义判断，不靠 token 字面相似度。同义词、长短不对称、命名空间前缀稀释这些字面匹配抓不到的问题，语义判断一轮就能发现。
- **两层筛选**：粗扫挑候选，精读做判断。既省 token，又避免一轮粗扫就下结论。
- **报告四段式**：每条诊断按 **判断 → 证据 → 推荐动作 → 原因** 呈现。「推荐动作」和「原因」加粗独立成行，是你拍板时最关键的两个字段，不藏在长段落里。
- **跨次偏好记忆**：你拒绝过的清理建议下次自动跳过。description 或正文有实质变化时偏好自动失效，重新评估。
- **完整可回退**：git 快照 + 内容哈希双重兜底，archive / rewrite 都能一键 rollback；冲突文件默认不覆盖，要 `--force` 明示。
- **stdlib only**：Python 标准库 + 系统 git，无第三方依赖。

## 安装

```bash
# Claude Code
git clone https://github.com/KKL08/Karakuri.git
cp -r Karakuri/skill-triage-sibyl ~/.claude/skills/

# Codex
cp -r Karakuri/skill-triage-sibyl ~/.codex/skills/
```

需要 Python 3 标准库 + 系统 git。无第三方依赖。

## 用法

在 Claude Code 或 Codex 里说：

```
帮我体检一下安装的 skill
```

或者直接：

```
用 skill-triage-sibyl
```

## 名字与灵感来源

名字来自《PSYCHO-PASS 心理测量者》里的 **Sibyl System**。原作中 Sibyl System 扫描市民的心理状态，按犯罪系数分档处置。Sibyl Scope 借用了同样的范式 —— **扫描 → 量化 → 分档处置** —— 扫描所有 skill 的 description 质量，按五类问题诊断，给出 archive / rewrite / keep 的处置建议。

跟原作不同的是：**决定权在你**。Sibyl Scope 出报告、给建议，archive / rewrite 必须你逐项确认才执行，所有动作可一键回退。

## 工作流

触发后你会经历这几步：

1. 首次使用时确认巡检模式和节奏
2. 自动扫描当前所有 skill 和 30 天调用频率
3. 看诊断报告，逐项选择 archive / rewrite / keep / defer
4. 确认后执行（archive 搬目录 + 写来源记录；rewrite 先快照再覆盖）
5. 可选：设月度自动巡检

每一步都需要你确认，不会跳过确认直接执行。

## 直接跑脚本

不走 agent，直接看一份事实清单也行：

```bash
SKILL_ROOT=~/.claude/skills/skill-triage-sibyl
RUN_DIR=~/sibyl-test/runs/$(date +%Y-%m-%d-%H%M%S)
mkdir -p $RUN_DIR

PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.inventory \
  --runtime claude-code --output $RUN_DIR/inventory.json

PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.usage \
  --runtime claude-code --inventory $RUN_DIR/inventory.json \
  --window-days 30 --output $RUN_DIR/usage.json
```

`inventory.json` + `usage.json` 是纯数据，你自己就能看；诊断建议得交给 agent 读完它们再生成。

## 回退

任何执行过的 archive / rewrite 都可以一键回退：

```bash
PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.apply rollback --run-id <run-id>
```

回退会做内容哈希一致性检查 —— 如果你在执行后手改过文件，默认不覆盖；想强制覆盖加 `--force`。

## 数据保存位置

```
$CLAUDE_PLUGIN_DATA/skill-triage-sibyl/         # 默认 ~/.claude/plugin-data/skill-triage-sibyl/
├── config.json                # 首次引导的模式 / 节奏
├── preferences.json           # 跨次累积的用户偏好
├── runs/<run-id>/
│   ├── inventory.json
│   ├── usage.json
│   ├── report.md
│   └── actions.jsonl          # 已执行的动作日志，rollback 倒序读
├── keeper/repo/               # 内部 git 仓库，rewrite 前的文件快照
└── archive/<run-id>/<runtime>/<skill-name>/   # 被归档的 skill 目录
```

## 偏好怎么影响下次扫描

偏好不等于授权 —— 它只决定「下次还提不提」。当 description 或正文有实质变化时，对应的偏好自动失效，下次扫描会重新评估。不同诊断类型的失效条件不同，详见 [`references/preference-merge.md`](./references/preference-merge.md)。

## 安全边界

- 插件托管 skill 默认只生成建议，不直接 archive/rewrite（避免被插件更新覆盖）
- 项目级 skill 改动前会提醒「这会影响协作者」
- 不对自己（skill-triage-sibyl）做诊断 —— 想验证本 skill 走 `tests/`
- 默认尊重用户手动改动 —— rollback 时哈希不一致会报 conflict，要 `--force` 才覆盖

## 进一步阅读

- [`SKILL.md`](./SKILL.md) —— agent 跑的工作流
- [`references/diagnosis-rubric.md`](./references/diagnosis-rubric.md) —— 五类问题怎么判
- [`references/preference-merge.md`](./references/preference-merge.md) —— 偏好规则
- [`references/action-flow.md`](./references/action-flow.md) —— archive / rewrite / keep / defer 措辞与流程
- [`references/rollback-model.md`](./references/rollback-model.md) —— 回退语义
