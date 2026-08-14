import importlib.util
from pathlib import Path
from types import ModuleType
from xml.etree import ElementTree as ET

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate_benchmark_v2.py"


def load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sheet2midi_benchmark_v2_generator", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v2_generator_writes_five_multimeasure_scores(
    tmp_path: Path,
    monkeypatch,
) -> None:
    generator = load_generator()
    monkeypatch.setattr(generator, "ROOT", tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"cases":[1,2,3,4,5]}', encoding="utf-8")
    generator.main()
    files = sorted((tmp_path / "ground_truth").glob("*.musicxml"))
    assert len(files) == 5
    for path in files:
        root = ET.parse(path).getroot()
        parts = root.findall("part")
        assert parts
        for part in parts:
            assert len(part.findall("measure")) == 4
        for note in root.findall(".//note"):
            assert note.find("type") is not None


def test_v2_piano_has_grand_staff_and_polyphonic_chord(
    tmp_path: Path,
    monkeypatch,
) -> None:
    generator = load_generator()
    monkeypatch.setattr(generator, "ROOT", tmp_path)
    (tmp_path / "manifest.json").write_text(
        '{"cases":[1,2,3,4,5]}',
        encoding="utf-8",
    )
    generator.main()
    root = ET.parse(tmp_path / "ground_truth/piano-polyphonic.musicxml").getroot()
    assert root.find(".//staves").text == "2"
    clefs = {
        (node.attrib.get("number"), node.findtext("sign"))
        for node in root.findall(".//clef")
    }
    assert ("1", "G") in clefs
    assert ("2", "F") in clefs
    assert root.find(".//chord") is not None
