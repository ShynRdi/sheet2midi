import json
from pathlib import Path
from xml.etree import ElementTree as ET

from sheet2midi.benchmark.metrics import evaluate_scores

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "benchmarks/corpus"
PIANO = CORPUS / "ground_truth/piano-grand.musicxml"


def test_self_evaluation_is_perfect() -> None:
    result = evaluate_scores(PIANO, PIANO)
    assert result.note_f1 == 1.0
    assert result.onset_f1 == 1.0
    assert result.duration_accuracy == 1.0
    assert result.part_accuracy == 1.0
    assert result.staff_accuracy == 1.0
    assert result.voice_accuracy == 1.0


def test_ground_truth_notes_have_explicit_types() -> None:
    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    for case in manifest["cases"]:
        root = ET.parse(CORPUS / case["ground_truth"]).getroot()
        notes = root.findall(".//note")
        assert notes, case["id"]
        for note in notes:
            assert note.find("type") is not None, case["id"]


def test_piano_fixtures_use_grand_staff_clefs() -> None:
    for filename in ("piano-grand.musicxml", "vocal-piano.musicxml", "choir-piano.musicxml"):
        root = ET.parse(CORPUS / "ground_truth" / filename).getroot()
        clefs = {
            (clef.attrib.get("number"), clef.findtext("sign"))
            for clef in root.findall(".//clef")
        }
        assert ("1", "G") in clefs
        assert ("2", "F") in clefs
