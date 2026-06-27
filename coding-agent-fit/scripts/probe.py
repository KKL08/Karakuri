#!/usr/bin/env python3
"""
Coding Agent readiness — URL resource prober

Probe a documentation site for AI-readable indexes, API specs, MCP/agent
discovery files, Markdown access, and page/index signals.

Usage: python3 probe.py <docs-url>
Output: JSON to stdout — { input_url, base_url, summary, probes }
"""

import json
import re
import socket
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
        "resource_type": "graphql",
        "paths": ["/graphql", "/api/graphql", "/v1/graphql"],
        "max_content": 10_000,
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
        "paths": [
            "/.well-known/agent-skills/index.json",
            "/.well-known/skills/index.json",
        ],
        "max_content": 50_000,
    },
    {
        "resource_type": "oauth_authorization_server",
        "paths": ["/.well-known/oauth-authorization-server", "/.well-known/openid-configuration"],
        "max_content": 100_000,
    },
    {
        "resource_type": "oauth_protected_resource",
        "paths": ["/.well-known/oauth-protected-resource"],
        "max_content": 100_000,
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
        "resource_type": "security_txt",
        "paths": ["/.well-known/security.txt", "/security.txt"],
        "max_content": 50_000,
    },
    {
        "resource_type": "mint_json",
        "paths": ["/mint.json"],
        "max_content": 100_000,
    },
]

COMMON_DOC_SUBDOMAINS = ("docs", "developer", "developers", "api", "platform")

TIMEOUT = 10
DNS_TIMEOUT = 5
PREVIEW_LIMIT = 2000
USER_AGENT = "Coding-Agent-Fit-Probe/1.0"

_ssl_strict = ssl.create_default_context()
_ssl_insecure = ssl.create_default_context()
_ssl_insecure.check_hostname = False
_ssl_insecure.verify_mode = ssl.CERT_NONE


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
    req = Request(url, headers=headers)
    tls_insecure = False

    try:
        resp = urlopen(req, timeout=TIMEOUT, context=_ssl_strict)
    except ssl.SSLError:
        tls_insecure = True
        try:
            resp = urlopen(req, timeout=TIMEOUT, context=_ssl_insecure)
        except HTTPError as exc:
            return _http_error_result(url, exc, max_content, tls_insecure=True)
        except (URLError, TimeoutError, OSError) as exc:
            return _error_result(url, exc, tls_insecure=True)
    except HTTPError as exc:
        return _http_error_result(url, exc, max_content)
    except (URLError, TimeoutError, OSError) as exc:
        return _error_result(url, exc)

    raw = resp.read(max_content)
    text = raw.decode("utf-8", errors="replace")
    return {
        "ok": True,
        "url": resp.geturl(),
        "status": getattr(resp, "status", 200),
        "content_type": resp.headers.get("Content-Type", ""),
        "headers": dict(resp.headers.items()),
        "text": text,
        "tls_insecure": tls_insecure,
    }


def _http_error_result(url: str, exc: HTTPError, max_content: int, tls_insecure: bool = False) -> dict:
    body = exc.read(min(max_content, PREVIEW_LIMIT)).decode("utf-8", errors="replace")
    return {
        "ok": False,
        "url": url,
        "status": exc.code,
        "content_type": exc.headers.get("Content-Type", ""),
        "headers": dict(exc.headers.items()),
        "text": body,
        "tls_insecure": tls_insecure,
    }


def _error_result(url: str, exc: Exception, tls_insecure: bool = False) -> dict:
    return {
        "ok": False,
        "url": url,
        "status": None,
        "content_type": "",
        "headers": {},
        "text": str(exc),
        "tls_insecure": tls_insecure,
    }


def is_usable_resource(result: dict, resource_type: str) -> bool:
    if not result["ok"] and resource_type != "graphql":
        return False
    content_type = result.get("content_type", "").lower()
    text = result.get("text", "")
    status = result.get("status")

    if resource_type == "sitemap":
        return "sitemap" in text[:500].lower() or "<urlset" in text[:500].lower()
    if resource_type == "llms_txt":
        return "text/html" not in content_type and ("# " in text[:200] or "- [" in text[:500])
    if resource_type == "graphql":
        # GraphQL endpoints typically reject GET with 400/405 but still respond.
        if status in (200, 400, 405):
            body = text[:1000].lower()
            return any(kw in body for kw in ("graphql", "must provide", "query"))
        return False
    if resource_type in {
        "openapi",
        "mcp_json",
        "mcp_server_card",
        "agent_skills",
        "oauth_authorization_server",
        "oauth_protected_resource",
        "api_catalog",
        "mint_json",
    }:
        return "text/html" not in content_type and text.strip() not in {"", "null", "Asset not found"}
    if resource_type == "robots_txt":
        return "user-agent" in text[:500].lower()
    if resource_type == "security_txt":
        return "contact:" in text[:1000].lower()
    return "text/html" not in content_type


def preview_result(result: dict, exists: bool, *, source: str) -> dict:
    return {
        "exists": exists,
        "url": result["url"],
        "status": result.get("status"),
        "content_type": result.get("content_type"),
        "source": source,
        "tls_insecure": result.get("tls_insecure", False),
        "content_preview": result.get("text", "")[:PREVIEW_LIMIT] if exists else None,
    }


def attempts_snapshot(attempts: list[dict]) -> list[dict]:
    return [{key: value for key, value in attempt.items() if key != "attempts"} for attempt in attempts]


def host_resolves(host: str) -> bool:
    try:
        socket.setdefaulttimeout(DNS_TIMEOUT)
        socket.getaddrinfo(host, 443)
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False
    finally:
        socket.setdefaulttimeout(None)


def candidate_subdomain_origins(input_url: str) -> list[str]:
    """Return subdomain origins worth probing besides the input host.

    Skips if the input is already on a known doc subdomain. DNS-resolves each
    candidate; non-resolving hosts are dropped so they don't bloat probe count.
    """
    parsed = urlparse(input_url)
    parts = parsed.netloc.split(".")
    if len(parts) >= 3 and parts[0].lower() in COMMON_DOC_SUBDOMAINS:
        return []
    apex = ".".join(parts[-2:]) if len(parts) >= 2 else parsed.netloc
    origins = []
    for sub in COMMON_DOC_SUBDOMAINS:
        host = f"{sub}.{apex}"
        if host == parsed.netloc:
            continue
        if host_resolves(host):
            origins.append(f"{parsed.scheme}://{host}")
    return origins


def candidate_bases(input_url: str) -> list[dict]:
    parsed = urlparse(input_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    parts = [part for part in parsed.path.split("/") if part]
    candidates = [{"label": "origin", "base_url": origin}]

    # Path prefixes — many docs platforms mount under /docs, /developer, etc.
    for index in range(1, len(parts) + 1):
        prefix = "/".join(parts[:index])
        candidates.append({"label": f"mount:/{prefix}", "base_url": f"{origin}/{prefix}"})

    # Subdomain candidates — docs.host, developer.host, api.host, etc.
    for sub_origin in candidate_subdomain_origins(input_url):
        candidates.append({"label": f"subdomain:{sub_origin}", "base_url": sub_origin})

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
        "url": fallback.get("url"),
        "status": fallback.get("status"),
        "content_type": fallback.get("content_type"),
        "source": fallback.get("source"),
        "tls_insecure": fallback.get("tls_insecure", False),
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
            "tls_insecure": result.get("tls_insecure", False),
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
        "tls_insecure": fallback.get("tls_insecure", False),
        "content_preview": None,
        "attempts": attempts,
    }


def probe_index_markdown(input_url: str) -> dict:
    attempts = []
    for base in candidate_bases(input_url):
        url = f"{base['base_url'].rstrip('/')}/index.md"
        result = fetch(url, max_content=100_000)
        exists = result["ok"] and "text/html" not in result.get("content_type", "").lower()
        attempt = preview_result(result, exists, source=base["label"])
        attempts.append(attempt)
        if exists:
            attempt["attempts"] = attempts_snapshot(attempts)
            return attempt

    fallback = attempts[0] if attempts else {"url": None}
    return {
        "exists": False,
        "url": fallback.get("url"),
        "status": fallback.get("status"),
        "content_type": fallback.get("content_type"),
        "source": fallback.get("source"),
        "tls_insecure": fallback.get("tls_insecure", False),
        "content_preview": None,
        "attempts": attempts,
    }


def extract_llms_signals(llms_result: dict) -> dict:
    text = llms_result.get("content_preview") or ""
    for attempt in llms_result.get("attempts", []):
        if attempt.get("exists") and attempt.get("content_preview"):
            text = attempt["content_preview"]
            break

    if llms_result.get("exists") and llms_result.get("url"):
        fetched = fetch(llms_result["url"], max_content=250_000)
        if fetched["ok"]:
            text = fetched["text"]

    patterns = {
        "mcp": r"mcp|model context protocol",
        "cli": r"\bcli\b|command line|命令行",
        "ai_coding": r"claude code|cursor|codex|cline|opencode|roo code|ai 编程|agent|agentic",
        "openapi": r"openapi|swagger|api spec",
        "sdk": r"\bsdk\b|sdks?/",
        "skill": r"\bskill\b|agent skill|agents\.md|\.cursor/rules|prompt pack|rules",
        "auth": r"auth|oauth|api key|token|鉴权|认证|权限",
        "rate_limit": r"rate limit|quota|retry|限流|额度|重试",
        "errors": r"error code|status code|troubleshoot|错误码|状态码|排障",
        "changelog": r"changelog|release notes|deprecat|migration|变更|弃用|迁移",
        "ai_section": r"ai agent|llm|agentic|ai integration|ai coding|agent integration",
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


def extract_page_signals(input_url: str) -> dict:
    result = fetch(input_url, max_content=250_000)
    text = result.get("text", "")
    patterns = {
        "developer_entry": r"developer|docs|documentation|api reference|开发者|文档|接口",
        "quickstart": r"quickstart|get started|getting started|快速开始|入门",
        "cli": r"\bcli\b|command line|命令行|npm install|brew install|pip install",
        "mcp": r"mcp|model context protocol",
        "skill": r"\bskill\b|agent skill|agents\.md|\.cursor/rules|prompt pack|rules",
        "agent_tools": r"claude code|cursor|codex|cline|windsurf|copilot|vs code",
        "openapi": r"openapi|swagger|api catalog|graphql schema",
        "auth": r"auth|oauth|api key|token|鉴权|认证|权限",
        "rate_limit": r"rate limit|quota|retry|限流|额度|重试",
        "errors": r"error code|status code|troubleshoot|错误码|状态码|排障",
        "status": r"status page|system status|service status|状态页|服务状态",
        "changelog": r"changelog|release notes|deprecat|migration|变更|弃用|迁移",
        "pricing_limits": r"pricing|billing|quota|region|plan|计费|套餐|地区",
        "ai_section": r"ai agent|for llms?|agentic|ai integration|ai coding tools",
        "sandbox": r"sandbox|test mode|test api key|playground|demo key|onboarding domain",
    }
    signals = {}
    for key, pattern in patterns.items():
        regex = re.compile(pattern, re.IGNORECASE)
        matches = regex.findall(text)
        signals[key] = {"exists": bool(matches), "count": len(matches)}
    return {
        "url": result.get("url"),
        "status": result.get("status"),
        "content_type": result.get("content_type"),
        "tls_insecure": result.get("tls_insecure", False),
        "signals": signals,
    }


def extract_robots_signals(robots_result: dict) -> dict:
    text = robots_result.get("content_preview") or ""
    if robots_result.get("exists") and robots_result.get("url"):
        fetched = fetch(robots_result["url"], max_content=100_000)
        if fetched["ok"]:
            text = fetched["text"]

    patterns = {
        "ai_bots": r"gptbot|chatgpt-user|claudebot|anthropic-ai|perplexitybot|ccbot|google-extended",
        "agent_policy": r"ai|agent|llm|training|crawl|content signal|use policy",
        "disallow": r"disallow:",
    }
    return {
        key: {
            "exists": bool(re.search(pattern, text, re.IGNORECASE)),
            "count": len(re.findall(pattern, text, re.IGNORECASE)),
        }
        for key, pattern in patterns.items()
    }


def normalize_input(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme:
        return raw_url
    return f"https://{raw_url}"


def _resource_summary(probe_result: dict | None) -> dict:
    if not probe_result or not probe_result.get("exists"):
        return {"exists": False}
    return {
        "exists": True,
        "url": probe_result.get("url"),
        "source": probe_result.get("source"),
        "tls_insecure": probe_result.get("tls_insecure", False),
        "size_bytes": len(probe_result.get("content_preview") or ""),
    }


def _page_signal(probes: dict, key: str) -> bool:
    return probes.get("page_signals", {}).get("signals", {}).get(key, {}).get("exists", False)


def build_summary(probes: dict) -> dict:
    """Pre-digested view of the probe payload for scoring agents.

    Each section maps to one rubric dimension's evidence. Field names are
    aligned with rubric naming contract — see references/rubric.md and SKILL.md.
    """
    llms_signals = probes.get("llms_index_signals", {})
    return {
        "ai_discovery": {
            "llms_txt": _resource_summary(probes.get("llms_txt")),
            "llms_signals_hit": [
                k for k, v in llms_signals.items() if v.get("count", 0) > 0
            ],
            "link_header_llms": probes.get("response_headers", {})
                .get("link_header", {}).get("exists", False),
            "ai_section_in_llms": llms_signals.get("ai_section", {}).get("count", 0) > 0,
            "ai_section_on_page": _page_signal(probes, "ai_section"),
        },
        "api_spec": {
            "openapi": _resource_summary(probes.get("openapi")),
            "api_catalog": _resource_summary(probes.get("api_catalog")),
            "graphql": _resource_summary(probes.get("graphql")),
            "page_mentions_openapi": _page_signal(probes, "openapi"),
        },
        "agent_tools": {
            "mcp_json": _resource_summary(probes.get("mcp_json")),
            "mcp_server_card": _resource_summary(probes.get("mcp_server_card")),
            "agent_skills": _resource_summary(probes.get("agent_skills")),
            "page_mentions_mcp": _page_signal(probes, "mcp"),
            "page_mentions_cli": _page_signal(probes, "cli"),
            "page_mentions_skill": _page_signal(probes, "skill"),
            "page_mentions_agent_tools": _page_signal(probes, "agent_tools"),
        },
        "docs_machine_readable": {
            "page_markdown": _resource_summary(probes.get("page_markdown")),
            "index_markdown": _resource_summary(probes.get("index_markdown")),
            "markdown_negotiation": probes.get("response_headers", {})
                .get("markdown_negotiation", {}).get("exists", False),
        },
        "auth": {
            "oauth_authorization_server": _resource_summary(probes.get("oauth_authorization_server")),
            "oauth_protected_resource": _resource_summary(probes.get("oauth_protected_resource")),
            "page_mentions_auth": _page_signal(probes, "auth"),
        },
        "friction_signals": {
            "tls_insecure_input": probes.get("page_signals", {}).get("tls_insecure", False),
            "robots_ai_bots": probes.get("robots_signals", {}).get("ai_bots", {}).get("exists", False),
            "page_mentions_errors": _page_signal(probes, "errors"),
            "page_mentions_rate_limit": _page_signal(probes, "rate_limit"),
            "page_mentions_pricing_limits": _page_signal(probes, "pricing_limits"),
            "page_mentions_sandbox": _page_signal(probes, "sandbox"),
        },
        "maintenance_hints": {
            "page_mentions_changelog": _page_signal(probes, "changelog"),
            "page_mentions_status": _page_signal(probes, "status"),
        },
    }


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
        "index_markdown": probe_index_markdown(input_url),
        "response_headers": probe_headers(input_url, bases),
    }

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {
            executor.submit(probe_resource, bases, target): target["resource_type"]
            for target in PROBE_TARGETS
        }
        for future in as_completed(futures):
            resource_type, result = future.result()
            probes[resource_type] = result

    probes["llms_index_signals"] = extract_llms_signals(probes.get("llms_txt", {}))
    probes["page_signals"] = extract_page_signals(input_url)
    probes["robots_signals"] = extract_robots_signals(probes.get("robots_txt", {}))

    output = {
        "input_url": input_url,
        "base_url": origin,
        "summary": build_summary(probes),
        "probes": probes,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
