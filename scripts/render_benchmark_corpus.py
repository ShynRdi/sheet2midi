#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def find_musescore() -> str:
    for candidate in ("mscore", "musescore", "mscore3", "musescore3", "musescore4"):
        executable = shutil.which(candidate)
        if executable:
            return executable
    raise SystemExit("MuseScore CLI not found on PATH")


def crop_to_content(image, *, threshold: int = 245, padding: int = 80):
    grayscale = image.convert("L")
    mask = grayscale.point(lambda pixel: 255 if pixel < threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return image

    left, top, right, bottom = bbox
    return image.crop(
        (
            max(0, left - padding),
            max(0, top - padding),
            min(image.width, right + padding),
            min(image.height, bottom + padding),
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Render benchmark MusicXML into PNG images")
    parser.add_argument(
        "manifest",
        type=Path,
        nargs="?",
        default=Path("benchmarks/corpus/manifest.json"),
    )
    parser.add_argument(
        "--crop-content",
        action="store_true",
        help="Crop large page margins around rendered score content",
    )
    parser.add_argument("--crop-threshold", type=int, default=245)
    parser.add_argument("--crop-padding", type=int, default=80)
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    root = manifest.parent
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    musescore = find_musescore()

    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise SystemExit("Install PDF support first: pip install -e '.[pdf]'") from exc

    for case in payload["cases"]:
        source = root / case["ground_truth"]
        destination = root / case["image"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        pdf = destination.with_suffix(".pdf")
        subprocess.run([musescore, "-o", str(pdf), str(source)], check=True)

        document = pdfium.PdfDocument(str(pdf))
        page = document[0]
        image = page.render(scale=3).to_pil().convert("RGB")
        if args.crop_content:
            image = crop_to_content(
                image,
                threshold=args.crop_threshold,
                padding=args.crop_padding,
            )
        image.save(destination)
        page.close()
        document.close()
        pdf.unlink(missing_ok=True)
        print(f"{destination} ({image.width}x{image.height})")


if __name__ == "__main__":
    main()
