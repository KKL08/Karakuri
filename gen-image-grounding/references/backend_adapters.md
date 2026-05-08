# Backend Adapters

The skill outputs a backend-neutral generation spec. The host agent should adapt it to the image model it is about to call.

## Reference-capable image edit models

Examples: Qwen-Image-Edit, Gemini image models with image inputs, Seedream variants with reference support.

Use:
- `gen_prompt` as the textual instruction.
- Up to the first 3-5 `reference_images[].local_path` values as input images, depending on backend limit.
- Preserve reference ordering. If the prompt says "first reference image", it must map to the first image passed.

## Text-only image models

Examples: many Flux or SD text-to-image deployments.

Use:
- `gen_prompt` only.
- Do not pass reference image URLs into the model prompt unless the backend explicitly supports URL fetching.
- Mention in the final user-facing response that references were used to ground the prompt, but the selected backend did not consume image inputs.

## Agent integration shapes

Codex / Claude Code:
- Use the local skill directly.
- Store the JSON spec next to the generated image or in `/tmp`.

Hermes:
- Treat this as a procedural skill/tool. It should not modify Hermes memory by default.
- If useful, attach the JSON spec to the current session artifact trail.

OpenClaw / OpenViking:
- Store the JSON spec, downloaded reference images, and source pages as resources so future sessions can reuse the visual grounding.

MCP:
- Wrap `prepare` as a tool named `prepare_image_generation`.
- Input: `{ "prompt": string, "backend": string | null }`.
- Output: the JSON spec.

## Provider Notes

Volcengine:
- Best used for Chinese and China-local visual grounding.
- Configure `VOLCENGINE_SEARCH_API_KEY`.
- The provider uses API-key mode and `SearchType=image`.
- Returned image URLs can be signed/temporary; always consume `local_path` after the CLI downloads the image.
- `page_url` may be empty for some image results, so do not treat missing source pages as a parsing error.
