#!/usr/bin/env python3
"""
DocAI Audit — URL Resource Prober

Probe a documentation site for AI-readable indexes, API specs, MCP/agent
discovery files, Markdown access, and page/index signals.

Usage: python3 probe.py <docs-url>
Output: JSON to stdout
"""

import json
import re
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

PROBE_TARGETS = [
    {
        "resource_type": "llms_txt",
        "paths": ["/llms.txt", "/llms-full.txt"],
        "max_content": 1_000_000,
    },
    {
        "resource_type": "openapi",
        "paths": [
            "/openapi.json",
            "/openapi.yaml",
            "/swagger.json",
            "/api-spec.json",
            "/api/openapi.json",
            "/api/openapi.yaml",
        ],
        "max_content": 500_000,
    },
    {
        "resource_type": "mcp_json",
        "paths": ["/.well-known/mcp.json"],
        "max_content": 50_000,
    },
    {
        "resource_type": "mcp_server_card",
        "paths": ["/.well-known/mcp/server-card.json"],
        "max_content": 50_000,
    },
    {
        "resource_type": "agent_skills",
        "paths": ["/.well-known/agent-skills/index.json"],
        "max_content": 50_000,
    },
    {
        "resource_type": "api_catalog",
        "paths": ["/.well-known/api-catalog", "/api-catalog"],
        "max_content": 100_000,
    },
    {
        "resource_type": "sitemap",
        "paths": ["/sitemap.xml", "/sitemap_index.xml"],
        "max_content": 500_000,
    },
    {
        "resource_type": "robots_txt",
        "paths": ["/robots.txt"],
        "max_content": 50_000,
    },
    {
        "resource_type": "mint_json",
        "paths": ["/mint.json"],
        "max_content": 100_000,
    },
]

TIMEOUT = 10
PREVIEW_LIMIT = 2000
USER_AGENT = "DocAI-Audit-Probe/2.0"

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


class LinkHeaderParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "link":
            return
        attr = {name.lower(): value for name, value in attrs}
        rel = attr.get("rel", "")
        href = attr.get("href")
        if href and ("llms" in rel.lower() or "alternate" in rel.lower()):
            self.links.append({"rel": rel, "href": href})


def fetch(url: str, *, accept: str | None = None, max_content: int = 100_000) -> dict:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    try:
        req = Request(url, headers=headers)
        resp = urlopen(req, timeout=TIMEOUT, context=_ssl_ctx)
        raw = resp.read(max_content)
        text = raw.decode("utf-8", errors="replace")
        return {
            "ok": True,
            "url": resp.geturl(),
            "status": getattr(resp, "status", 200),
            "content_type": resp.headers.get("Content-Type", ""),
            "headers": dict(resp.headers.items()),
            "text": text,
        }
    except HTTPError as exc:
        body = exc.read(min(max_content, PREVIEW_LIMIT)).decode("utf-8", errors="replace")
        return {
            "ok": False,
            "url": url,
            "status": exc.code,
            "content_type": exc.headers.get("Content-Type", ""),
            "headers": dict(exc.headers.items()),
            "text": body,
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "url": url,
            "status": None,
            "content_type": "",
            "headers": {},
            "text": str(exc),
        }


def is_usable_resource(result: dict, resource_type: str) -> bool:
    if not result["ok"]:
        return False
    content_type = result.get("content_type", "").lower()
    text = result.get("text", "")
    if resource_type == "sitemap":
        return "sitemap" in text[:500].lower() or "<urlset" in text[:500].lower()
    if resource_type == "llms_txt":
        return "text/html" not in content_type and ("# " in text[:200] or "- [" in text[:500])
    if resource_type in {"openapi", "mcp_json", "mcp_server_card", "agent_skills", "api_catalog", "mint_json"}:
        return "text/html" not in content_type and text.strip() not in {"", "null", "Asset not found"}
    if resource_type == "robots_txt":
        return "user-agent" in text[:500].lower()
    return "text/html" not in content_type


def preview_result(result: dict, exists: bool, *, source: str) -> dict:
    return {
        "exists": exists,
        "url": result["url"],
        "status": result.get("status"),
        "content_type": result.get("content_type"),
        "source": source,
        "content_preview": result.get("text", "")[:PREVIEW_LIMIT] if exists else None,
    }


def attempts_snapshot(attempts: list[dict]) -> list[dict]:
    return [{key: value for key, value in attempt.items() if key != "attempts"} for attempt in attempts]


def candidate_bases(input_url: str) -> list[dict]:
    parsed = urlparse(input_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    parts = [part for part in parsed.path.split("/") if part]
    candidates = [{"label": "origin", "base_url": origin}]

    # Many docs platforms mount AI resources under the docs app path, e.g. /docs/llms.txt.
    if parts:
        first = f"{origin}/{parts[0]}"
        candidates.append({"label": f"mount:/{parts[0]}", "base_url": first})

    # Also try the direct parent for nested docs deployments.
    if len(parts) > 1:
        parent = f"{origin}/{'/'.join(parts[:-1])}"
        candidates.append({"label": "page-parent", "base_url": parent})

    seen = set()
    unique = []
    for candidate in candidates:
        if candidate["base_url"] in seen:
            continue
        seen.add(candidate["base_url"])
        unique.append(candidate)
    return unique


def probe_resource(base_candidates: list[dict], target: dict) -> tuple[str, dict]:
    resource_type = target["resource_type"]
    max_content = target.get("max_content", 100_000)
    attempts = []

    for base in base_candidates:
        for path in target["paths"]:
            url = f"{base['base_url']}{path}"
            result = fetch(url, max_content=max_content)
            exists = is_usable_resource(result, resource_type)
            attempt = preview_result(result, exists, source=base["label"])
            attempts.append(attempt)
            if exists:
                attempt["attempts"] = attempts_snapshot(attempts)
                return resource_type, attempt

    fallback = attempts[0] if attempts else {"url": None, "status": None, "content_type": None}
    return resource_type, {
        "exists": False,
        "url": fallback["url"],
        "status": fallback.get("status"),
        "content_type": fallback.get("content_type"),
        "source": fallback.get("source"),
        "content_preview": None,
        "attempts": attempts,
    }


def parse_link_header(link_header: str, base_url: str) -> list[dict]:
    links = []
    for match in re.finditer(r"<([^>]+)>\s*;\s*rel=\"?([^\",;]+)\"?", link_header or ""):
        href, rel = match.groups()
        links.append({"rel": rel, "url": urljoin(base_url.rstrip("/") + "/", href)})
    return links


def probe_headers(input_url: str, base_candidates: list[dict]) -> dict:
    targets = [input_url] + [candidate["base_url"] for candidate in base_candidates]
    results = {}
    for target in dict.fromkeys(targets):
        result = fetch(target, max_content=100_000)
        link = result.get("headers", {}).get("Link", "")
        x_llms = result.get("headers", {}).get("X-Llms-Txt") or result.get("headers", {}).get("x-llms-txt")

        parser = LinkHeaderParser()
        if result.get("text"):
            parser.feed(result["text"][:100_000])

        md = fetch(target, accept="text/markdown, text/plain;q=0.9", max_content=100_000)
        results[target] = {
            "status": result.get("status"),
            "content_type": result.get("content_type"),
            "link_header": {"exists": bool(link), "value": link[:500] if link else None},
            "link_header_urls": parse_link_header(link, target),
            "x_llms_txt": {"exists": bool(x_llms), "value": x_llms},
            "html_llms_links": [
                {"rel": item["rel"], "url": urljoin(target, item["href"])}
                for item in parser.links
            ],
            "markdown_negotiation": {
                "exists": md["ok"] and "text/markdown" in md.get("content_type", "").lower(),
                "content_type": md.get("content_type"),
            },
        }

    first = results.get(input_url, {})
    return {
        "input_url": first,
        "all": results,
        # Backward-compatible summary fields.
        "link_header": first.get("link_header", {"exists": False, "value": None}),
        "markdown_negotiation": first.get("markdown_negotiation", {"exists": False}),
    }


def probe_page_markdown(input_url: str) -> dict:
    candidates = []
    if not input_url.rstrip("/").endswith(".md"):
        candidates.append(input_url.rstrip("/") + ".md")
    candidates.append(input_url)

    attempts = []
    for index, url in enumerate(candidates):
        accept = None if index == 0 and url.endswith(".md") else "text/markdown, text/plain;q=0.9"
        result = fetch(url, accept=accept, max_content=100_000)
        exists = result["ok"] and "text/markdown" in result.get("content_type", "").lower()
        attempt = preview_result(result, exists, source=".md" if url.endswith(".md") else "accept:text/markdown")
        attempts.append(attempt)
        if exists:
            attempt["attempts"] = attempts_snapshot(attempts)
            return attempt

    fallback = attempts[0] if attempts else {"url": input_url}
    return {
        "exists": False,
        "url": fallback.get("url"),
        "status": fallback.get("status"),
        "content_type": fallback.get("content_type"),
        "source": fallback.get("source"),
        "content_preview": None,
        "attempts": attempts,
    }


def extract_llms_signals(llms_result: dict) -> dict:
    text = llms_result.get("content_preview") or ""
    for attempt in llms_result.get("attempts", []):
        if attempt.get("exists") and attempt.get("content_preview"):
            text = attempt["content_preview"]
            break

    # If the first preview is too small, refetch the winning URL with a larger cap.
    if llms_result.get("exists") and llms_result.get("url"):
        fetched = fetch(llms_result["url"], max_content=250_000)
        if fetched["ok"]:
            text = fetched["text"]

    patterns = {
        "mcp": r"mcp|model context protocol",
        "cli": r"\bcli\b|command line|命令行",
        "ai_coding": r"claude code|cursor|codex|cline|opencode|roo code|ai 编程|agent",
        "openapi": r"openapi|swagger",
        "sdk": r"\bsdk\b",
    }
    links = re.findall(r"- \[([^\]]+)\]\(([^)]+)\)(?::\s*([^\n]+))?", text)
    signal_links = {}
    for key, pattern in patterns.items():
        regex = re.compile(pattern, re.IGNORECASE)
        matches = [
            {"title": title, "url": url, "description": desc.strip()}
            for title, url, desc in links
            if regex.search(title) or regex.search(url) or regex.search(desc)
        ]
        signal_links[key] = {"count": len(matches), "sample": matches[:10]}
    return signal_links


def normalize_input(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme:
        return raw_url
    return f"https://{raw_url}"


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python3 probe.py <docs-url>"}))
        sys.exit(1)

    input_url = normalize_input(sys.argv[1])
    parsed = urlparse(input_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    bases = candidate_bases(input_url)

    probes = {
        "candidate_bases": bases,
        "page_markdown": probe_page_markdown(input_url),
        "response_headers": probe_headers(input_url, bases),
    }

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(probe_resource, bases, target): target["resource_type"]
            for target in PROBE_TARGETS
        }
        for future in as_completed(futures):
            resource_type, result = future.result()
            probes[resource_type] = result

    probes["llms_index_signals"] = extract_llms_signals(probes.get("llms_txt", {}))

    output = {
        "input_url": input_url,
        "base_url": origin,
        "probes": probes,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
