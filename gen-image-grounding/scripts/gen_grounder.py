#!/usr/bin/env python3
"""Prepare a search-grounded image generation spec.

This script is intentionally dependency-light. It can run without API keys in
plan-only mode, and it uses live providers when relevant environment variables
are present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request


SERPER_SEARCH_URL = "https://google.serper.dev/search"
SERPER_IMAGES_URL = "https://google.serper.dev/images"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"
FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v2/search"
VOLCENGINE_SEARCH_URL = "https://open.feedcoopapi.com/search_api/web_search"


@dataclass
class Source:
    title: str
    url: str
    snippet: str = ""
    provider: str = ""


@dataclass
class Fact:
    claim: str
    source_url: str
    confidence: str = "medium"


@dataclass
class ReferenceImage:
    id: str
    local_path: str
    url: str
    page_url: str = ""
    title: str = ""
    note: str = ""
    width: int | None = None
    height: int | None = None
    provider: str = ""
    source_name: str = ""


def _json_request(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int = 30) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _get_text(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> str:
    req = request.Request(url, headers=headers or {}, method="GET")
    with request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _safe_slug(text: str, limit: int = 64) -> str:
    slug = re.sub(r"[^0-9A-Za-z._-]+", "_", text.strip())
    slug = slug.strip("._-")
    return (slug[:limit] or "item")


def need_search(prompt: str) -> tuple[bool, list[str]]:
    p = prompt.lower()
    reasons: list[str] = []
    trigger_words = [
        "real",
        "accurate",
        "reference",
        "logo",
        "brand",
        "poster",
        "event",
        "news",
        "celebrity",
        "athlete",
        "landmark",
        "architecture",
        "trophy",
        "badge",
        "uniform",
        "jersey",
        "product",
        "screenshot",
        "map",
        "真实",
        "准确",
        "参考",
        "人物",
        "明星",
        "球员",
        "地标",
        "建筑",
        "品牌",
        "徽标",
        "海报",
        "新闻",
        "事件",
        "产品",
        "奖杯",
        "球衣",
        "服装",
        "文字",
    ]
    for word in trigger_words:
        if word in p:
            reasons.append(f"contains trigger: {word}")
    if re.search(r"\b(19|20)\d{2}\b", prompt):
        reasons.append("contains a year")
    if re.search(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}", prompt):
        reasons.append("contains likely named entity")
    return bool(reasons), reasons[:6]


def build_queries(prompt: str) -> dict[str, list[str]]:
    cleaned = re.sub(r"\s+", " ", prompt).strip()
    short = cleaned[:180]
    image_query = short
    if not re.search(r"reference|参考|photo|image|图片", image_query, re.I):
        image_query = f"{image_query} reference image"
    text_queries = [short]
    if len(short) > 90:
        text_queries.append(short[:90])
    return {
        "text": list(dict.fromkeys(text_queries))[:3],
        "image": [image_query],
    }


def serper_text_search(queries: list[str], top_k: int) -> list[Source]:
    key = os.getenv("SERPER_KEY_ID", "").strip()
    if not key:
        return []
    url = os.getenv("TEXT_SEARCH_API_BASE_URL", SERPER_SEARCH_URL).strip() or SERPER_SEARCH_URL
    headers = {"X-API-KEY": key, "Content-Type": "application/json"}
    out: list[Source] = []
    for q in queries:
        data = _json_request(url, {"q": q, "num": max(1, min(top_k, 10))}, headers)
        for item in data.get("organic") or []:
            link = item.get("link") or ""
            if not link:
                continue
            out.append(Source(
                title=_strip_html(item.get("title") or ""),
                url=link,
                snippet=_strip_html(item.get("snippet") or ""),
                provider="serper",
            ))
    return _dedupe_sources(out)


def tavily_search(query: str, top_k: int, include_images: bool = False) -> tuple[list[Source], list[dict[str, Any]]]:
    key = os.getenv("TAVILY_API_KEY", "").strip()
    if not key:
        return [], []
    payload = {
        "api_key": key,
        "query": query,
        "search_depth": "basic",
        "max_results": max(1, min(top_k, 10)),
        "include_images": include_images,
        "include_answer": False,
    }
    data = _json_request(TAVILY_SEARCH_URL, payload, {"Content-Type": "application/json"})
    sources = [
        Source(
            title=item.get("title") or "",
            url=item.get("url") or "",
            snippet=item.get("content") or "",
            provider="tavily",
        )
        for item in data.get("results") or []
        if item.get("url")
    ]
    images: list[dict[str, Any]] = []
    for img in data.get("images") or []:
        if isinstance(img, str):
            images.append({"imageUrl": img, "title": "image", "link": ""})
        elif isinstance(img, dict):
            images.append(img)
    return _dedupe_sources(sources), images


def firecrawl_search(query: str, top_k: int) -> tuple[list[Source], list[dict[str, Any]]]:
    key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not key:
        return [], []
    payload = {"query": query, "limit": max(1, min(top_k, 10)), "sources": ["web", "images"]}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = _json_request(FIRECRAWL_SEARCH_URL, payload, headers)
    results = data.get("data") or data.get("results") or []
    sources: list[Source] = []
    images: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        image_url = item.get("imageUrl") or item.get("image_url")
        if image_url:
            images.append(item)
        elif item.get("url"):
            sources.append(Source(
                title=item.get("title") or "",
                url=item.get("url") or "",
                snippet=item.get("description") or item.get("content") or "",
                provider="firecrawl",
            ))
    return _dedupe_sources(sources), images


def serper_image_search(query: str, top_k: int) -> list[dict[str, Any]]:
    key = os.getenv("SERPER_KEY_ID", "").strip()
    if not key:
        return []
    url = os.getenv("IMAGE_SEARCH_API_BASE_URL", SERPER_IMAGES_URL).strip() or SERPER_IMAGES_URL
    headers = {"X-API-KEY": key, "Content-Type": "application/json"}
    data = _json_request(url, {"q": query, "num": max(1, min(top_k, 10))}, headers)
    return list(data.get("images") or [])


def volcengine_image_search(query: str, top_k: int) -> list[dict[str, Any]]:
    """Search images through Volcengine Web Search API.

    API-key mode docs use:
      POST https://open.feedcoopapi.com/search_api/web_search
      Authorization: Bearer <API_KEY>
      {"Query": "...", "SearchType": "image", "Count": 5}
    """
    key = os.getenv("VOLCENGINE_SEARCH_API_KEY", "").strip()
    if not key:
        return []
    url = (
        os.getenv("VOLCENGINE_SEARCH_API_BASE", "").strip()
        or os.getenv("VOLCENGINE_SEARCH_API_URL", "").strip()
        or VOLCENGINE_SEARCH_URL
    )
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    # Volcengine image search currently documents Count as max 5.
    payload = {"Query": query, "SearchType": "image", "Count": max(1, min(top_k, 5))}
    data = _json_request(url, payload, headers)
    result = data.get("Result") or {}
    items: list[dict[str, Any]] = []
    for raw in result.get("ImageResults") or []:
        if not isinstance(raw, dict):
            continue
        image = raw.get("Image") or {}
        image_url = image.get("Url") or ""
        if not image_url:
            continue
        # Normalize to the same shape used by other image providers.
        items.append({
            "title": raw.get("Title") or "reference image",
            "imageUrl": image_url,
            "link": raw.get("Url") or "",
            "source": raw.get("SiteName") or "",
            "imageWidth": image.get("Width"),
            "imageHeight": image.get("Height"),
            "shape": image.get("Shape"),
            "rankScore": raw.get("RankScore"),
            "publishTime": raw.get("PublishTime"),
            "_provider": "volcengine",
        })
    return items


def jina_browse(url: str, goal: str) -> str:
    key = os.getenv("JINA_API_KEYS", "").strip()
    if not key:
        return ""
    jina_url = "https://r.jina.ai/" + url
    try:
        text = _get_text(jina_url, headers={"Authorization": f"Bearer {key}"}, timeout=40)
    except Exception:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    return text[:900]


def _strip_html(text: str) -> str:
    return re.sub(r"</?b>", "", text or "").strip()


def _dedupe_sources(sources: list[Source]) -> list[Source]:
    seen: set[str] = set()
    out: list[Source] = []
    for src in sources:
        if not src.url or src.url in seen:
            continue
        seen.add(src.url)
        out.append(src)
    return out


def _image_url_from_item(item: dict[str, Any]) -> str:
    image = item.get("Image") if isinstance(item.get("Image"), dict) else {}
    return (
        item.get("imageUrl")
        or item.get("image_url")
        or item.get("url")
        or item.get("thumbnailUrl")
        or item.get("thumbnail_url")
        or image.get("Url")
        or ""
    )


def _page_url_from_item(item: dict[str, Any]) -> str:
    return item.get("link") or item.get("pageUrl") or item.get("sourceUrl") or item.get("source_url") or item.get("Url") or ""


def _image_width_from_item(item: dict[str, Any]) -> int | None:
    image = item.get("Image") if isinstance(item.get("Image"), dict) else {}
    return _to_int(item.get("imageWidth") or item.get("width") or image.get("Width"))


def _image_height_from_item(item: dict[str, Any]) -> int | None:
    image = item.get("Image") if isinstance(item.get("Image"), dict) else {}
    return _to_int(item.get("imageHeight") or item.get("height") or image.get("Height"))


def _source_name_from_item(item: dict[str, Any]) -> str:
    return item.get("source") or item.get("sourceName") or item.get("SiteName") or item.get("domain") or ""


def download_image(image_url: str, cache_dir: Path, page_url: str = "") -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(image_url.encode("utf-8")).hexdigest()[:24]
    ext = Path(parse.urlparse(image_url).path).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    path = cache_dir / f"{digest}{ext}"
    if path.exists() and path.stat().st_size > 512:
        return str(path)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; gen-image-grounder/0.1)",
        "Accept": "image/avif,image/webp,image/png,image/jpeg,image/*,*/*;q=0.8",
    }
    if page_url:
        headers["Referer"] = page_url
    req = request.Request(image_url, headers=headers, method="GET")
    with request.urlopen(req, timeout=30) as resp:
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read()
    if len(raw) < 512:
        raise ValueError("downloaded image is too small")
    guessed_ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
    if guessed_ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"} and guessed_ext != ext:
        path = cache_dir / f"{digest}{guessed_ext}"
    path.write_bytes(raw)
    return str(path)


def build_reference_images(items: list[dict[str, Any]], cache_dir: Path, max_images: int) -> tuple[list[ReferenceImage], list[str]]:
    refs: list[ReferenceImage] = []
    warnings: list[str] = []
    seen_urls: set[str] = set()
    for item in items:
        if len(refs) >= max_images:
            break
        image_url = _image_url_from_item(item)
        if not image_url or image_url in seen_urls:
            continue
        seen_urls.add(image_url)
        page_url = _page_url_from_item(item)
        title = item.get("title") or item.get("Title") or item.get("source") or "reference image"
        try:
            local_path = download_image(image_url, cache_dir, page_url=page_url)
        except Exception as exc:
            warnings.append(f"Failed to download image from {image_url[:120]}: {exc}")
            continue
        ref_id = f"IMG_{len(refs) + 1:03d}"
        refs.append(ReferenceImage(
            id=ref_id,
            local_path=local_path,
            url=image_url,
            page_url=page_url,
            title=title,
            note=f"Use {ref_id} as a visual reference for the main subject, style, setting, or object details.",
            width=_image_width_from_item(item),
            height=_image_height_from_item(item),
            provider=item.get("_provider") or "",
            source_name=_source_name_from_item(item),
        ))
    return refs, warnings


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def facts_from_sources(sources: list[Source], browse_goal: str, max_facts: int = 5) -> list[Fact]:
    facts: list[Fact] = []
    for src in sources[:max_facts]:
        snippet = src.snippet.strip()
        if snippet:
            claim = snippet[:260]
        else:
            browsed = jina_browse(src.url, browse_goal)
            claim = browsed[:260] if browsed else f"Relevant source found: {src.title or src.url}"
        facts.append(Fact(claim=claim, source_url=src.url, confidence="medium"))
    return facts


def compose_prompt(original_prompt: str, refs: list[ReferenceImage], facts: list[Fact], warnings: list[str]) -> str:
    pieces = [original_prompt.strip()]
    if refs:
        ref_phrases = []
        ordinals = ["first", "second", "third", "fourth", "fifth"]
        for idx, ref in enumerate(refs[:5]):
            ordinal = ordinals[idx] if idx < len(ordinals) else f"{idx + 1}th"
            ref_phrases.append(f"use the {ordinal} reference image for {ref.note.replace(ref.id, '').strip()}")
        pieces.append("Reference guidance: " + "; ".join(ref_phrases) + ".")
    if facts:
        fact_text = " ".join(f.claim for f in facts[:3] if f.claim)
        if fact_text:
            pieces.append("Grounded details to preserve: " + fact_text)
    pieces.append(
        "Create a visually coherent, high-quality image with accurate identity, setting, objects, wardrobe, proportions, lighting, and any required readable text. Do not include source URLs in the image."
    )
    if warnings:
        pieces.append("Avoid overcommitting to uncertain details that were not verified.")
    return "\n\n".join(p for p in pieces if p)


def prepare(prompt: str, out: Path, cache_dir: Path, top_k: int, max_images: int, dry_run: bool, backend: str) -> dict[str, Any]:
    search_needed, reasons = need_search(prompt)
    queries = build_queries(prompt)
    warnings: list[str] = []
    sources: list[Source] = []
    image_items: list[dict[str, Any]] = []

    if dry_run:
        warnings.append("Dry run: no network providers were called.")
    elif search_needed:
        try:
            sources.extend(serper_text_search(queries["text"], top_k))
        except Exception as exc:
            warnings.append(f"Serper text search failed: {exc}")
        try:
            tavily_sources, tavily_images = tavily_search(queries["text"][0], top_k, include_images=True)
            sources.extend(tavily_sources)
            for item in tavily_images:
                item["_provider"] = "tavily"
            image_items.extend(tavily_images)
        except Exception as exc:
            warnings.append(f"Tavily search failed: {exc}")
        try:
            firecrawl_sources, firecrawl_images = firecrawl_search(queries["text"][0], top_k)
            sources.extend(firecrawl_sources)
            for item in firecrawl_images:
                item["_provider"] = "firecrawl"
            image_items.extend(firecrawl_images)
        except Exception as exc:
            warnings.append(f"Firecrawl search failed: {exc}")
        try:
            volcengine_images = volcengine_image_search(queries["image"][0], top_k)
            image_items.extend(volcengine_images)
        except Exception as exc:
            warnings.append(f"Volcengine image search failed: {exc}")
        try:
            serper_images = serper_image_search(queries["image"][0], top_k)
            for item in serper_images:
                item["_provider"] = "serper"
            image_items.extend(serper_images)
        except Exception as exc:
            warnings.append(f"Serper image search failed: {exc}")

    sources = _dedupe_sources(sources)[:top_k]
    refs: list[ReferenceImage] = []
    if image_items and not dry_run:
        refs, image_warnings = build_reference_images(image_items, cache_dir / "images", max_images)
        warnings.extend(image_warnings)
    if search_needed and not sources and not refs and not dry_run:
        warnings.append("No live search results were collected. Check provider API keys or run with --dry-run for planning.")

    facts = facts_from_sources(sources, prompt) if sources and not dry_run else []
    gen_prompt = compose_prompt(prompt, refs, facts, warnings if search_needed else [])
    mode = "image_edit" if refs else "text_to_image"
    if backend and backend.lower() in {"flux", "sd", "stable-diffusion", "text"}:
        mode = "text_to_image"
    spec = {
        "schema_version": "0.1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "need_search": search_needed,
        "search_reasons": reasons,
        "original_prompt": prompt,
        "queries": queries,
        "gen_prompt": gen_prompt,
        "reference_images": [asdict(r) for r in refs],
        "facts": [asdict(f) for f in facts],
        "sources": [asdict(s) for s in sources],
        "warnings": warnings,
        "suggested_backend": {
            "mode": mode,
            "reason": "Reference images are available." if refs else "No downloaded reference images are available.",
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return spec


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Search-ground an image generation prompt.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_prepare = sub.add_parser("prepare", help="Create a grounded generation spec.")
    p_prepare.add_argument("--prompt", required=True)
    p_prepare.add_argument("--out", required=True)
    p_prepare.add_argument("--cache-dir", default=str(Path(__file__).resolve().parents[1] / "cache"))
    p_prepare.add_argument("--top-k", type=int, default=5)
    p_prepare.add_argument("--max-images", type=int, default=5)
    p_prepare.add_argument("--backend", default="")
    p_prepare.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.cmd == "prepare":
        try:
            spec = prepare(
                prompt=args.prompt,
                out=Path(args.out),
                cache_dir=Path(args.cache_dir),
                top_k=args.top_k,
                max_images=args.max_images,
                dry_run=args.dry_run,
                backend=args.backend,
            )
        except (error.URLError, TimeoutError, ValueError, OSError) as exc:
            print(f"gen_grounder failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({
            "out": str(Path(args.out).resolve()),
            "need_search": spec["need_search"],
            "reference_images": len(spec["reference_images"]),
            "sources": len(spec["sources"]),
            "warnings": len(spec["warnings"]),
        }, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
