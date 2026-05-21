from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable


TOKEN_RE = re.compile(r"[A-Za-z0-9_\-一-鿿]+")

TRIGGER_TERM_STOPWORDS = {
    "all", "and", "any", "are", "but", "can", "for", "from", "has", "have",
    "into", "its", "more", "not", "one", "out", "see", "such", "than", "that",
    "the", "their", "them", "they", "this", "use", "uses", "via", "when",
    "where", "which", "while", "will", "with", "without", "you", "your",
}

DOMAIN_KEYWORDS = {
    "web": {"web", "webpage", "browser", "chrome", "url", "link", "网页", "浏览器", "链接", "搜索", "抓取", "联网"},
    "lark": {"lark", "feishu", "飞书", "多维表格", "云文档", "妙记", "日历", "邮箱", "审批", "考勤", "画板"},
    "email": {"email", "gmail", "mail", "inbox", "邮箱", "邮件", "收件箱"},
    "document": {"document", "documents", "doc", "docs", "pdf", "markdown", "文档", "文件"},
    "workflow": {"workflow", "subagent", "流程", "计划", "评审", "调试"},
    "frontend": {"frontend", "react", "nextjs", "shadcn", "ui", "web-app"},
    "deployment": {"vercel", "cloudflare", "deploy", "worker", "wrangler", "部署"},
    "media": {"image", "video", "presentation", "slides", "spreadsheet", "图片", "视频", "幻灯片", "表格"},
    "map": {"map", "amap", "地图", "高德", "poi", "路线"},
    "code": {"git", "github", "repo", "code", "代码", "仓库"},
}

ACTION_KEYWORDS = {
    "search": {"search", "query", "find", "lookup", "搜索", "查询", "查找"},
    "fetch": {"fetch", "download", "获取", "下载", "抓取"},
    "read": {"read", "extract", "open", "查看", "读取"},
    "write": {"write", "create", "edit", "update", "append", "replace", "compose", "创建", "编辑", "更新", "写入", "起草"},
    "send": {"send", "reply", "forward", "发送", "回复", "转发"},
    "run": {"run", "execute", "cli", "script", "执行", "运行", "命令"},
    "review": {"review", "triage", "audit", "debug", "评审", "整理", "排查", "审查"},
    "generate": {"generate", "build", "render", "生成", "构建", "渲染"},
    "manage": {"manage", "organize", "cleanup", "archive", "管理", "整理", "归档"},
}

OBJECT_KEYWORDS = {
    "url": {"url", "link", "链接", "网址"},
    "webpage": {"webpage", "page", "browser", "网页", "页面", "浏览器"},
    "markdown": {"markdown", "md"},
    "document": {"document", "doc", "docs", "docx", "文档", "云文档"},
    "pdf": {"pdf"},
    "email": {"email", "mail", "gmail", "邮件", "邮箱"},
    "calendar": {"calendar", "日历", "日程"},
    "task": {"task", "todo", "任务", "待办"},
    "meeting": {"meeting", "minutes", "vc", "会议", "妙记", "纪要"},
    "base": {"base", "sheet", "spreadsheet", "多维表格", "表格"},
    "slide": {"slide", "slides", "presentation", "幻灯片", "演示文稿"},
    "whiteboard": {"whiteboard", "画板", "mermaid", "plantuml"},
    "map": {"map", "poi", "route", "地图", "路线"},
    "repo": {"repo", "github", "git", "branch", "仓库", "分支"},
}


def _tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    raw = {token.lower().replace("_", "-") for token in TOKEN_RE.findall(text)}
    expanded = set(raw)
    for token in raw:
        expanded.update(part for part in token.split("-") if part)
    return expanded


def _matches(tokens: set[str], lexicon: dict[str, set[str]]) -> list[str]:
    matched: list[str] = []
    text = " ".join(tokens)
    for label, keywords in lexicon.items():
        if tokens.intersection(keywords):
            matched.append(label)
            continue
        for keyword in keywords:
            if not keyword.isascii():
                if keyword in text:
                    matched.append(label)
                    break
            elif (keyword + "s") in tokens:
                matched.append(label)
                break
    return sorted(matched)


def extract_capability_fingerprint(skill: dict[str, object]) -> dict[str, object]:
    name = str(skill.get("name") or "")
    directory = Path(str(skill.get("skill_dir") or "")).name
    description = str(skill.get("description") or "")
    tokens = _tokens(" ".join([name, directory, description]))
    return {
        "domains": _matches(tokens, DOMAIN_KEYWORDS),
        "actions": _matches(tokens, ACTION_KEYWORDS),
        "objects": _matches(tokens, OBJECT_KEYWORDS),
        "trigger_terms": sorted(token for token in tokens if len(token) > 2 and token not in TRIGGER_TERM_STOPWORDS)[:40],
    }


def _shared(left: dict[str, object], right: dict[str, object], key: str) -> set[str]:
    return set(left.get(key, [])).intersection(set(right.get(key, [])))


def capability_overlap(left: dict[str, object], right: dict[str, object]) -> tuple[float, list[str]]:
    shared_domains = _shared(left, right, "domains")
    shared_actions = _shared(left, right, "actions")
    shared_objects = _shared(left, right, "objects")
    shared_terms = _shared(left, right, "trigger_terms")
    score = 0.0
    reasons: list[str] = []
    if shared_domains:
        score += 0.34
        reasons.extend(f"shared_domain:{value}" for value in sorted(shared_domains))
    if shared_actions:
        score += min(0.24, 0.12 * len(shared_actions))
        reasons.extend(f"shared_action:{value}" for value in sorted(shared_actions))
    if shared_objects:
        score += min(0.30, 0.15 * len(shared_objects))
        reasons.extend(f"shared_object:{value}" for value in sorted(shared_objects))
    if len(shared_terms) >= 3:
        score += 0.12
        reasons.append("shared_trigger_terms")
    if not (shared_domains and (shared_actions or shared_objects)):
        return 0.0, []
    return round(min(score, 1.0), 3), reasons


CAPABILITY_GROUP_THRESHOLD = 0.73

TIGHT_MAX_SIZE = 6
TIGHT_MIN_DENSITY = 0.6
LOOSE_MAX_SIZE = 10
LOOSE_MIN_DENSITY = 0.4

DOMAIN_REPORT_LABELS = {
    "web": "网页/浏览器",
    "document": "文档",
    "email": "邮件",
    "lark": "飞书/Lark",
    "frontend": "前端",
    "code": "代码仓库",
    "workflow": "工作流程",
    "deployment": "部署",
    "media": "媒体内容",
    "map": "地图",
    "mixed": "混合功能",
}


def _classify_group(size: int, density: float) -> str:
    if size <= TIGHT_MAX_SIZE and density >= TIGHT_MIN_DENSITY:
        return "tight"
    if size <= LOOSE_MAX_SIZE and density >= LOOSE_MIN_DENSITY:
        return "loose"
    return "too_broad"


def _group_confidence(status: str, mean_pair_score: float) -> str:
    if status == "tight" and mean_pair_score >= 0.78:
        return "high"
    if status in ("tight", "loose") and mean_pair_score >= 0.70:
        return "medium"
    return "low"


def _too_broad_reasons(size: int, density: float) -> list[str]:
    reasons: list[str] = []
    if size > LOOSE_MAX_SIZE:
        reasons.append(f"数量 {size} 超过宽松功能组上限 {LOOSE_MAX_SIZE}")
    if density < LOOSE_MIN_DENSITY:
        reasons.append(f"连接密度 {density:.2f} 低于宽松功能组阈值 {LOOSE_MIN_DENSITY:.2f}")
    return reasons or ["功能组超过当前基础筛查可稳定解释的范围"]


def _coverage_hint(status: str, primary_domain: str, size: int, density: float) -> dict[str, object] | None:
    if status != "too_broad":
        return None
    domain_label = DOMAIN_REPORT_LABELS.get(primary_domain, primary_domain)
    reasons = _too_broad_reasons(size, density)
    reason_text = "；".join(reasons)
    return {
        "kind": "too_broad_capability_group",
        "report_action": "brief_note_only",
        "summary": f"基础筛查发现{domain_label}相关描述形成 {size} 项宽泛功能组，但{reason_text}，不作为 Agent 评估入口。",
        "recommended_wording": f"基础筛查发现一组{domain_label}相关的 skill 描述较宽泛，已作为覆盖提示保留；本次未因这个宽泛功能组逐项深读。",
        "why_not_routed": reasons,
    }


def _primary_domain(fingerprints: Iterable[dict[str, object]]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for fingerprint in fingerprints:
        for domain in fingerprint.get("domains", []):
            counts[str(domain)] += 1
    if not counts:
        return "mixed"
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def build_capability_groups(skills: list[dict[str, object]]) -> list[dict[str, object]]:
    usable = [skill for skill in skills if not skill.get("is_self")]
    fingerprints = {
        str(skill["skill_id"]): skill.get("capability_fingerprint") or extract_capability_fingerprint(skill)
        for skill in usable
    }
    pairs: list[dict[str, object]] = []
    for left_index, left in enumerate(usable):
        for right in usable[left_index + 1 :]:
            left_id = str(left["skill_id"])
            right_id = str(right["skill_id"])
            if left_id == right_id:
                continue
            score, reasons = capability_overlap(fingerprints[left_id], fingerprints[right_id])
            if score >= CAPABILITY_GROUP_THRESHOLD:
                pairs.append(
                    {
                        "skill_ids": [left_id, right_id],
                        "score": score,
                        "reasons": reasons,
                    }
                )
    if not pairs:
        return []

    parent: dict[str, str] = {}

    def find(value: str) -> str:
        parent.setdefault(value, value)
        if parent[value] != value:
            parent[value] = find(parent[value])
        return parent[value]

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    for pair in pairs:
        left_id, right_id = pair["skill_ids"]
        union(str(left_id), str(right_id))

    grouped_ids: dict[str, set[str]] = defaultdict(set)
    for pair in pairs:
        for skill_id in pair["skill_ids"]:
            grouped_ids[find(str(skill_id))].add(str(skill_id))

    groups: list[dict[str, object]] = []
    for members in grouped_ids.values():
        member_pairs = [
            pair for pair in pairs if set(pair["skill_ids"]).issubset(members)
        ]
        member_fingerprints = [fingerprints[skill_id] for skill_id in sorted(members)]
        reasons = sorted({reason for pair in member_pairs for reason in pair["reasons"]})
        size = len(members)
        max_pairs = size * (size - 1) // 2
        density = (len(member_pairs) / max_pairs) if max_pairs else 0.0
        scores = [float(pair["score"]) for pair in member_pairs]
        max_pair_score = round(max(scores), 3) if scores else 0.0
        mean_pair_score = round(sum(scores) / len(scores), 3) if scores else 0.0
        status = _classify_group(size, density)
        confidence = _group_confidence(status, mean_pair_score)
        score = round(mean_pair_score * math.sqrt(density), 3) if density else 0.0
        primary_domain = _primary_domain(member_fingerprints)
        group: dict[str, object] = {
            "group_id": "",
            "skill_ids": sorted(members),
            "score": score,
            "max_pair_score": max_pair_score,
            "mean_pair_score": mean_pair_score,
            "pair_density": round(density, 3),
            "status": status,
            "confidence": confidence,
            "primary_domain": primary_domain,
            "reasons": reasons,
            "review_questions": [
                "是否存在一个应保留的主入口？",
                "是否有 skill 只是旧入口或子能力入口？",
                "是否需要通过 description 明确边界，而不是归档？",
            ],
        }
        hint = _coverage_hint(status, primary_domain, size, density)
        if hint is not None:
            group["coverage_hint"] = hint
        groups.append(group)

    groups = sorted(groups, key=lambda item: (-float(item["score"]), str(item["primary_domain"]), item["skill_ids"]))
    domain_counts: dict[str, int] = defaultdict(int)
    for group in groups:
        domain = str(group["primary_domain"])
        domain_counts[domain] += 1
        group["group_id"] = f"capability-{domain}-{domain_counts[domain]:03d}"
    return groups
