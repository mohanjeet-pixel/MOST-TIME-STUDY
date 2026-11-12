"""Fault finder: deterministic checks an IE expert would do. Free (no AI), runs on every save.

Levels: error = almost certainly wrong (e.g. invented timestamp) - blocks approval
        warn  = likely wrong, expert must look
        info  = worth a glance
"""
import re

from . import config
from .models import Activity, Study

STEP_RE = re.compile(r"(\d+)\s*(?:-|TO)\s*(\d+)\s*STEP|(\d+)\s*STEP")
from .most import FIXED_TOOLS as NO_COUNT  # tool columns chosen by type/difficulty, no count needed
# words in a PROCESS description that the Tool Use card covers (expert should code them there)
TOOL_WORDS = [("TIGHTEN", "F fasten"), ("BOLT", "F fasten"), ("SCREW", "F fasten"), ("NUT ", "F fasten"),
              ("LOOSEN", "L loosen"), ("HAMMER", "F strikes"), ("SIGN", "R record"), ("WRITE", "R record"),
              ("DOCUMENT", "R record / T read"), ("READ ", "T read"), ("MEASURE", "M measure"), ("WIPE", "S wipe"),
              (" CUT", "C cut"), ("TYPE", "W keyboard"), ("CRANK", "M crank"), ("HANDWHEEL", "M crank")]
# object names from the reference sheet; the AI has copied them into unrelated videos before
EXAMPLE_WORDS = ["PENDENT", "TACKLE", "MAGNETIC", "SCRUBER"]


def _t(s):
    return f"{int(s // 60):02d}:{s % 60:04.1f}" if s is not None else "?"


INCH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:INCH|INCHES|IN\b|\")")


def _add(lst, level, msg):
    lst.append({"level": level, "msg": msg})


def run(study: Study) -> Study:
    dur = study.video_duration_s or 0
    study.issues = []
    prev_end = 0.0
    covered = 0.0
    total_steps = 0
    prev_step = None

    for op in study.operations:
        if not op.steps:
            _add(study.issues, "warn", f"Operation {op.opn_no} has no steps")
        # evenly spaced timestamps = the AI filled time instead of reading the video
        run = 1
        for a, b in zip(op.steps, op.steps[1:]):
            same = (None not in (a.start_s, a.end_s, b.start_s, b.end_s) and abs(b.start_s - a.end_s) < 0.05
                    and abs((b.end_s - b.start_s) - (a.end_s - a.start_s)) < 0.05)
            run = run + 1 if same else 1
            if run == 6:
                _add(study.issues, "warn", f"Operation {op.opn_no}: 6+ steps in a row have exactly the same duration "
                                           f"({a.end_s - a.start_s:.1f} s) — timestamps look generated, not read from the video")
        for n, s in enumerate(op.steps, 1):
            total_steps += 1
            iss: list[dict] = []
            st, en = s.start_s, s.end_s
            desc = (s.description or "").upper()

            # --- timestamps: the main hallucination guard ---
            if st is None or en is None:
                _add(iss, "warn", "No start/end time — cannot be verified against the video")
            else:
                if en <= st:
                    _add(iss, "error", "End time is not after start time")
                if dur and (st > dur + 0.5 or en > dur + 0.5):
                    _add(iss, "error", f"Time is beyond the video end ({dur:.1f} s) — step does not exist in the video")
                if st < prev_end - 0.3:
                    _add(iss, "warn", f"Overlaps previous step by {prev_end - st:.1f} s")
                gap = st - prev_end
                if gap > max(3.0, 0.05 * dur):
                    _add(iss, "info", f"{gap:.1f} s of video before this step is not covered — missed activity or idle?")
                if en > st:
                    covered += en - st
                prev_end = max(prev_end, en)

            obs = (en - st) if st is not None and en is not None and en > st else None

            # --- MOST standard vs what the video shows ---
            if obs and s.activity != Activity.PROCESS and s.index and s.ai_repeat <= 1:
                std = s.index * config.STD_SECONDS_PER_INDEX * s.freq / (s.div_freq or 1)
                if obs > 4 * std + 2:
                    _add(iss, "warn", f"Observed {obs:.1f} s but MOST standard is {std:.1f} s — index too low, waiting inside step, or should be split")
                elif std > 3 * obs and std - obs > 3:
                    _add(iss, "error", f"Impossible: video shows {obs:.1f} s but MOST says {std:.1f} s (operator would be "
                                       f"{std / obs:.0%} of normal pace). Count, Freq or index is too high — correct it to what the video shows")
                elif obs < std / 4 - 1:
                    _add(iss, "warn", f"Observed {obs:.1f} s but MOST standard is {std:.1f} s — index looks too high")
            if obs and obs > 90 and s.activity != Activity.PROCESS:
                _add(iss, "warn", f"{obs:.0f} s is very long for one element — split it")

            # --- walking plausibility ---
            if s.activity == Activity.WALK:
                if s.walk_steps_min is None and s.walk_steps_max is None and s.distance_in is None:
                    _add(iss, "warn", "Walk without a step count")
                elif obs and s.walk_steps_max and s.walk_steps_max / obs > 3:
                    _add(iss, "warn", f"{s.walk_steps_max} steps in {obs:.1f} s is faster than running — step count or times wrong")
                if s.walk_steps_min and s.walk_steps_max and s.walk_steps_min > s.walk_steps_max:
                    _add(iss, "error", "Steps min is greater than steps max")

            # --- text vs data consistency (AI saying one thing, coding another) ---
            m = STEP_RE.search(desc)
            if m and s.activity in (Activity.WALK, Activity.GET, Activity.PUSH_PULL):
                lo = int(m.group(1) or m.group(3))
                hi = int(m.group(2) or m.group(3))
                if (s.walk_steps_min is not None and s.walk_steps_min != lo) or (s.walk_steps_max is not None and s.walk_steps_max != hi):
                    _add(iss, "warn", f"Text says {lo}-{hi} steps but data says {s.walk_steps_min}-{s.walk_steps_max}")
            mi = INCH_RE.search(desc)
            if mi and s.distance_in is not None and abs(float(mi.group(1)) - s.distance_in) > 1:
                _add(iss, "info", f"Text says {mi.group(1)}\" but distance is {s.distance_in:g}\"")
            if s.activity == Activity.WALK and "WALK" not in desc and "STEP" not in desc and "MOVE" not in desc and "TURN" not in desc:
                _add(iss, "info", "Activity is Walk but text does not describe walking")

            # --- double counting (main cause of MOST > video) ---
            if (s.activity == Activity.GET and prev_step is not None and prev_step.activity == Activity.WALK
                    and (s.walk_steps_min or s.walk_steps_max)):
                _add(iss, "warn", "Walk counted twice: previous step is already WALK, so this GET should be within reach (no steps)")
            if s.activity == Activity.TOOL_USE:
                if s.tool_action is None:
                    _add(iss, "warn", "Tool use without a data-card column (tool action) — index cannot be looked up")
                elif s.tool_action.value not in NO_COUNT and s.tool_count is None:
                    _add(iss, "warn", "Tool use without a count (turns / strokes / cuts ...) — index is the lowest on the card")
            # --- AI hallucination guards ---
            if s.ai_repeat > 1 and s.review != "ok":
                span = f" ({_t(s.start_s)} to {_t(s.ai_repeat_end)})" if s.start_s is not None and s.ai_repeat_end else ""
                _add(iss, "error", f"AI wrote this step {s.ai_repeat} times in a row{span} — typical AI repetition loop. "
                                   f"Counted only once (Freq = {s.freq:g}). Watch the video: if the operator really repeats it, "
                                   "set Freq to the real count, then verify (V).")
            ex = next((w for w in EXAMPLE_WORDS if w in desc), None)
            if ex and s.review != "ok" and s.confidence != "manual":
                _add(iss, "warn", f"'{ex}' is a word from the AI wording examples — confirm a {ex.lower()} is really in this video")
            if s.activity == Activity.PROCESS and not s.manual:
                hit = next((w for w, col in TOOL_WORDS if w in desc), None)
                if hit:
                    _add(iss, "warn", f"'{hit.strip()}' is on the Tool Use card ({dict(TOOL_WORDS)[hit]}) — code it as Tool use "
                                      "with a count instead of measured process time")
            prev_step = s

            # --- basics ---
            if not desc.strip():
                _add(iss, "error", "Empty description")
            if s.index == 0 and not s.manual:
                _add(iss, "warn", "Index is 0")
            if s.freq <= 0 or s.div_freq <= 0:
                _add(iss, "error", "Frequency must be greater than 0")

            # --- AI self-confidence ---
            if s.confidence == "low":
                _add(iss, "warn", "AI was unsure (action partly hidden/out of frame) — watch this step")
            elif s.confidence == "medium":
                _add(iss, "info", "AI confidence medium — counts may be estimated")

            if s.review == "flag":
                _add(iss, "error", f"Flagged by expert: {s.note or 'no comment'}")
            s.issues = iss

    if dur and total_steps:
        cov = covered / dur
        if cov < 0.6:
            _add(study.issues, "warn", f"Only {cov:.0%} of the video is covered by steps — activities may be missing")
        if study.total_cycle_time_s > dur * 1.05:
            msg = (f"MOST time {study.total_cycle_time_s:.0f} s is more than the video {dur:.0f} s. "
                   "MOST is the normal-pace standard, so it is normally lower: look for walks counted twice, "
                   "indexes too high, Freq > 1, or extra steps.")
            if abs(config.SECONDS_PER_INDEX - config.STD_SECONDS_PER_INDEX) > 0.01:
                msg += f" Sec/Index is {config.SECONDS_PER_INDEX} (data card = 0.36)."
            # > 130 %: the operator would have worked far above normal pace for the whole video - not credible
            _add(study.issues, "error" if study.total_cycle_time_s > dur * 1.3 else "warn", msg)
    if not study.operations:
        _add(study.issues, "error", "No operations")
    return study


def summary(study: Study) -> dict:
    steps = [s for op in study.operations for s in op.steps]
    lv = lambda L: sum(1 for s in steps for i in s.issues if i["level"] == L) + sum(1 for i in study.issues if i["level"] == L)
    return {
        "steps": len(steps),
        "verified": sum(1 for s in steps if s.review == "ok"),
        "flagged": sum(1 for s in steps if s.review == "flag"),
        "errors": lv("error"),
        "warnings": lv("warn"),
        "low_conf": sum(1 for s in steps if s.confidence == "low"),
    }


def can_approve(study: Study) -> tuple[bool, str]:
    sm = summary(study)
    if not sm["steps"]:
        return False, "No steps to approve"
    if sm["errors"]:
        return False, f"{sm['errors']} error(s) must be fixed first"
    if sm["verified"] < sm["steps"]:
        return False, f"{sm['steps'] - sm['verified']} step(s) not yet verified by the expert"
    return True, ""
