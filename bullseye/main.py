import datetime as dt
import shutil
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import audit, config, excel, most, pipeline, store
from .models import Operation, Study, ToolAction

app = FastAPI(title="Bulls Eye - MOST Video Time Study")
STATIC = Path(__file__).parent / "static"
ALLOWED = {".mp4", ".mts", ".m2ts", ".mov", ".avi", ".mkv"}


@app.on_event("startup")
def _recover_interrupted():
    for s in store.all_studies():
        if s.status in ("processing", "uploaded"):
            s.status, s.error = "error", "Processing was interrupted (server restarted). Click 'Re-run AI'."
            store.save(s)


def _get(study_id: str) -> Study:
    s = store.load(study_id)
    if not s:
        raise HTTPException(404, "Study not found")
    return s


def _out(s: Study) -> dict:
    return {**s.model_dump(), "audit": audit.summary(s), "can_approve": audit.can_approve(s)}


def _content(s: Study) -> str:
    """Study content that, if changed, invalidates an approval (ignores review marks)."""
    skip = {"review", "note", "issues", "cycle_time"}
    return repr([[op.name, [s2.model_dump(exclude=skip) for s2 in op.steps]] for op in s.operations])


@app.get("/api/config")
def get_config():
    return {"seconds_per_index": config.SECONDS_PER_INDEX, "model": config.GEMINI_MODEL,
            "has_key": bool(config.GEMINI_API_KEY), "usd_inr": config.USD_INR,
            "price_in": config.PRICE_IN, "price_out": config.PRICE_OUT,
            "thinking_budget": config.THINKING_BUDGET, "max_fps": config.MAX_FPS,
            "tools": [t.value for t in ToolAction]}


@app.get("/api/studies")
def list_studies():
    out = []
    for s in store.all_studies():
        sm = audit.summary(s)
        out.append({"id": s.id, "title": s.title, "status": s.status, "date": s.date, "study_by": s.study_by,
                    "steps": sm["steps"], "verified": sm["verified"], "errors": sm["errors"],
                    "proxy": bool(s.proxy_file), "approved_by": s.approved_by,
                    "cost_inr": s.cost_inr, "ai_runs": s.ai_runs,
                    "cycle_min": round(s.total_cycle_time_s / 60, 2),
                    "video_min": round(s.video_duration_s / 60, 2)})
    return out


@app.post("/api/studies")
async def upload(background: BackgroundTasks, file: UploadFile = File(...), title: str = Form(""),
                 study_by: str = Form(""), hint: str = Form("")):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"Unsupported file type {ext}. Use MP4 or MTS.")
    sid = uuid.uuid4().hex[:12]
    d = store.folder(sid)
    with open(d / f"original{ext}", "wb") as out:
        shutil.copyfileobj(file.file, out, length=8 * 1024 * 1024)
    study = Study(id=sid, title=title.upper(), study_by=study_by.upper(),
                  date=dt.date.today().strftime("%d/%m/%Y"), video_file=f"original{ext}")
    store.save(study)
    background.add_task(pipeline.process, sid, hint)
    return _out(study)


@app.get("/api/studies/{study_id}")
def get_study(study_id: str):
    s = _get(study_id)
    most.compute_study(s)  # refresh audit with current rules
    return _out(s)


@app.put("/api/studies/{study_id}")
def update_study(study_id: str, body: dict):
    s = _get(study_id)
    before = _content(s)
    for k in ("title", "study_by", "date", "source"):
        if k in body:
            setattr(s, k, str(body[k]))
    if "operations" in body:
        s.operations = [Operation.model_validate(o) for o in body["operations"]]
    most.compute_study(s)
    if s.approved_by and _content(s) != before:
        s.approved_by = s.approved_at = ""   # data changed after approval -> needs re-approval
    store.save(s)
    return _out(s)


@app.post("/api/studies/{study_id}/approve")
def approve(study_id: str, body: dict):
    s = _get(study_id)
    most.compute_study(s)
    name = str(body.get("name", "")).strip().upper()
    if not name:
        raise HTTPException(400, "Enter the name of the approving expert")
    ok, why = audit.can_approve(s)
    if not ok:
        raise HTTPException(400, why)
    s.approved_by, s.approved_at = name, dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    store.save(s)
    return _out(s)


@app.post("/api/studies/{study_id}/unapprove")
def unapprove(study_id: str):
    s = _get(study_id)
    s.approved_by = s.approved_at = ""
    store.save(s)
    return _out(s)


@app.post("/api/studies/{study_id}/reprocess")
def reprocess(study_id: str, background: BackgroundTasks, hint: str = Form(""), force: bool = Form(False)):
    _get(study_id)
    background.add_task(pipeline.process, study_id, hint, force)
    return {"ok": True}


@app.get("/api/studies/{study_id}/video")
def get_video(study_id: str):
    s = _get(study_id)
    if not s.proxy_file:
        raise HTTPException(404, "Video not ready")
    return FileResponse(store.folder(study_id) / s.proxy_file, media_type="video/mp4")


@app.get("/api/studies/{study_id}/excel")
def get_excel(study_id: str):
    s = _get(study_id)
    name = (s.title or "MOST_STUDY").replace(" ", "_").replace("/", "-")
    return Response(excel.export(s),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{name}_MOST.xlsx"'})


@app.delete("/api/studies/{study_id}")
def delete_study(study_id: str):
    _get(study_id)
    shutil.rmtree(store.folder(study_id), ignore_errors=True)
    return {"ok": True}


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
