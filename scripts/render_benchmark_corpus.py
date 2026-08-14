#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def find_musescore() -> str:
    for candidate in ("mscore", "musescore", "musescore4", "MuseScore4"):
        executable = shutil.which(candidate)
        if executable:
            return executable
    raise SystemExit("MuseScore CLI not found on PATH")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render benchmark MusicXML into PNG images")
    parser.add_argument("manifest", type=Path, nargs="?", default=Path("benchmarks/corpus/manifest.json"))
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    root = manifest.parent
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    musescore = find_musescore()

    for case in payload["cases"]:
        source = root / case["ground_truth"]
        destination = root / case["image"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        pdf = destination.with_suffix(".pdf")
        subprocess.run([musescore, "-o", str(pdf), str(source)], check=True)
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise SystemExit("Install PDF support first: pip install -e '.[pdf]'") from exc
        document = pdfium.PdfDocument(str(pdf))
        page = document[0]
        image = page.render(scale=3).to_pil().convert("RGB")
        image.save(destination)
        page.close()
        document.close()
        pdf.unlink(missing_ok=True)
        print(destination)


if __name__ == "__main__":
    main()
