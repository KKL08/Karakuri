# Prompt Rules

The `gen_prompt` should be suitable for a downstream image generation model.

## Include

- Main subject identity and count.
- Action, pose, composition, camera angle, crop, lighting, style, and medium.
- Specific visual attributes confirmed by sources or reference images.
- Required readable text exactly as written by the user, if any.
- Reference image ordering using ordinal language: "the first reference image", "the second reference image".

## Avoid

- Raw image URLs.
- Source URLs.
- Long research notes.
- Unverified facts stated as certain.
- More than five reference images.

## Handling uncertainty

If a detail is not verified, phrase it as a visual approximation or move it to `warnings`.

Example:

```text
Use the first reference image for the subject's face shape and hairstyle, the second reference image for the venue facade, and the third reference image for the trophy shape. Create a cinematic editorial photograph...
```

## Backend modes

- `image_edit`: use when reference images exist and identity/visual fidelity matters.
- `text_to_image`: use when no reference image is available or the requested backend does not support image inputs.
- `hybrid`: use when the host agent will first generate from text, then refine with references.
