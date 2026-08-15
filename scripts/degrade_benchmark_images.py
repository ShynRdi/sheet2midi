#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

VARIANTS = ("rotate", "blur", "shadow", "perspective", "jpeg")


def _solve_linear_system(matrix: list[list[float]], values: list[float]) -> list[float]:
    """Solve a small dense linear system with Gaussian elimination."""
    size = len(values)
    augmented = [row[:] + [value] for row, value in zip(matrix, values, strict=True)]

    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("Perspective transform is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]

        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]

        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0:
                continue
            augmented[row] = [
                current - factor * pivot_current
                for current, pivot_current in zip(
                    augmented[row],
                    augmented[column],
                    strict=True,
                )
            ]

    return [augmented[row][-1] for row in range(size)]


def _perspective_coefficients(
    destination: tuple[tuple[float, float], ...],
    source: tuple[tuple[float, float], ...],
) -> tuple[float, ...]:
    """Return Pillow output-to-input perspective coefficients.

    Pillow samples the source image for every output pixel, so the equations map
    points in the desired destination quadrilateral back to source coordinates.
    """
    if len(destination) != 4 or len(source) != 4:
        raise ValueError("Perspective transform requires four point pairs")

    matrix: list[list[float]] = []
    values: list[float] = []
    for (x, y), (u, v) in zip(destination, source, strict=True):
        matrix.append([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y])
        values.append(u)
        matrix.append([0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y])
        values.append(v)
    return tuple(_solve_linear_system(matrix, values))


def _mild_perspective(image: Image.Image) -> Image.Image:
    """Simulate a modest off-axis phone photo without collapsing the page."""
    width, height = image.size
    source = (
        (0.0, 0.0),
        (float(width - 1), 0.0),
        (float(width - 1), float(height - 1)),
        (0.0, float(height - 1)),
    )
    destination = (
        (0.04 * width, 0.035 * height),
        (0.965 * width, 0.005 * height),
        (0.91 * width, 0.975 * height),
        (0.075 * width, 0.995 * height),
    )
    coefficients = _perspective_coefficients(destination, source)
    return image.transform(
        image.size,
        Image.Transform.PERSPECTIVE,
        coefficients,
        resample=Image.Resampling.BICUBIC,
        fillcolor="white",
    )


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
        return _mild_perspective(image)
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
