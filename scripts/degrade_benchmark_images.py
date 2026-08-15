#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

VARIANTS = ("rotate", "blur", "shadow", "perspective", "jpeg")


def degrade(image: Image.Image, variant: str) -> Image.Image:
    image = image.convert("RGB")
    if variant == "rotate":
        return image.rotate(2.5, expand=True, fillcolor="white")
    if variant == "blur":
        return image.filter(ImageFilter.GaussianBlur(radius=1.4))
    if variant == "shadow":
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        width, height = image.size
        for x in range(width):
            alpha = int(95 * (x / max(1, width - 1)))
            draw.line((x, 0, x, height), fill=(0, 0, 0, alpha))
        return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    if variant == "perspective":
        width, height = image.size
        return image.transform(
            (width, height),
            Image.Transform.QUAD,
            (
                35,
                20,
                width - 10,
                0,
                width - 40,
                height - 15,
                5,
                height,
            ),
            resample=Image.Resampling.BICUBIC,
            fillcolor="white",
        )
    if variant == "jpeg":
        return image
    raise ValueError(variant)


def _manifest_relative(path_from_root: Path) -> str:
    """Return a path usable from corpus-v2/manifests/*.json."""
    return (Path("..") / path_from_root).as_posix()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic benchmark image degradations"
    )
    parser.add_argument(
        "manifest",
        type=Path,
        nargs="?",
        default=Path("benchmarks/corpus-v2/manifest.json"),
    )
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    root = manifest_path.parent
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    for variant in VARIANTS:
        variant_manifest = {**payload, "variant": variant, "cases": []}
        for case in payload["cases"]:
            source = root / case["image"]
            destination = root / "images" / variant / f"{case['id']}.png"
            destination.parent.mkdir(parents=True, exist_ok=True)
            image = degrade(Image.open(source), variant)
            if variant == "jpeg":
                jpg = destination.with_suffix(".jpg")
                image.save(jpg, quality=42, optimize=True)
                image = Image.open(jpg).convert("RGB")
                jpg.unlink()
            image.save(destination)

            updated = dict(case)
            updated["ground_truth"] = _manifest_relative(Path(case["ground_truth"]))
            updated["image"] = _manifest_relative(destination.relative_to(root))
            variant_manifest["cases"].append(updated)

        manifest_out = root / "manifests" / f"{variant}.json"
        manifest_out.parent.mkdir(parents=True, exist_ok=True)
        manifest_out.write_text(
            json.dumps(variant_manifest, indent=2),
            encoding="utf-8",
        )
        print(manifest_out)


if __name__ == "__main__":
    main()
