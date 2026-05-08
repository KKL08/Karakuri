---
name: gen-image-grounding
description: Use before image generation when a prompt depends on real-world visual accuracy, current facts, specific people, places, events, products, logos, outfits, architecture, props, posters, or readable text. The skill searches and browses evidence, retrieves reference images, and produces a grounded generation spec for any downstream image model.
---

# Gen Image Grounding

Use this skill before calling an image generation model when the user's request needs external visual or factual grounding.

Good triggers:
- Real people, public figures, athletes, celebrities, teams, outfits, trophies, venues, products, brands, logos, landmarks, buildings, events, news, scientific objects, historical objects, posters, UI screenshots, maps, badges, signs, or readable text.
- The user asks for accuracy, "based on references", "look it up", "search first", "真实", "准确", "参考图", "按真实样子".

Skip by default:
- Purely fictional or generic prompts where outside knowledge does not matter, such as "a cat on a sofa in watercolor", unless the user explicitly asks for references.

## Workflow

1. Run the grounding CLI:

```bash
python scripts/gen_grounder.py prepare --prompt "<user prompt>" --out /tmp/generation_spec.json
```

2. Read the generated JSON spec.

3. If `need_search` is false, use `gen_prompt` directly.

4. If `need_search` is true, pass `gen_prompt` and the valid `reference_images[].local_path` files to an image model that supports references. If the target backend is text-only, use `gen_prompt` and mention that references were used only to write the prompt.

5. Preserve `facts`, `sources`, and `warnings` in the response or artifact trail. Do not present unverified details as confirmed.

## Environment

The CLI works in plan-only mode without credentials. Configure any of these providers for live search:

```bash
export SERPER_KEY_ID="..."                 # text + image search, recommended MVP
export VOLCENGINE_SEARCH_API_KEY="..."     # China-friendly image search via Volcengine
export TAVILY_API_KEY="..."                # agent-friendly text search with optional images
export FIRECRAWL_API_KEY="..."             # optional search provider
export JINA_API_KEYS="..."                 # page reading via r.jina.ai
```

Optional endpoints:

```bash
export TEXT_SEARCH_API_BASE_URL="https://google.serper.dev/search"
export IMAGE_SEARCH_API_BASE_URL="https://google.serper.dev/images"
export VOLCENGINE_SEARCH_API_BASE="https://open.feedcoopapi.com/search_api/web_search"
```

Volcengine image results may use signed image URLs, so the CLI downloads them immediately into `cache/images`. Some results may not include a source landing page; preserve empty `page_url` instead of inventing one.

## Output Contract

The CLI returns:

```json
{
  "need_search": true,
  "original_prompt": "...",
  "gen_prompt": "...",
  "reference_images": [
    {
      "id": "IMG_001",
      "local_path": "cache/images/...",
      "url": "https://...",
      "page_url": "https://...",
      "title": "...",
      "note": "What to copy from this image.",
      "provider": "volcengine"
    }
  ],
  "facts": [
    {
      "claim": "...",
      "source_url": "https://...",
      "confidence": "medium"
    }
  ],
  "sources": [
    {
      "title": "...",
      "url": "https://...",
      "snippet": "..."
    }
  ],
  "warnings": ["..."],
  "suggested_backend": {
    "mode": "image_edit",
    "reason": "Reference images are available."
  }
}
```

## Guidance

- Prefer 1-5 reference images. Keep one clear image per visual subject when possible.
- Use text search to confirm names, dates, context, and written details.
- Use image search for faces, outfits, venue cues, props, logos, architecture, and style references.
- Avoid copying raw URLs into the final image prompt. Keep URLs in `sources` and `reference_images`.
- If a detail remains uncertain, put it in `warnings` instead of inventing it.

For backend-specific handling, read `references/backend_adapters.md`.
For prompt composition rules, read `references/prompt_rules.md`.
