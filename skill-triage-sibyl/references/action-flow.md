# 动作流程：archive / rewrite / keep / defer

四种用户选项，每种都有明确的措辞规范、流程要求和回退路径。

## archive

**措辞**：报告里写「建议归档（保留备份，需要时可回退）」，不要写「删除」。删除会让用户警觉，归档传达的是「目录被移到 archive 区、agent 不再发现、要的时候可以一键回来」，更准确。

**执行**：

```bash
PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.apply archive \
  --run-id $RUN_ID --skill-path <skill_path> --runtime $RUNTIME
```

skill 目录被搬到 `$CLAUDE_PLUGIN_DATA/skill-triage-sibyl/archive/<run-id>/<runtime>/<basename>/`，目录内写一份 `_sibyl_origin.json` 记录原始路径。

**适用场景**：长期 0 调用 + 定位被另一个 skill 完全覆盖；或定位缺失到无法挽救。

## rewrite

**通用流程**：起草 → diff → 二次确认 → apply。diff 必须给用户看，不能跳过。

**起草约束**：

- description 不超过 1024 字符
- 遵循 Anthropic skill 规范的 frontmatter 写法
- 解释清楚 what + when，避免宽泛词

**overlap 互斥要求（关键）**：

如果 skill 出现在某条 `positioning_overlap` 诊断里，起草新 description 时必须把所有 overlap 对手的 description 一起读进来，用：

> Use when X. NOT when Y / Z (use sibling A / sibling B instead).

这种互斥句式让 agent 一眼看清边界。这条要求不分 2 元还是 N 元 overlap，统一适用。

**执行**：

```bash
echo -n "$NEW_TEXT" > $RUN_DIR/proposed-<name>.md
PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.apply rewrite \
  --run-id $RUN_ID --skill-md-path <skill_md> --new-text-file $RUN_DIR/proposed-<name>.md
```

apply.rewrite 会先 keeper.snap 原文件（拿到 pre_commit）、再写新内容、记下 post_content_hash —— 这两个值让后续 rollback 能做 hash 一致性校验。

## keep

**适用场景**：只是被 Layer 1 粗扫挑出来、但 Layer 2 精读后确认无混淆风险。

**记录方式**：keep 也是有效信号 —— 它告诉下次扫描「这个推荐被用户驳回过」。报告里要在「**原因**」字段里说明 keep 的依据（例：「虽然 description 和 X 共享一些 token，但服务对象 / 触发场景已经分干净」），这样 reviewer 能跟着思路审。

## defer

**适用场景**：用户暂时不想决定。

**处理**：本次不写偏好（也不沉淀 `user_deferred` 记录到 preferences，因为没有任何「决定」可记），下次扫描重新评估、重新提。

## N+ overlap 合并提问子流程

当一组 `positioning_overlap` 涉及 ≥ 3 个 skill 时，不要逐 pair 问，先 AskUserQuestion 一次性问场景区分：

| 用户回答 | 后续动作 |
|---|---|
| 其实重复 | 按使用频率推荐保留次数最多的一个，其余整批走 archive 的二次确认 |
| 有场景区分 | 对组内每个 skill 都走 rewrite + 互斥要求；先**整组 diff 给用户看互斥措辞自洽**，再逐个二次确认 + apply |
| 暂时不决定 | 整组 defer，本次不写偏好 |

合并提问只是 UX 决策 —— 没有引入新的诊断类型，也没有新的执行动作，还是走 `positioning_overlap` + archive/rewrite。

### 关于 router skill

**不主动建议**做「统一入口的 router skill」。原因：router 本身要抢第一跳触发，等于多塞一个候选去跟 archive/rewrite 后已经写清的 description 抢命中 —— 通常拖累命中率而不是改善。

用户主动问「要不要做一个 router」时再解释代价：
- 多一跳（agent 第一跳命中 router → 再跳到具体 skill → 多一段 context、多一次工具调用）
- 维护翻倍（router 描述要随子 skill 描述同步更新）
- 可能拖累命中率（router 本身就是一个新的「边界夸大」候选）

把决定权交给用户。v1 不直接创建 router skill 文件，这是边界。

### 完整正例

设想 5 个 lark 邮件相关 skill：`lark-mail-send` / `lark-mail-search` / `lark-mail-rules` / `lark-mail-attachments` / `lark-mail-monitor`。description 都涉及「飞书邮件」，Layer 1 粗扫按服务对象 + 主要动词把它们聚成一组。

合并提问 → 用户回答「有场景区分」（确实是发邮件、搜邮件、规则、附件、监听五个不同任务）。

走 rewrite 时给每个起草新 description，互斥句式：
- `lark-mail-send`: "Use when sending / replying / forwarding email via Lark. NOT for searching, attachment download, mail rules, or monitoring (use lark-mail-search / lark-mail-attachments / lark-mail-rules / lark-mail-monitor instead)."
- 其他四个同构

整组 diff 给用户看一遍互斥措辞，再逐个确认 + apply。

### 完整反例

三个 skill `chart-renderer` / `data-summarizer` / `report-writer`，description 都提「数据可视化」。Layer 1 粗扫聚成一组。

合并提问 → 用户回答「有场景区分，但更深一层」。读各自 SKILL.md：`chart-renderer` 是把 CSV 渲染成图、`data-summarizer` 是统计聚合、`report-writer` 是组合多段输出成 PDF。三者服务的任务阶段完全不同（呈现 / 计算 / 出稿）。

正确判断 → keep + 报告里标「已确认无混淆」，不走 rewrite。Layer 1 把它们拉一起只是因为表层主题词「数据可视化」相同，Layer 2 精读后看出任务阶段完全不同，不构成真混淆。
