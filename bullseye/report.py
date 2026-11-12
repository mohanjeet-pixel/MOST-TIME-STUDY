"""Study analysis for the report: KPIs, breakdowns, Pareto and data-card based improvement ideas.

All numbers are derived from the (expert-verified) MOST steps - no AI, no cost.
"""
from . import config, most
from .models import Activity, Step, Study

CATEGORIES = ["Value-adding work", "Handling", "Movement (walk / body)", "Check / record"]
CAT_COLORS = ["#16A34A", "#2563EB", "#E11B22", "#CA8A04"]


def category(s: Step) -> str:
    a = s.activity
    if a in (Activity.SIT_STAND, Activity.BEND_ARISE, Activity.BODY_LARGE) or (a == Activity.WALK and s.index >= 3):
        return CATEGORIES[2]
    if a == Activity.INSPECT or (a == Activity.TOOL_USE and s.code in ("M", "T", "R", "W", "K")):
        return CATEGORIES[3]
    if a in (Activity.PROCESS, Activity.PUSH_PULL, Activity.TOOL_USE):
        return CATEGORIES[0]
    return CATEGORIES[1]


def _sec(index: float, s: Step) -> float:
    return index * config.SECONDS_PER_INDEX * s.freq / (s.div_freq or 1)


def kaizen(study: Study, steps: list[tuple[int, int, Step]]) -> list[dict]:
    """Improvement opportunities with an estimated MOST saving per cycle (seconds)."""
    ideas = []

    def add(title, action, rows, saving):
        if rows and saving > 0.05:
            ideas.append({"title": title, "action": action, "count": len(rows), "saving_s": round(saving, 1),
                          "where": ", ".join(f"{o}.{n}" for o, n, _ in rows[:8]) + (" ..." if len(rows) > 8 else "")})

    walks = [(o, n, s) for o, n, s in steps if s.activity == Activity.WALK and s.index >= 10 and not s.manual]
    sav = sum(_sec(s.index - most.a_index((most.steps_for(s) or 0) / 2, None), s) for _, _, s in walks)
    add("Long walks", "Bring parts, tools and bins to the point of use (re-layout, kitting, gravity racks). "
        "Saving shown = walking distance halved.", walks, sav)

    body = [(o, n, s) for o, n, s in steps if s.code == "B"]
    add("Bending / body motion", "Raise parts and bins to waist height, use tilt tables - removes B3-B16 motions.",
        body, sum(_sec(s.index, s) for _, _, s in body))

    heavy = [(o, n, s) for o, n, s in steps if s.activity in (Activity.GET, Activity.GRASP) and s.heavy]
    add("Heavy / difficult gain control", "Use a balancer, hoist, handles or trolley so G3 becomes G1.",
        heavy, sum(_sec(2, s) for _, _, s in heavy))

    pos = [(o, n, s) for o, n, s in steps if s.code == "P" and s.index >= 6]
    add("Precise positioning (P6)", "Add locating pins, guides, chamfers or a fixture so P6 becomes P3 / P1.",
        pos, sum(_sec(3, s) for _, _, s in pos))

    fasten = [(o, n, s) for o, n, s in steps if s.code in ("F", "L") and s.index >= 10
              and s.tool_action and s.tool_action.value != "POWER_WRENCH"]
    add("Manual fastening", "Use a power wrench / nut runner (F3-F6 per fastener) instead of hand turns and strokes.",
        fasten, sum(_sec(s.index - 6, s) for _, _, s in fasten))

    check = [(o, n, s) for o, n, s in steps if category(s) == CATEGORIES[3] and s.index >= 10]
    add("Long inspection / measuring", "Use a go/no-go gauge or poka-yoke so the check becomes a gauge read (T3).",
        check, sum(_sec(s.index - 3, s) for _, _, s in check))

    off = [(o, n, s) for o, n, s in steps if s.offline]
    add("External work (off-line)", "These steps can be done while the machine runs - move them out of the "
        "machine-stopped time (SMED).", off, sum(s.cycle_time for _, _, s in off))

    return sorted(ideas, key=lambda i: -i["saving_s"])


def analyse(study: Study) -> dict:
    steps = [(op.opn_no, n, s) for op in study.operations for n, s in enumerate(op.steps, 1)]
    video = study.video_duration_s or 0.0
    total = study.total_cycle_time_s
    offline = sum(s.cycle_time for _, _, s in steps if s.offline)
    covered = sum(s.end_s - s.start_s for _, _, s in steps
                  if s.start_s is not None and s.end_s is not None and s.end_s > s.start_s)
    std = total * (1 + config.ALLOWANCE_PCT / 100)

    by_cat = {c: 0.0 for c in CATEGORIES}
    by_code: dict[str, float] = {}
    for _, _, s in steps:
        by_cat[category(s)] += s.cycle_time
        by_code[s.code or "?"] = by_code.get(s.code or "?", 0) + s.cycle_time

    return {
        "video_s": video,
        "most_s": total,
        "online_s": total - offline,
        "offline_s": offline,
        "allowance_pct": config.ALLOWANCE_PCT,
        "std_s": std,
        "per_hour": 3600 / std if std else 0,
        "per_shift": config.SHIFT_MIN * 60 / std if std else 0,
        "shift_min": config.SHIFT_MIN,
        "method_eff": total / video if video else 0,
        "gap_s": video - total,
        "idle_s": max(0.0, video - covered),
        "steps": len(steps),
        "by_op": [{"opn": op.opn_no, "name": op.name, "steps": len(op.steps), "video_s": op.video_time,
                   "most_s": op.cycle_time} for op in study.operations],
        "by_cat": by_cat,
        "by_code": dict(sorted(by_code.items(), key=lambda kv: -kv[1])),
        "pareto": [{"opn": o, "n": n, "desc": s.description, "code": f"{s.code}{s.index}", "most_s": s.cycle_time}
                   for o, n, s in sorted(steps, key=lambda t: -t[2].cycle_time)[:10]],
        "kaizen": kaizen(study, steps),
    }
