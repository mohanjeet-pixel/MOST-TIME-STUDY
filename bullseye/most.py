"""BasicMOST rules engine: activity attributes -> code + index -> cycle time.

Every table below is copied from the BasicMOST data cards (General Move, Controlled Move,
Tool Use, Equipment Use, TMU intervals). Deterministic on purpose: the AI only describes what
happened, this file does the maths, so the same data always gives the same index.

Time: index x 10 = TMU, 1 TMU = 0.036 s  ->  cycle time = index x SECONDS_PER_INDEX (0.36).
"""
from . import config
from .models import Activity, Difficulty, Operation, Step, Study, ToolAction

S, A_, P_ = Difficulty.SIMPLE, Difficulty.ADJUST, Difficulty.PRECISE

# ---- TMU intervals & conversions card: (index, upper TMU limit of its interval) ----
INTERVALS = [(0, 0), (1, 17), (3, 42), (6, 77), (10, 126), (16, 196), (24, 277), (32, 366),
             (42, 476), (54, 601), (67, 736), (81, 881), (96, 1041), (113, 1216), (131, 1411),
             (152, 1621), (173, 1841), (196, 2076), (220, 2321), (245, 2571), (270, 2846),
             (300, 3146), (330, 3446)]
INDEX_SCALE = [i for i, _ in INTERVALS]


def index_for_tmu(tmu: float) -> int:
    """Index whose BasicMOST interval contains this TMU value (data card interval limits)."""
    if tmu <= 0:
        return 0
    for idx, hi in INTERVALS:
        if tmu <= hi + 0.5:
            return idx
    return round(tmu / 10)  # beyond 330: plain conversion


def nearest_index(value: float) -> int:
    return index_for_tmu(value * 10)


def by_count(table: list[tuple[int, float]], count: float | None) -> int:
    """table = [(index, max count), ...] from a data card column."""
    if count is None:
        return table[0][0]
    for idx, mx in table:
        if count <= mx:
            return idx
    last_idx, last_mx = table[-1]  # beyond the card: extrapolate proportionally
    return index_for_tmu(last_idx * 10 * count / last_mx)


# ---- General Move card ----
# A  Action distance: 0 = <=2 in, 1 = within reach, then walking steps (incl. extended values card)
A_STEPS = [(3, 2), (6, 4), (10, 7), (16, 10), (24, 15), (32, 20), (42, 26), (54, 33), (67, 40),
           (81, 49), (96, 57), (113, 67), (131, 78), (152, 90), (173, 102), (196, 115), (220, 128),
           (245, 142), (270, 158), (300, 174), (330, 191)]
INCHES_PER_STEP = 30.0
REACH_IN = 30.0
# B  Body motion
B_INDEX = {Activity.SIT_STAND: 3, Activity.BEND_ARISE: 6, Activity.BODY_LARGE: 16}
# G  Gain control: 1 = grasp light object; 3 = non-simo, heavy/bulky, blind/obstructed, disengage, interlocked
G_INDEX = {False: 1, True: 3}
# P  Placement: 1 = lay aside / loose fit; 3 = adjustments, light pressure, double placement;
#               6 = position: care/precision, heavy pressure, blind/obstructed, intermediate moves
P_INDEX = {S: 1, A_: 3, P_: 6}

# ---- Controlled Move card ----
# M  push/pull/turn without walking: 1 = <=12 in, button, switch, knob; 3 = >12 in, resistance,
#    seat/unseat, high control, 2 stages <=24 in; 6 = 2 stages >24 in
M_INDEX = {S: 1, A_: 3, P_: 6}
# M  with walking steps (incl. push/pull extended values)
M_STEPS = [(6, 2), (10, 5), (16, 9), (24, 13), (32, 17), (42, 22), (54, 28), (67, 34)]
# I  Alignment: 1 = 1 point; 3 = 2 points <=4 in; 6 = 2 points >4 in; 16 = precision
I_INDEX = {S: 1, A_: 3, P_: 6}

# ---- Tool Use / Equipment Use cards: tool action -> (code, [(index, max count)]) ----
T = ToolAction
TOOL_TABLES = {
    # F Fasten / L Loosen
    T.FINGER_SPINS: ("F", [(1, 1), (3, 2), (6, 3), (10, 8), (16, 16), (24, 25), (32, 35), (42, 47), (54, 61)]),
    T.WRIST_TURNS: ("F", [(3, 1), (6, 3), (10, 5), (16, 9), (24, 13), (32, 17), (42, 23), (54, 29)]),
    T.WRENCH_WRIST_STROKES: ("F", [(3, 1), (6, 2), (10, 3), (16, 5), (24, 8), (32, 10), (42, 13), (54, 17)]),
    T.WRIST_CRANKS: ("F", [(3, 1), (6, 3), (10, 5), (16, 8), (24, 11), (32, 15), (42, 20), (54, 25)]),
    T.HAMMER_TAPS: ("F", [(1, 1), (3, 3), (6, 6), (10, 10), (16, 16), (24, 23), (32, 30), (42, 39), (54, 50)]),
    T.RATCHET_ARM_TURNS: ("F", [(3, 1), (6, 2), (10, 4), (16, 6), (24, 9), (32, 12), (42, 15), (54, 20)]),
    T.T_WRENCH_TURNS: ("F", [(6, 1), (16, 3), (24, 6), (32, 8), (42, 11), (54, 15)]),
    T.WRENCH_ARM_STROKES: ("F", [(3, 1), (10, 2), (16, 3), (24, 4), (32, 6), (42, 8), (54, 10)]),
    T.ARM_CRANKS: ("F", [(6, 1), (10, 2), (16, 3), (24, 5), (32, 6), (42, 8), (54, 11)]),
    T.HAMMER_STRIKES: ("F", [(3, 1), (6, 3), (10, 5), (16, 8), (24, 12), (32, 16), (42, 21), (54, 27)]),
    # C Cut
    T.SCISSORS_CUTS: ("C", [(1, 1), (3, 2), (6, 4), (10, 7), (16, 11), (24, 15), (32, 20), (42, 27), (54, 33)]),
    T.KNIFE_SLICES: ("C", [(3, 1), (10, 3), (16, 4), (24, 6), (32, 9), (42, 11)]),
    # S Surface treat (sq ft; up to ~1 sq ft = spot / cavity)
    T.AIR_CLEAN: ("S", [(6, 1), (16, 3), (24, 4), (32, 7), (42, 10)]),
    T.BRUSH_CLEAN: ("S", [(6, 1), (16, 2), (24, 3), (32, 5), (42, 7)]),
    T.WIPE_CLOTH: ("S", [(3, 0.5), (10, 1), (16, 2), (32, 5), (42, 7)]),
    # R Record
    T.WRITE_DIGITS: ("R", [(1, 1), (3, 2), (6, 4), (10, 6), (16, 9), (24, 13), (32, 18), (42, 23), (54, 29)]),
    T.WRITE_WORDS: ("R", [(6, 1), (16, 2), (24, 3), (32, 4), (42, 5), (54, 7)]),
    T.MARK_DIGITS: ("R", [(1, 0), (3, 1), (6, 2), (10, 3), (16, 5), (24, 7), (32, 10), (42, 13), (54, 16)]),
    # T Think
    T.INSPECT_POINTS: ("T", [(1, 1), (3, 3), (6, 5), (10, 9), (16, 14), (24, 19), (32, 26), (42, 34), (54, 42)]),
    T.READ_DIGITS: ("T", [(1, 1), (3, 3), (6, 6), (10, 12)]),
    T.READ_WORDS: ("T", [(1, 3), (3, 8), (6, 15), (10, 24), (16, 38), (24, 54), (32, 72), (42, 94), (54, 119)]),
    T.COMPARE: ("T", [(1, 1), (3, 2), (6, 4), (10, 8), (16, 13)]),
    # W Keyboard / K Keypad (Equipment Use)
    T.KEYBOARD_WORDS: ("W", [(1, 0), (3, 1), (6, 2), (10, 4), (16, 6), (24, 8), (32, 11), (42, 15), (54, 19)]),
    T.KEYPAD_DIGITS: ("K", [(1, 2), (3, 6), (6, 11), (10, 18), (16, 28), (24, 39), (32, 52), (42, 68), (54, 85)]),
    # Controlled Move card: crank revolutions (incl. crank extended values)
    T.CRANK_REVS: ("M", [(3, 1), (6, 3), (10, 6), (16, 11), (24, 16), (32, 21), (42, 28), (54, 36)]),
}

# Columns chosen by difficulty instead of a count
TOOL_BY_DIFF = {
    T.POWER_WRENCH: ("F", {S: 3, A_: 6, P_: 6}),      # per fastener: <=1/4 in (6 mm) = 3, <=1 in (25 mm) = 6
    T.WIRE_CUT: ("C", {S: 3, A_: 6, P_: 10}),         # soft / medium / hard wire
    T.PLIERS_SECURE: ("C", {S: 1, A_: 6, P_: 16}),    # grip / twist-form loop / secure cotter pin
    T.MEASURE_PROFILE_GAUGE: ("M", {S: 10, A_: 10, P_: 10}),
    T.MEASURE_FIXED_SCALE: ("M", {S: 16, A_: 16, P_: 16}),
    T.MEASURE_TAPE: ("M", {S: 32, A_: 32, P_: 32}),
    T.FEELER_GAUGE: ("M", {S: 24, A_: 24, P_: 24}),
    T.DEPTH_MICROMETER: ("M", {S: 32, A_: 32, P_: 32}),
    T.OD_MICROMETER: ("M", {S: 42, A_: 42, P_: 42}),
    T.ID_MICROMETER: ("M", {S: 54, A_: 54, P_: 54}),
    T.READ_GAUGE: ("T", {S: 3, A_: 3, P_: 3}),
    T.READ_SCALE: ("T", {S: 6, A_: 6, P_: 6}),
    T.READ_VERNIER: ("T", {S: 10, A_: 10, P_: 10}),
    T.READ_TABLE: ("T", {S: 16, A_: 16, P_: 16}),
    T.FEEL_HEAT: ("T", {S: 6, A_: 6, P_: 6}),
    T.FEEL_DEFECT: ("T", {S: 10, A_: 10, P_: 10}),
}
FIXED_TOOLS = {t.value for t in TOOL_BY_DIFF}
LOOSEN_WORDS = ("LOOSEN", "UNSCREW", "UNTIGHT", "REMOVE", "OPEN")


def steps_for(step: Step) -> float | None:
    lo, hi = step.walk_steps_min, step.walk_steps_max
    if lo is None and hi is None:
        return None
    lo = lo if lo is not None else hi
    hi = hi if hi is not None else lo
    policy = config.STEP_RANGE_POLICY
    if policy == "max":
        return hi
    if policy == "avg":
        return (lo + hi) / 2
    return lo


def a_index(steps: float | None, distance_in: float | None) -> int:
    if steps is None and distance_in is not None:
        if distance_in <= 2:
            return 0
        if distance_in <= REACH_IN:
            return 1
        steps = distance_in / INCHES_PER_STEP
    if not steps:
        return 1  # within reach
    return by_count(A_STEPS, steps)


def m_index(step: Step, steps: float | None) -> int:
    if steps:
        return by_count(M_STEPS, steps)
    d, dist = step.difficulty, step.distance_in
    if dist is not None:
        if dist > 24:
            return 6
        if dist > 12:
            return max(3, M_INDEX[d])
        return M_INDEX[d]
    return M_INDEX[d]


def tool_index(step: Step) -> tuple[str, int]:
    ta = step.tool_action
    if ta in TOOL_BY_DIFF:
        code, table = TOOL_BY_DIFF[ta]
        idx = table[step.difficulty]
    elif ta in TOOL_TABLES:
        code, table = TOOL_TABLES[ta]
        idx = by_count(table, step.tool_count)
    else:
        return "T", 0
    if code == "F" and any(w in (step.description or "").upper() for w in LOOSEN_WORDS):
        code = "L"
    return code, idx


def duration(step: Step) -> float | None:
    if step.process_seconds:
        return step.process_seconds
    if step.start_s is not None and step.end_s is not None and step.end_s > step.start_s:
        return step.end_s - step.start_s
    return None


def classify(step: Step) -> tuple[str, int]:
    act, d = step.activity, step.difficulty
    steps = steps_for(step)
    if act in (Activity.WALK, Activity.MOVE_OBJECT):
        return "A", a_index(steps, step.distance_in)
    if act == Activity.GET:
        return "AG", a_index(steps, step.distance_in) + G_INDEX[step.heavy]
    if act == Activity.GRASP:
        return "G", G_INDEX[step.heavy]
    if act == Activity.SIT_STAND and d != S:
        return "B", 10  # sit or stand with adjustments
    if act in B_INDEX:
        return "B", B_INDEX[act]
    if act == Activity.PUSH_PULL:
        return "M", m_index(step, steps)
    if act == Activity.PLACE_ASIDE:
        return "P", 1
    if act == Activity.PLACE:
        return "P", P_INDEX[d]
    if act == Activity.POSITION:
        return "P", 6
    if act == Activity.INSERT_ALIGN:
        return "I", I_INDEX[d]
    if act == Activity.INSPECT:
        return "I", 1 if d == S else 3
    if act == Activity.TOOL_USE:
        return tool_index(step)
    if act == Activity.PROCESS:
        # Process time is measured, not estimated: put the observed time on the index scale.
        secs = duration(step) or 0
        return config.PROCESS_CODE, max(1, index_for_tmu(secs / config.SECONDS_PER_INDEX * 10))
    return "A", 0


A_TEXT = {0: "<= 2 in", 1: "within reach"}
B_TEXT = {3: "sit or stand", 6: "bend and arise", 10: "sit or stand with adjustments",
          16: "stand & bend / bend & sit / climb / through door"}
G_TEXT = {1: "light object", 3: "heavy/bulky, blind or obstructed, non-simo"}
P_TEXT = {1: "lay aside / loose fit", 3: "adjustments / light pressure", 6: "position: care, heavy pressure, blind"}
M_TEXT = {1: "<= 12 in, button/switch/knob", 3: "> 12 in, resistance, seat/unseat", 6: "2 stages > 24 in"}
I_TEXT = {1: "1 point", 3: "2 points <= 4 in", 6: "2 points > 4 in"}


def basis(step: Step) -> str:
    """Data-card reason for the index, so the expert can check the coding line by line."""
    if step.manual:
        return f"{step.code}{step.index}: set manually by the expert"
    act, steps = step.activity, steps_for(step)
    a = a_index(steps, step.distance_in)
    a_txt = f"{steps:g} steps" if steps else (A_TEXT.get(a) or f"{step.distance_in:g} in")
    if act in (Activity.WALK, Activity.MOVE_OBJECT):
        return f"A{a}: {a_txt}"
    if act == Activity.GET:
        g = G_INDEX[step.heavy]
        return f"A{a}: {a_txt} + G{g}: {G_TEXT[g]}"
    if act == Activity.GRASP:
        return f"G{step.index}: {G_TEXT[step.index]}"
    if step.code == "B":
        return f"B{step.index}: {B_TEXT.get(step.index, '')}"
    if act == Activity.PUSH_PULL:
        if steps:
            return f"M{step.index}: push/pull with {steps:g} steps"
        return f"M{step.index}: {M_TEXT.get(step.index, '')}" + (f" ({step.distance_in:g} in)" if step.distance_in else "")
    if act in (Activity.PLACE_ASIDE, Activity.PLACE, Activity.POSITION):
        return f"P{step.index}: {P_TEXT[step.index]}"
    if act == Activity.INSERT_ALIGN:
        return f"I{step.index}: {I_TEXT[step.index]}"
    if act == Activity.INSPECT:
        return f"I{step.index}: visual check"
    if act == Activity.TOOL_USE:
        name = step.tool_action.value.replace("_", " ").lower() if step.tool_action else "no tool column"
        cnt = f" x {step.tool_count:g}" if step.tool_count is not None and step.tool_action and step.tool_action.value not in FIXED_TOOLS else ""
        return f"{step.code}{step.index}: {name}{cnt}"
    if act == Activity.PROCESS:
        return f"{step.code}{step.index}: process time measured {duration(step) or 0:.1f} s"
    return ""


def compute_step(step: Step) -> Step:
    if not step.manual:
        step.code, step.index = classify(step)
    div = step.div_freq or 1
    step.cycle_time = round(step.index * config.SECONDS_PER_INDEX * step.freq / div, 2)
    return step


def compute_operation(op: Operation) -> Operation:
    for s in op.steps:
        compute_step(s)
    op.cycle_time = round(sum(s.cycle_time for s in op.steps), 2)
    starts = [s.start_s for s in op.steps if s.start_s is not None]
    ends = [s.end_s for s in op.steps if s.end_s is not None]
    op.video_time = round(max(ends) - min(starts), 1) if starts and ends else 0.0
    return op


def compute_study(study: Study) -> Study:
    for i, op in enumerate(study.operations):
        op.opn_no = (i + 1) * 10
        compute_operation(op)
    study.total_cycle_time_s = round(sum(op.cycle_time for op in study.operations), 2)
    from . import audit
    return audit.run(study)
