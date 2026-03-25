#!/usr/bin/env python3
"""
DocAI Audit — URL Resource Prober

Probes a documentation site for AI-related resources:
llms.txt, OpenAPI spec, MCP config, sitemap, robots.txt, mint.json.

Usage: python3 probe.py <base_url>
Output: JSON to stdout
"""

import json
import sys
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

PROBE_TARGETS = [
    {
        "resource_type": "llms_txt",
        "paths": ["/llms.txt", "/llms-full.txt"],
        "max_content": 100_000,
    },
    {
        "resource_type": "openapi",
        "paths": [
            "/openapi.json",
            "/openapi.yaml",
            "/swagger.json",
            "/api-spec.json",
            "/api/openapi.json",
        ],
        "max_content": 500_000,
    },
    {
        "resource_type": "mcp_json",
        "paths": ["/.well-known/mcp.json"],
        "max_content": 50_000,
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

TIMEOUT = 10  # seconds
PREVIEW_LIMIT = 2000  # characters for content_preview
USER_AGENT = "DocAI-Audit-Probe/1.0"

# Create a permissive SSL context for sites with certificate issues
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def probe_url(url: str, resource_type: str, max_content: int) -> dict:
    """Probe a single URL. Returns a result dict."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        resp = urlopen(req, timeout=TIMEOUT, context=_ssl_ctx)

        content_type = resp.headers.get("Content-Type", "")

        # Filter out HTML responses (error pages masquerading as the resource)
        # Exception: sitemaps can be served as text/html
        if resource_type != "sitemap" and "text/html" in content_type:
            return {"exists": False, "url": url, "content_preview": None}

        raw = resp.read(max_content)
        text = raw.decode("utf-8", errors="replace")
        preview = text[:PREVIEW_LIMIT]

        return {"exists": True, "url": url, "content_preview": preview}

    except (URLError, HTTPError, TimeoutError, OSError):
        return {"exists": False, "url": url, "content_preview": None}


def probe_resource(origin: str, target: dict) -> tuple[str, dict]:
    """Probe all paths for a resource type, return first match."""
    resource_type = target["resource_type"]
    max_content = target.get("max_content", 100_000)

    for path in target["paths"]:
        url = f"{origin}{path}"
        result = probe_url(url, resource_type, max_content)
        if result["exists"]:
            return resource_type, result

    # No match found — return last attempted URL
    last_url = f"{origin}{target['paths'][0]}"
    return resource_type, {"exists": False, "url": last_url, "content_preview": None}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python3 probe.py <base_url>"}))
        sys.exit(1)

    base_url = sys.argv[1]

    # Normalize to origin
    parsed = urlparse(base_url)
    if not parsed.scheme:
        base_url = f"https://{base_url}"
        parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    probes = {}

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(probe_resource, origin, target): target["resource_type"]
            for target in PROBE_TARGETS
        }

        for future in as_completed(futures):
            resource_type, result = future.result()
            probes[resource_type] = result

    output = {"base_url": origin, "probes": probes}
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
