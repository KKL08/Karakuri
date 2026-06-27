# Skill Triage: Sibyl Scope · 体检报告

> Run ID：{{run_id}}　Runtime：{{runtime}}　扫描时间：{{scanned_at}}

## 一、需要你决定的项

每条按**判断 → 证据 → 推荐动作 → 原因**四段式呈现。「推荐动作」「原因」是你决定时最关键的两个字段，必须独立成行加粗。

写法约定：

- **标题**带使用频率，让用户一眼看到这 skill 用得多不多：`### N. <skill-name>（30 天 X 次 / 全期 Y 次）`
- **证据**用 `>` 嵌套引用 description / body 原文，论述和引文分开
- **推荐动作**默认给单一推荐；只有当两个方案都合理且依赖用户偏好时，给「主推 + 备选」结构
- **原因**尽量叠加多重信号：使用频率、文本证据、外部上下文（社区维护活跃度、是否插件托管、用户历史决策、版本迁移情况等）。一句话的原因往往不够。

示范条目：

> ### 1. `<skill-name>`（30 天 X 次 / 全期 Y 次）
>
> **判断**：positioning_overlap，与 `<sibling>` 服务对象与主要动词重合。
>
> **证据**：
> > `<skill-name>` description：「...」
> >
> > `<sibling>` description：「...」
> >
> > 两者都覆盖「<重叠关键短语>」。
>
> **推荐动作**：archive `<skill-name>`，保留 `<sibling>`。
>
> **原因**：① 调用数据看，`<sibling>` 30 天 Y 次活跃、`<skill-name>` 长期 0；② description 主要动词完全重合（「<动词>」）；③ `<sibling>` 由插件社区维护，更新频次更高；保留两份让 agent 持续混淆。

{{decision_items}}

## 二、保留无需处理

{{kept_items}}

## 三、扫描概况

- 扫描到 skill 总数：{{total}}
- 30 天内有调用：{{used_30d}}
- 30 天 0 调用：{{idle_30d}}
- 长期 0 调用（90+ 天）：{{long_idle}}
- 上次用户已保留（本次按偏好跳过）：{{respected_preferences}}

## 四、回退

如需撤销本次执行：

```bash
PYTHONPATH={{skill_root}}/scripts python3 -m sibyl.apply rollback --run-id {{run_id}}
```

冲突文件会列出，需要 `--force` 才覆盖。
