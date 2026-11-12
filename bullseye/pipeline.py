"""Upload -> proxy video -> Gemini -> MOST engine -> saved study."""
import hashlib
import json
import re
import traceback

from . import config, gemini, most, store, video
from .models import Activity, AIResult, Operation, Step, ToolAction


def mmss_to_s(t: str) -> float | None:
    try:
        parts = [float(x) for x in str(t).strip().split(":")]
    except ValueError:
        return None
    s = 0.0
    for p in parts:
        s = s * 60 + p
    return s


_LEAD = re.compile(r"^(?:THE\s+)?(?:OPERATOR|WORKER|PERSON)\s+|^PROCESS\s*[:\-]?\s+(?=\w)")
_VERB_FIX = [(re.compile(p), r) for p, r in [
    (r"^WALKS\b", "WALK"), (r"^GRASPS\b", "GRASP"), (r"^PLACES ASIDE\b", "PLACES ASIDE"), (r"^PUSHES\b", "PUSH"),
    (r"^PULLS\b", "PULL"), (r"^INSERTS\b", "INSERT"), (r"^INSPECTS\b", "INSPECT"), (r"^POSITIONS\b", "POSITION"),
    (r"^MOVES\b", "MOVE"), (r"^TIGHTENING\b", "FASTEN"), (r"^TIGHTENS?\b", "FASTEN"), (r"^LOOSENING\b", "LOOSEN"),
    (r"^SIGNING\b", "SIGN"), (r"^CHECKING\b", "CHECK"), (r"^WALKING\b", "WALK"), (r"^WITHIN REACH\b", "WITH IN REACH"),
    (r"\bSTEPS? STEPS\b", "STEPS"), (r"\bPUSH\s*/\s*PULL\b", "PUSH /PULL")]]


def clean_text(t: str) -> str:
    """Company wording: upper case, starts with the MOST verb, no 'OPERATOR ...' / 'PROCESS ...' prefix."""
    t = " ".join(str(t or "").upper().replace("’", "'").split()).rstrip(".")
    for _ in range(2):
        t = _LEAD.sub("", t)
    for rx, rep in _VERB_FIX:
        t = rx.sub(rep, t)
    return t


def ai_to_operations(ai: AIResult) -> list[Operation]:
    ops = []
    for i, aop in enumerate(ai.operations):
        steps = []
        for a in aop.steps:
            # Power-wrench index is per fastener: the fastener count goes into Freq
            per_fastener = a.tool_action == ToolAction.POWER_WRENCH and a.tool_count and a.tool_count > 1
            steps.append(Step(
                tool_action=a.tool_action if a.activity == Activity.TOOL_USE else None,
                tool_count=a.tool_count if a.activity == Activity.TOOL_USE else None,
                freq=(a.tool_count if per_fastener else 1) * max(1, a.repeat_count or 1),
                description=clean_text(a.description),
                activity=a.activity,
                start_s=mmss_to_s(a.start),
                end_s=mmss_to_s(a.end),
                walk_steps_min=a.walk_steps_min,
                walk_steps_max=a.walk_steps_max,
                distance_in=a.distance_in,
                heavy=a.heavy,
                difficulty=a.difficulty,
                offline=a.offline,
                confidence=a.confidence.value,
                oprt=config.DEFAULT_OPRT,
            ))
        ops.append(Operation(opn_no=(i + 1) * 10, name=clean_text(aop.name), steps=collapse_loops(steps)))
    return ops


def collapse_loops(steps: list[Step], min_reps: int = 3, max_block: int = 4) -> list[Step]:
    """Language models sometimes get stuck repeating the same step(s). A block of 1-4 identical steps
    appearing 3+ times back-to-back is kept ONCE (Freq unchanged) and marked; the audit blocks approval
    until the expert has checked the video and set the real Freq. Repetitions the AI may have invented
    are never counted into the MOST time."""
    sig = lambda s: (s.activity, s.description)
    out, i, n = [], 0, len(steps)
    while i < n:
        best = None
        for k in range(1, max_block + 1):
            reps = 1
            while i + (reps + 1) * k <= n and all(sig(steps[i + reps * k + j]) == sig(steps[i + j]) for j in range(k)):
                reps += 1
            if reps >= min_reps and (best is None or reps * k > best[0] * best[1]):
                best = (reps, k)
        if best:
            reps, k = best
            end = steps[i + reps * k - 1].end_s
            for s in steps[i:i + k]:
                s.ai_repeat, s.ai_repeat_end = reps, end
                out.append(s)
            i += reps * k
        else:
            out.append(steps[i])
            i += 1
    return out


def file_hash(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:24]


def analyse_cached(src, proxy, hint: str, duration_s: float, force: bool) -> tuple[AIResult, dict, bool]:
    """Same video + same prompt/model/settings -> the saved AI answer (identical result, Rs 0).
    Only a changed video, prompt, model, setting or hint - or force - calls Gemini again."""
    key = f"{file_hash(src)}_{gemini.settings_key(hint, duration_s)}"
    f = config.CACHE_DIR / f"{key}.json"
    if f.exists() and not force:
        data = json.loads(f.read_text(encoding="utf-8"))
        return AIResult.model_validate(data["ai"]), data["usage"], True
    ai, u = gemini.analyse(proxy, hint, duration_s)
    if u["model"] != config.GEMINI_MODEL:  # backup model used (Google overloaded): don't freeze that answer
        return ai, u, False
    f.write_text(json.dumps({"ai": ai.model_dump(mode="json"), "usage": u}), encoding="utf-8")
    return ai, u, False


def process(study_id: str, hint: str = "", force: bool = False) -> None:
    study = store.load(study_id)
    if not study:
        return
    study.status, study.error = "processing", ""
    store.save(study)
    try:
        d = store.folder(study_id)
        src = d / study.video_file
        proxy = video.make_proxy(src, d / "proxy.mp4")
        study.proxy_file = proxy.name
        study.video_duration_s = video.probe_duration(src) or video.probe_duration(proxy)
        store.save(study)

        ai, u, cached = analyse_cached(src, proxy, hint, study.video_duration_s, force)
        study.operations = ai_to_operations(ai)
        if not study.title:
            study.title = ai.process_name.upper()
        study.ai_cached = cached
        run_usd = 0.0 if cached else config.cost_usd(u["in"], u["out"], u["think"], u["model"])
        study.model = u["model"]
        study.tokens_in, study.tokens_out, study.tokens_think = u["in"], u["out"], u["think"]
        study.ai_runs += 0 if cached else 1
        study.cost_usd = round(study.cost_usd + run_usd, 6)
        study.cost_inr = round(study.cost_usd * config.USD_INR, 4)
        study.last_run_inr = round(run_usd * config.USD_INR, 4)
        study.approved_by = study.approved_at = ""
        most.compute_study(study)
        study.status = "ready"
    except Exception as e:
        traceback.print_exc()
        study.status, study.error = "error", str(e)
    store.save(study)
