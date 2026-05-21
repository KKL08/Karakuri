from __future__ import annotations

from .models import ParsedSkill


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def _clean_scalar(value: str) -> str:
    return value.strip().strip("\"'")


def _join_description_lines(lines: list[str]) -> str:
    return " ".join(part.strip() for part in lines if part.strip())


def _parse_header(lines: list[str]) -> tuple[dict[str, str], str, str | None, list[str]]:
    data: dict[str, str] = {}
    notes: list[str] = []
    description_status = "absent"
    description_raw: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or ":" not in line:
            index += 1
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = _clean_scalar(raw_value)
        if key == "description":
            if value in {">", ">-", ">+", "|", "|-", "|+"}:
                block: list[str] = []
                index += 1
                while index < len(lines) and (lines[index].startswith(" ") or lines[index].startswith("\t")):
                    block.append(lines[index])
                    index += 1
                description_raw = _join_description_lines(block)
                if description_raw:
                    data[key] = description_raw
                    description_status = "parsed"
                    notes.append("description_block_scalar")
                else:
                    description_status = "empty"
                    description_raw = ""
                continue
            if value:
                data[key] = value
                description_status = "parsed"
                description_raw = value
                index += 1
                continue
            fallback: list[str] = []
            probe = index + 1
            while probe < len(lines) and (lines[probe].startswith(" ") or lines[probe].startswith("\t")):
                fallback.append(lines[probe])
                probe += 1
            description_raw = _join_description_lines(fallback)
            if description_raw:
                data[key] = description_raw
                description_status = "parse_incomplete"
                notes.append("description_fallback_indented")
                index = probe
                continue
            description_status = "empty"
            description_raw = ""
            index += 1
            continue
        data[key] = value
        index += 1
    return data, description_status, description_raw, notes


def parse_skill_markdown(text: str) -> ParsedSkill:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ParsedSkill(
            name=None,
            description=None,
            body=text,
            body_lines=len(lines),
            body_token_estimate=_estimate_tokens(text),
            frontmatter_malformed=True,
            raw_frontmatter={},
            description_status="absent",
            description_raw=None,
            frontmatter_notes=[],
        )

    closing_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        return ParsedSkill(
            name=None,
            description=None,
            body="\n".join(lines[1:]),
            body_lines=max(0, len(lines) - 1),
            body_token_estimate=_estimate_tokens(text),
            frontmatter_malformed=True,
            raw_frontmatter={},
            description_status="absent",
            description_raw=None,
            frontmatter_notes=[],
        )

    header, description_status, description_raw, notes = _parse_header(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :])
    return ParsedSkill(
        name=header.get("name") or None,
        description=header.get("description") or None,
        body=body,
        body_lines=len(body.splitlines()),
        body_token_estimate=_estimate_tokens(body),
        frontmatter_malformed=False,
        raw_frontmatter=header,
        description_status=description_status,
        description_raw=description_raw,
        frontmatter_notes=notes,
    )
