from pathlib import Path

from sheet2midi.benchmark.metrics import evaluate_scores


ROOT = Path(__file__).resolve().parents[1]
PIANO = ROOT / "benchmarks/corpus/ground_truth/piano-grand.musicxml"


def test_self_evaluation_is_perfect() -> None:
    result = evaluate_scores(PIANO, PIANO)
    assert result.note_f1 == 1.0
    assert result.onset_f1 == 1.0
    assert result.duration_accuracy == 1.0
    assert result.part_accuracy == 1.0
    assert result.staff_accuracy == 1.0
    assert result.voice_accuracy == 1.0
