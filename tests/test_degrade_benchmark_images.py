import importlib.util
import json
from pathlib import Path
from types import ModuleType

from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/degrade_benchmark_images.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sheet2midi_degrade_benchmark", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dark_bbox(image: Image.Image, threshold: int = 220) -> tuple[int, int, int, int] | None:
    grayscale = image.convert("L")
    mask = grayscale.point(lambda value: 255 if value < threshold else 0)
    return mask.getbbox()


def test_generated_variant_manifest_paths_resolve_from_manifest_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    script = load_script()
    corpus = tmp_path / "corpus-v2"
    clean = corpus / "images/clean/case.png"
    truth = corpus / "ground_truth/case.musicxml"
    clean.parent.mkdir(parents=True)
    truth.parent.mkdir(parents=True)
    Image.new("RGB", (100, 100), "white").save(clean)
    truth.write_text("<score-partwise/>", encoding="utf-8")

    manifest = corpus / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "case",
                        "category": "test",
                        "ground_truth": "ground_truth/case.musicxml",
                        "image": "images/clean/case.png",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        ["degrade_benchmark_images.py", str(manifest)],
    )
    script.main()

    for variant in script.VARIANTS:
        variant_manifest = corpus / "manifests" / f"{variant}.json"
        payload = json.loads(variant_manifest.read_text(encoding="utf-8"))
        case = payload["cases"][0]
        assert (variant_manifest.parent / case["ground_truth"]).is_file()
        assert (variant_manifest.parent / case["image"]).is_file()


def test_perspective_variant_preserves_score_width() -> None:
    script = load_script()
    image = Image.new("RGB", (1200, 800), "white")
    draw = ImageDraw.Draw(image)
    for y in range(180, 621, 55):
        draw.line((120, y, 1080, y), fill="black", width=4)
    draw.rectangle((140, 150, 1060, 650), outline="black", width=4)

    clean_bbox = _dark_bbox(image)
    transformed = script.degrade(image, "perspective")
    transformed_bbox = _dark_bbox(transformed)

    assert clean_bbox is not None
    assert transformed_bbox is not None
    clean_width = clean_bbox[2] - clean_bbox[0]
    transformed_width = transformed_bbox[2] - transformed_bbox[0]

    assert transformed_width >= clean_width * 0.75
    assert transformed_width <= image.width
    assert transformed.size == image.size
