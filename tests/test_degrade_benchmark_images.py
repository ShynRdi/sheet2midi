import importlib.util
import json
from pathlib import Path
from types import ModuleType

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/degrade_benchmark_images.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sheet2midi_degrade_benchmark", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
