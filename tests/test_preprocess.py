from pathlib import Path

from PIL import Image, ImageDraw

from sheet2midi.preprocess import deskew_image, estimate_skew_angle


def make_staff_image(path: Path) -> None:
    image = Image.new("RGB", (1000, 700), "white")
    draw = ImageDraw.Draw(image)
    for base in (150, 350, 550):
        for offset in range(0, 70, 14):
            draw.line((80, base + offset, 920, base + offset), fill="black", width=2)
    for x in (180, 400, 620, 840):
        draw.line((x, 140, x, 620), fill="black", width=2)
    image.save(path)


def test_estimate_skew_detects_small_rotation(tmp_path: Path) -> None:
    source = tmp_path / "staff.png"
    make_staff_image(source)

    rotated = tmp_path / "rotated.png"
    Image.open(source).rotate(2.5, expand=True, fillcolor="white").save(rotated)

    angle = estimate_skew_angle(rotated)
    assert -2.8 < angle < -2.2


def test_deskew_reduces_staff_rotation(tmp_path: Path) -> None:
    source = tmp_path / "staff.png"
    make_staff_image(source)

    rotated = tmp_path / "rotated.png"
    Image.open(source).rotate(2.5, expand=True, fillcolor="white").save(rotated)

    corrected = tmp_path / "corrected.png"
    output, angle = deskew_image(rotated, corrected)

    assert output == corrected
    assert corrected.is_file()
    assert -2.8 < angle < -2.2
    assert abs(estimate_skew_angle(corrected)) < 0.25


def test_deskew_leaves_aligned_staff_alone(tmp_path: Path) -> None:
    source = tmp_path / "staff.png"
    make_staff_image(source)

    output = tmp_path / "clean.png"
    _path, angle = deskew_image(source, output)

    assert angle == 0.0
    assert output.is_file()
