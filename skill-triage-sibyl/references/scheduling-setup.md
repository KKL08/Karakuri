# 定时巡检接入

只在用户在 SKILL.md Step 9 明确同意「要定时巡检」后才走这一篇。

## Claude Code

让 agent 调 `CronCreate` 工具创建月度任务：

```text
CronCreate(
  name="skill-triage-sibyl-monthly",
  cron="0 9 1 * *",          # 每月 1 号上午 9 点
  prompt="请用 skill-triage-sibyl 帮我体检一次安装的 skill"
)
```

`cron` 用标准 5 字段表达式。常用频率：
- 每月：`0 9 1 * *`
- 每两周（每月 1 号和 15 号）：`0 9 1,15 * *`
- 每周一：`0 9 * * 1`

每月一次是合理的默认 —— skill 库的「卫生状态」变化不快，频率更高会打扰，更稀疏又会让新装的 skill 长时间留在描述混乱的状态。

## Codex

Codex 调度入口因安装方式不同有两条路径。

### 方式一：codex 插件已安装

```bash
codex schedule create \
  --name skill-triage-sibyl-monthly \
  --cron "0 9 1 * *" \
  --prompt "skill-triage-sibyl 月度巡检"
```

如果命令报「not found」或语法不对，说明 codex 这套调度接口未安装/不可用，走方式二。

### 方式二：写入 automations TOML

```bash
mkdir -p ~/.codex/automations
cat > ~/.codex/automations/skill-triage-sibyl.toml <<'EOF'
name = "skill-triage-sibyl-monthly"
cron = "0 9 1 * *"
prompt = "skill-triage-sibyl 月度巡检"
EOF
```

实际生效形式取决于 Codex 版本，agent 设置时如果命令失败就提示用户：「你机器上的 Codex 调度入口是哪种？我看到 `~/.codex/automations/` 不存在 / 不被读取。」

## 触发后做什么

定时触发会让 agent 重新进入 SKILL.md Step 1 → Step 9 全流程。`review_mode` 决定它能走多远：

- `report_only` → 出报告 + 通知用户审阅，不执行
- `propose_apply`（推荐） → 出报告 + 用 AskUserQuestion 提议执行；但定时场景下用户可能不在，这种情况就只出报告，等用户主动回来看
- `auto_apply`（不推荐） → 不要在定时巡检里默认启用 —— 用户不在场就执行 archive/rewrite 风险太大

实操建议：定时任务里强制走 `report_only` 行为，把报告写到 `$RUN_DIR/report.md`，并发一条简短的通知（「本月 skill 体检完成，X 项建议待审，详情见 <run-dir>」），等用户主动触发执行环节。这样既留下定时巡检的提醒，又不让定时任务自行改文件。
