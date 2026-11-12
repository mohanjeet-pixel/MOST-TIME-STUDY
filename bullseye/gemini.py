"""Gemini video analysis. One call per video, low media resolution, strict JSON output."""
import time
from pathlib import Path

from google import genai
from google.genai import errors, types

from . import config
from .models import AIResult

PROMPT = """You are a senior Industrial Engineer doing a BasicMOST work measurement study
from a shop-floor video. Watch the main operator only.

Break the work into MAIN OPERATIONS (logical groups, e.g. "MAGNETIC TACKLE ENGAGEMENT WITH SHEET",
"LIFTING - MOVING - PLACING", "SURFACE TREATMENT") and each into SUB-OPERATIONS that each map
to ONE MOST activity:

- WALK: operator walks. Count steps carefully; give a min-max range.
- GET: reaches or walks to an object AND grasps it ("WITH IN REACH GRASP THE PENDENT").
- GRASP: grasps an object already at hand.
- MOVE_OBJECT: moves a held object a short free distance (give distance_in).
- PUSH_PULL: presses a button, pushes/pulls a lever, switch, crank (give distance_in).
- PLACE_ASIDE: puts something down with no accuracy.
- PLACE: places with some adjustment. POSITION: positions accurately / heavy / into fixture.
- INSERT_ALIGN: inserts or aligns to a point. INSPECT: visual check.
- SIT_STAND: sits down or stands up (difficulty adjust = with adjustments, e.g. sliding the chair). BEND_ARISE: bends down and comes back up (e.g. to the floor).
  BODY_LARGE: stand-and-bend, bend-and-sit, climb on/off, walk through a door.
- TOOL_USE: work done WITH a tool or on equipment. Set tool_action + tool_count (count what you see):
  fastening/loosening -> FINGER_SPINS, WRIST_TURNS (screwdriver/ratchet/T-wrench by wrist),
  WRENCH_WRIST_STROKES, WRIST_CRANKS, HAMMER_TAPS, RATCHET_ARM_TURNS, T_WRENCH_TURNS (2 hands),
  WRENCH_ARM_STROKES, ARM_CRANKS, HAMMER_STRIKES, POWER_WRENCH (impact/nut runner, count = fasteners,
  difficulty simple = small <=6 mm, adjust = up to 25 mm);
  cutting -> WIRE_CUT, PLIERS_SECURE, SCISSORS_CUTS, KNIFE_SLICES; cleaning -> AIR_CLEAN, BRUSH_CLEAN,
  WIPE_CLOTH (count = sq ft); measuring -> MEASURE_PROFILE_GAUGE, MEASURE_FIXED_SCALE, FEELER_GAUGE,
  MEASURE_TAPE, DEPTH_MICROMETER, OD_MICROMETER, ID_MICROMETER; turning a crank/handwheel -> CRANK_REVS
  (count = revolutions); recording -> WRITE_DIGITS, WRITE_WORDS, MARK_DIGITS; reading/checking ->
  INSPECT_POINTS, READ_DIGITS, READ_WORDS, COMPARE, READ_GAUGE, READ_SCALE, READ_VERNIER, READ_TABLE,
  FEEL_HEAT, FEEL_DEFECT; KEYBOARD_WORDS, KEYPAD_DIGITS. Getting/placing the tool are separate GET/PLACE steps.
  Use "LOOSEN" in the description when loosening.
- PROCESS: only machine/crane time the operator waits for, or continuous work no TOOL_USE column
  fits (welding, grinding, large-area brushing). Timestamps must cover the full duration.

Rules:
- Timestamps MM:SS.s with tenths of a second (e.g. 01:07.4), in order, no overlaps. Every visible action of the operator must be covered.
- Description: UPPER CASE, max ~8 words, start with the MOST verb, include counts/distances.
  Never start with "OPERATOR", "PROCESS" or "THE OPERATOR". Sentence PATTERNS (company style):
    WALK            "WALK 5-8 STEPS" | "WALK 5-8 STEPS TO <PLACE>" | "TURN AND WALK 2-3 STEPS BACK TO HOME POSITION"
    GET (in reach)  "WITH IN REACH GRASP THE <OBJECT>" | heavy: "WITH IN REACH GET THE <OBJECT>"
    GET (walking)   "WALK 3-4 STEPS AND GET THE <OBJECT>"
    GRASP           "GRASP THE <OBJECT> IN HAND" | "GRASP THE <OBJECT> IN ONE HAND FOR GUIDE"
    MOVE_OBJECT     "MOVE <OBJECT> 3 INCHES WITH ORIENTATION"
    PUSH_PULL       "PUSH /PULL 3 INCHES LEVER TO OPEN THE <OBJECT>" | "PUSH THE <CONTROL> BUTTON TO <RESULT>"
    POSITION        "POSITION THE <OBJECT> INTO <PLACE>"
    PLACE           "PLACE THE <OBJECT> INTO <PLACE>"
    PLACE_ASIDE     "PLACE ASIDE THE <OBJECT>"
    INSERT_ALIGN    "INSERT <OBJECT> 2 INCHES INTO <PLACE>" | "ALIGN THE <OBJECT> TO <POINT>"
    INSPECT         "INSPECT THE <WHAT> CONDITION"
    BODY            "BEND AND ARISE TO GET THE <OBJECT>" | "SIT ON THE <SEAT>" | "CLIMB ON THE <PLATFORM>"
    TOOL_USE        "FASTEN <N> BOLTS WITH POWER WRENCH" | "FASTEN <PART> <N> TURNS WITH <TOOL>"
                    "LOOSEN <PART> <N> STROKES WITH <TOOL>" | "WRITE <N> DIGITS ON THE <DOCUMENT>" | "READ THE <GAUGE>"
    PROCESS         "<VERB> <WHAT> <AMOUNT>" e.g. "SURFACE TREAT 15 SQ.FT", "CRANE TRAVEL TO <PLACE>"
  <OBJECT>, <PLACE>, <CONTROL> ... = the real name of the thing you SEE in THIS video (bolt, frame, engine,
  wrench, hoist ...). The patterns give the wording only, never the content. NEVER name an object,
  tool or control (pendent, tackle, crane, lever ...) that is not visible in this video.
- Operation names: UPPER CASE noun phrase of what is achieved, like "MAGNETIC TACKLE ENGAGEMENT WITH SHEET",
  "LIFTING - MOVING - PLACING", "SURFACE TREATMENT".
- difficulty: simple = light, loose, one point, button; adjust = needs adjustment, resistance,
  two points; precise = care, precision, heavy pressure, blind/obstructed.
- Ignore idle waiting/talking unless it is part of the process (then use PROCESS).

ACCURACY RULES (an expert will check every step against the video):
- Report ONLY what is visible in the frames. Never add steps that "usually" happen in such a process.
- Every timestamp must point to the moment the action is actually visible.
- If an action is partly hidden, out of frame or you are inferring it, still list it but set confidence = low.
- If a count (steps, inches) is estimated rather than clearly seen, set confidence = medium.
- The walk step count in the description must equal walk_steps_min/max.
- NO REPETITION LOOPS: never output the same step or group of steps again and again. If a motion really
  repeats back-to-back (e.g. the same bolt turned, 4 bolts fastened), list it ONCE with repeat_count = the
  number of repetitions you counted, and start/end spanning all repetitions. repeat_count = 1 otherwise.
- Counts must fit the time you see: a wrist turn / stroke / crank takes about 0.7 s, a finger spin
  0.3 s, a walking step 0.6 s, a hammer strike 0.5 s. Never report more turns or steps than can happen
  between start and end. If you cannot count them, give the count that fits the duration, confidence medium.
- Timestamps must be read from the video. Never fill time with evenly spaced (1.0 s, 1.0 s ...) guesses;
  if you cannot see what happens in a period, leave it out.
- Never count the same motion twice: if a WALK step brings the operator to an object, the next
  GET is within reach (walk_steps null).
- Each sub-operation is ONE motion. Do not stretch a step over idle time; MOST is the normal-pace
  standard, so the sum of steps is normally LESS than the video time.
"""


def settings_key(hint: str, duration_s: float) -> str:
    """Everything that changes the AI answer. A cached result is reused only if all of it is identical."""
    import hashlib
    import json
    parts = [PROMPT, json.dumps(AIResult.model_json_schema(), sort_keys=True), config.GEMINI_MODEL,
             str(config.THINKING_BUDGET), str(pick_fps(duration_s)), str(config.AI_SEED), "LOW", "t0", hint.strip()]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def _client() -> genai.Client:
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    # google-genai 3.x defaults to API v1, which rejects JSON-schema output; v1beta supports it.
    return genai.Client(api_key=config.GEMINI_API_KEY, http_options=types.HttpOptions(api_version="v1beta"))


def pick_fps(duration_s: float) -> float:
    """More frames for short clips (sharper timing), fewer for long ones (cost).
    FRAME_BUDGET frames x ~66 tokens at low media resolution."""
    if not duration_s:
        return 1.0
    return round(max(1.0, min(config.MAX_FPS, config.FRAME_BUDGET / duration_s)), 2)


RETRY_CODES = (429, 500, 502, 503, 504)

# google-genai talks HTTP through httpx or its fork httpx2, depending on the version installed.
_NET_ERRORS: tuple = (ConnectionError, TimeoutError)
for _mod in ("httpx2", "httpx"):
    try:
        _NET_ERRORS += (__import__(_mod).TransportError,)
    except Exception:  # noqa: BLE001
        pass
_NET_WORDS = ("disconnected", "connection", "timed out", "timeout", "reset", "eof")


def _transient(e: Exception) -> bool:
    """Overload (HTTP 429/5xx) or a dropped connection ("Server disconnected", reset, timeout)."""
    if isinstance(e, errors.APIError):
        return getattr(e, "code", None) in RETRY_CODES
    if isinstance(e, _NET_ERRORS):
        return True
    return any(w in str(e).lower() for w in _NET_WORDS)


def _with_retry(fn, waits=(0, 5, 15, 30)):
    last = None
    for w in waits:
        time.sleep(w)
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            if not _transient(e):
                raise
            last = e
    raise RuntimeError(f"Could not reach Google Gemini (network/overload, tried {len(waits)} times). "
                       f"Check the internet connection and click 'Re-run AI'. Last error: {last}")


def analyse(video: Path, hint: str = "", duration_s: float = 0.0) -> tuple[AIResult, dict]:
    client = _client()
    f = _with_retry(lambda: client.files.upload(file=str(video), config={"mime_type": "video/mp4"}))
    while f.state and f.state.name == "PROCESSING":
        time.sleep(3)
        f = _with_retry(lambda: client.files.get(name=f.name))
    if f.state and f.state.name == "FAILED":
        raise RuntimeError("Gemini could not process the video")

    try:
        parts = [
            types.Part(
                file_data=types.FileData(file_uri=f.uri, mime_type="video/mp4"),
                video_metadata=types.VideoMetadata(fps=pick_fps(duration_s)),
            ),
            types.Part(text=PROMPT + (f"\nContext from the engineer: {hint}" if hint else "")),
        ]
        gen_cfg = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AIResult,
            media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
            temperature=0.0,          # no randomness: most likely answer every time
            seed=config.AI_SEED,      # fixed seed: same input -> same output as far as Google allows
            thinking_config=types.ThinkingConfig(thinking_budget=config.THINKING_BUDGET),
        )
        # Google returns 503/429 when overloaded: wait and retry, then fall back to the cheaper model.
        attempts = [(config.GEMINI_MODEL, 0), (config.GEMINI_MODEL, 15), (config.GEMINI_MODEL, 45)]
        if config.FALLBACK_MODEL and config.FALLBACK_MODEL != config.GEMINI_MODEL:
            attempts += [(config.FALLBACK_MODEL, 5), (config.FALLBACK_MODEL, 30)]
        last_err = None
        for model, wait in attempts:
            time.sleep(wait)
            try:
                resp = client.models.generate_content(
                    model=model, contents=[types.Content(role="user", parts=parts)], config=gen_cfg)
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
                if not _transient(e):
                    raise
        else:
            raise RuntimeError("Google Gemini is overloaded or unreachable right now (tried "
                               f"{len(attempts)} times). Click 'Re-run AI' in a few minutes. Last error: {last_err}")
    finally:
        try:
            client.files.delete(name=f.name)
        except Exception:
            pass

    result = resp.parsed if isinstance(resp.parsed, AIResult) else AIResult.model_validate_json(resp.text)
    u = resp.usage_metadata
    usage = {
        "model": model,
        "in": (u.prompt_token_count or 0) if u else 0,
        "out": (u.candidates_token_count or 0) if u else 0,
        "think": (getattr(u, "thoughts_token_count", 0) or 0) if u else 0,
    }
    return result, usage
