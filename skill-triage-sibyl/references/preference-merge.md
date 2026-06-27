# 偏好怎么读怎么写

偏好（`preferences.json`）记录用户上次对每条诊断的最终选择，让下次扫描跳过「已被驳回」的建议，避免重复打扰。**偏好只影响「该不该再提议」，不影响当次扫描结果和诊断本身。**

## 写入：每条 entry 必须带 diagnosis_type + 对应字段

漏填 at_decision 字段会让下次失效检测算错。按诊断类型对照下表：

| diagnosis_type | 必填 at_decision 字段 |
|---|---|
| positioning_unclear / trigger_boundary_overlap | `description_hash_at_decision` |
| boundary_inflation / boundary_deflation | `description_hash_at_decision`、`version_at_decision`、`body_word_count_at_decision`、`body_h2_count_at_decision`（都从本次 inventory.json 取） |
| positioning_overlap | `description_hash_at_decision`、`adversaries_at_decision`（同组所有对手的 `skill_id` + `description_hash`） |

`signal` 取 `user_kept`（最强信号 —— 建议清理但用户保留）/ `user_archived` / `user_rewrote` / `user_deferred`。

`preferences.append([...])` 按 `(skill_id, signal, diagnosis_type, description_hash_at_decision)` 四元组去重，重复进入时累加 occurrences、刷新 last_seen_run。

## 读取：三档失效规则

`preferences.filter_active(prefs, state_by_id)` 把偏好分成 `active`（仍生效，跳过同类建议）和 `stale`（按当前内容重新评估）。三档判定规则：

| 偏好关联诊断 | 失效条件（任一命中 → stale） |
|---|---|
| positioning_unclear / trigger_boundary_overlap | `description_hash` 变 |
| boundary_inflation / boundary_deflation | `description_hash` 变 **或** ① 双方都有版本号 → 版本号不同 ② 任一方没有版本号 → 字数变化 ≥ 20% **或** ## 二级标题数变化 ≥ 1 |
| positioning_overlap | `description_hash` 变 **或** 任一 adversary 从 inventory 消失 / `description_hash` 变 |

## 为什么这样分档（why）

### 字数 ≥ 20% 与 h2 ≥ 1 的门槛 —— 既不放过真正的能力变化，又不被错别字修正打扰

如果只看 hash，body 改一个标点都会失效，太敏感；如果完全不看 body，能力变化但 description 没改的 boundary 类偏好会一直挂着不复评。20% 字数是稳健的「明确改了一段」信号，h2 数变化是「加了 / 删了一个能力章节」的硬信号。两个阈值都写在 `preferences.py` 顶层常量便于以后调。

### adversaries_at_decision —— 偏好绑定的是关系，不是孤立的 skill

用户上次 keep A 的真实原因常常是「A 跟 B、C 各自有别」。如果只记 A 的 hash，B 改了 description 不会让 A 的偏好失效 —— 但 A 跟 B 的差异关系可能已经不成立了。记录「当时和 A 同组的对手 + 它们的 hash」，对手任一消失或变样都重新评估，才符合用户的真实判断逻辑。

### 「簇」不持久化

3+ skill 同组 overlap 时合并提问只是 UX 决策。簇成员是 agent 在本次扫描里按相似度临时聚出来的，跨次扫描不稳定。如果偏好挂在「簇身份」上，第二次扫描簇略有变动就全部失效，反而打扰用户。所以失效检测看具体 adversary，不看簇。

## 行为速查

| 偏好状态 | 行为 |
|---|---|
| `user_kept` + 全部失效字段未变 | 跳过同类建议，报告里展示「按偏好保留」小节 |
| `user_kept` + 任一失效字段触发 | 偏好降级为 stale，按当前内容重新评估 |
| `user_archived` | skill 已不在 inventory 里，自然消失。仅作历史记录 |
| `user_rewrote` | 不特殊处理。仅作历史记录 |
| `user_deferred` | 报告里降低优先级展示，下次重新提 |
| 多次 `user_kept` 同一 skill | 报告里展示「用户已第 N 次保留此项」，措辞更克制 |

## 一条铁律

偏好不是执行授权。即使某条偏好是 `user_archived`，下次扫描也**不会**自动 archive 任何同类 skill。所有 archive / rewrite 都要走 SKILL.md Step 6-7 的用户逐项确认。
