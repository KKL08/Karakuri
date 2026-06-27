# 诊断手册：五类问题怎么判

每条 skill 至多挂一类诊断结论。写进 report.md 时按**固定四段式**呈现，顺序不能乱：

1. **判断** —— 问题类型 + 涉及的 skill
2. **证据** —— 从 description / body 里引证原文短语
3. **推荐动作** —— archive / rewrite / keep
4. **原因** —— 解释为什么这么推荐

「**推荐动作**」和「**原因**」是用户面前最关键的两个字段 —— 用户拍板靠它俩。必须独立成行、加粗、用中文标签（不写「why」「recommend」这种英文）。

## positioning_overlap（定位重叠）

**判定信号**：两个或更多 skill 的服务对象 + 主要动词落在同一语义簇。Layer 1 的粗扫挑出候选，Layer 2 精读时你必须主动核对：服务对象是不是真的同一个、主要动词是不是真的重叠。同前缀 / 同主题词不等于同语义簇。

**证据要求**：列出涉及的所有 skill_id、共同的关键短语、各自现在已经写明的差异点（如果有）。

**正例**：
- `lark-mail` 和 `mail-helper` 都说「管理 / 发送 / 整理邮件」，服务对象都是邮箱场景，差异点不明显 → overlap
- `lark-doc`、`lark-wiki`、`obsidian-vault` 三个都说「管理 / 创建 / 查找笔记/文档」，但服务对象不同（飞书云文档 vs 飞书知识库 vs 本地 Obsidian）—— 这里要看 description 有没有把服务对象写清。如果写清了 → keep；如果三个都只说「管理文档」没说在哪 → overlap

**反例**（看起来像但其实不是）：
- `coding-music` 和 `lark-mail` 都有「自动」 / 「提醒」类关键词，但服务对象（音乐 vs 邮件）和动词（暂停/恢复 vs 发送/回复）完全不同 → 不是 overlap

**3+ 成员的合并提问**：同一组 overlap 涉及 ≥ 3 个 skill 时，不要逐 pair 问，按 `action-flow.md` 的 N+ overlap 子流程一次性问「重复 / 有场景区分 / defer」。注意：v1 不引入「簇」作为独立诊断类型 —— 3+ 只是 UX 决策，数据上还是 `positioning_overlap`。你可以拒绝把弱相关项拉进同一组，也可以让同一 skill 在不同组里出现。

## trigger_boundary_overlap（触发边界重叠）

**判定信号**：两个 skill 的「什么时候用」短语集合显著相交。description 里的"when X / when Y"句式覆盖到对方的场景。

**证据要求**：列出共同触发词 + 各自独占触发词。

**正例**：A 写 "use when user wants to summarize a meeting"，B 写 "use when user wants meeting notes"。两边都覆盖"meeting"语境，触发词重叠 → overlap

**反例**：A 写 "use when user wants daily standup report"，B 写 "use when user wants quarterly review"。都是「会议总结」语义，但触发词（daily/quarterly）把场景拆得很清 → keep

## boundary_inflation（边界吹大）

**判定信号**：description 的触发面 > SKILL.md 正文实际能力。

**证据要求**：引证 description 中过宽的短语 + 正文中真实的能力上限。

**正例**：description 写 "manages all PDF operations including OCR, signature, form-filling, page extraction"，但正文只有 "open PDF in viewer" —— OCR / signature / form-filling 都不存在 → inflation

**反例**：description 写 "PDF viewer with annotation"，正文有 `viewer.py` + `annotate.py` 两套实现 → 完全覆盖，keep

## boundary_deflation（边界写小 / 写漏）

**判定信号**：description 涵盖面 < body 实际能力。Agent 看不到能力就不会调，能力被埋没。

这类问题比 inflation 难发现 —— description 没有「过宽词」当视觉信号。判定时必须 Read 完整 SKILL.md（body_snippet 600 字看不全），重点找正文里 description 没提到的能力章节。

**判定信号清单**：
- description 长度短但 calls_total 非 0（说明用过，但用得少 —— 可能是 agent 看不到全部能力）
- 正文有大量 `## 功能` / `## 能力` 章节但 description 里没对应短语
- 正文出现「也可以 / 还能 / 支持」开头的能力清单，description 完全没引

**证据要求**：引证正文里能做但 description 没提的能力 + description 现状。

**正例**：description 写 "Send emails via Lark"，正文有 `## 起草` / `## 回复` / `## 转发` / `## 搜索` / `## 标签管理` 五大节 —— description 只覆盖发送，剩下四档全藏起来了 → deflation

**反例**：description 写 "Lark mail end-to-end management"，正文同样五大节 —— description 用"end-to-end"概括到位 → keep

## positioning_unclear（定位缺失）

**判定信号**：description 缺少明确的"what + when"，或者长度 < 60 字，或者全是宽泛词（"help with X" / "manage Y" 而没具体场景）。

**证据要求**：列出缺失的要素（服务对象 / 动作 / 触发场景 / 与近邻 skill 的差异）。

**正例**：description 只写 "A useful tool for data" —— 无对象（哪种数据）、无场景（什么时候）、无差异化 → unclear

**反例**：description 写 "Format JSONL session logs to readable tables; use when the user shares a session export and wants to inspect tool calls" —— 对象（JSONL session）、动作（format → table）、场景（user shares export）都齐 → keep

## 「相似 ≠ 混淆」 原则

description 相似不等于会让 agent 调错。如果两个相似 skill 在**服务对象、数据来源、运行时、Provider、任务阶段**任一维度上有明确边界，agent 拿到具体请求时仍然能挑对 —— 这种情况判 keep，不要列进 overlap。

举例：`lark-mail` 和 `obsidian-vault` 都「管理文本」，但前者是飞书邮箱、后者是本地 Obsidian vault；用户问「看下我的邮件」和「看下我的笔记」时 agent 不会搞混。这种 description 即使共享一些 token（「管理 / 查看 / 整理」），也不构成混淆，判 keep，报告里标「已确认无混淆」。
