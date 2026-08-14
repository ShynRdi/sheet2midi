from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.background import BackgroundTasks
from fastapi.responses import FileResponse

from .omr import backend_status
from .pipeline import convert

app = FastAPI(title="Sheet2MIDI", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "backends": backend_status()}


@app.post("/v1/convert")
def convert_sheet(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    engine: str = Form("auto"),
    track_mode: str = Form("staff"),
) -> FileResponse:
    if engine not in {"auto", "homr", "oemer", "audiveris"}:
        raise HTTPException(400, "Unsupported OMR engine")
    if track_mode not in {"staff", "part"}:
        raise HTTPException(400, "track_mode must be staff or part")

    temp = Path(tempfile.mkdtemp(prefix="sheet2midi-api-"))
    background_tasks.add_task(shutil.rmtree, temp, True)
    filename = Path(file.filename or "score.bin").name
    source = temp / filename
    with source.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)

    try:
        result = convert(source, temp / "out", engine=engine, track_mode=track_mode)
    except Exception as exc:
        shutil.rmtree(temp, ignore_errors=True)
        raise HTTPException(422, str(exc)) from exc

    archive = temp / "sheet2midi-output.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        output.write(result.musicxml, "score.musicxml")
        output.write(result.midi, "score.mid")
        output.write(result.validation_json, "validation.json")
    return FileResponse(
        archive,
        media_type="application/zip",
        filename="sheet2midi-output.zip",
        background=background_tasks,
    )
