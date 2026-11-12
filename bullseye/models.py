from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Activity(str, Enum):
    """What Gemini sees. The MOST engine turns these into code + index."""
    WALK = "WALK"                  # body motion: walk N steps                     -> A
    GET = "GET"                    # reach/walk to an object AND grasp it            -> AG
    GRASP = "GRASP"                # grasp only (object already at hand)             -> G
    MOVE_OBJECT = "MOVE_OBJECT"    # free move of a held object, short distance      -> A
    PUSH_PULL = "PUSH_PULL"        # controlled move: button, lever, switch, crank   -> M
    PLACE_ASIDE = "PLACE_ASIDE"    # put down / toss aside, no accuracy              -> P1
    PLACE = "PLACE"                # place with some care / adjustment               -> P
    POSITION = "POSITION"          # position accurately / heavy / blind             -> P
    INSERT_ALIGN = "INSERT_ALIGN"  # insert, align to points                         -> I
    INSPECT = "INSPECT"            # visual check                                    -> I
    PROCESS = "PROCESS"            # continuous work timed from video (brushing, welding, machine) -> X/M
    SIT_STAND = "SIT_STAND"        # body motion: sit or stand (difficulty adjust = with adjustments) -> B3 / B10
    BEND_ARISE = "BEND_ARISE"      # body motion: bend and arise                     -> B6
    BODY_LARGE = "BODY_LARGE"      # stand and bend / bend and sit / climb / through door -> B16
    TOOL_USE = "TOOL_USE"          # fasten/loosen, cut, clean, measure, write, read, keyboard -> F L C S M R T W K


class ToolAction(str, Enum):
    """BasicMOST Tool Use / Equipment Use data card columns. tool_count is what the column counts."""
    FINGER_SPINS = "FINGER_SPINS"              # F/L fingers, screwdriver: spins
    WRIST_TURNS = "WRIST_TURNS"                # F/L hand, screwdriver, ratchet, T-wrench: turns
    WRENCH_WRIST_STROKES = "WRENCH_WRIST_STROKES"  # F/L wrench: wrist strokes
    WRIST_CRANKS = "WRIST_CRANKS"              # F/L wrench, ratchet: wrist cranks
    HAMMER_TAPS = "HAMMER_TAPS"                # F/L hand, hammer: taps
    RATCHET_ARM_TURNS = "RATCHET_ARM_TURNS"    # F/L ratchet: arm turns
    T_WRENCH_TURNS = "T_WRENCH_TURNS"          # F/L T-wrench 2 hands: turns
    WRENCH_ARM_STROKES = "WRENCH_ARM_STROKES"  # F/L wrench: arm strokes
    ARM_CRANKS = "ARM_CRANKS"                  # F/L wrench, ratchet: arm cranks
    HAMMER_STRIKES = "HAMMER_STRIKES"          # F/L hammer: strikes
    POWER_WRENCH = "POWER_WRENCH"              # F/L power wrench, per fastener (count = fasteners)
    WIRE_CUT = "WIRE_CUT"                      # C pliers cut-off wire (difficulty soft/medium/hard)
    PLIERS_SECURE = "PLIERS_SECURE"            # C pliers grip / twist / cotter pin (difficulty)
    SCISSORS_CUTS = "SCISSORS_CUTS"            # C scissors: cuts
    KNIFE_SLICES = "KNIFE_SLICES"              # C knife: slices
    AIR_CLEAN = "AIR_CLEAN"                    # S air nozzle: sq ft
    BRUSH_CLEAN = "BRUSH_CLEAN"                # S brush: sq ft
    WIPE_CLOTH = "WIPE_CLOTH"                  # S cloth: sq ft
    MEASURE_PROFILE_GAUGE = "MEASURE_PROFILE_GAUGE"  # M
    MEASURE_FIXED_SCALE = "MEASURE_FIXED_SCALE"      # M
    MEASURE_TAPE = "MEASURE_TAPE"                    # M steel tape <= 6 ft
    FEELER_GAUGE = "FEELER_GAUGE"                    # M 24
    DEPTH_MICROMETER = "DEPTH_MICROMETER"            # M 32
    OD_MICROMETER = "OD_MICROMETER"                  # M 42 (<= 4 in)
    ID_MICROMETER = "ID_MICROMETER"                  # M 54 (<= 4 in)
    CRANK_REVS = "CRANK_REVS"                        # M controlled move: crank revolutions
    WRITE_DIGITS = "WRITE_DIGITS"              # R pencil/pen: digits
    WRITE_WORDS = "WRITE_WORDS"                # R pencil/pen: words
    MARK_DIGITS = "MARK_DIGITS"                # R marker: digits (1 = check mark / scribe line)
    INSPECT_POINTS = "INSPECT_POINTS"          # T eyes/fingers: points inspected
    READ_DIGITS = "READ_DIGITS"                # T eyes: digits / single words
    READ_WORDS = "READ_WORDS"                  # T eyes: words of text
    COMPARE = "COMPARE"                        # T eyes: compare (count)
    READ_GAUGE = "READ_GAUGE"                  # T 3
    READ_SCALE = "READ_SCALE"                  # T 6 scale value, date or time
    READ_VERNIER = "READ_VERNIER"              # T 10
    READ_TABLE = "READ_TABLE"                  # T 16 table value
    FEEL_HEAT = "FEEL_HEAT"                    # T 6
    FEEL_DEFECT = "FEEL_DEFECT"                # T 10
    KEYBOARD_WORDS = "KEYBOARD_WORDS"          # W keyboard: words (0 = mouse click)
    KEYPAD_DIGITS = "KEYPAD_DIGITS"            # K keypad: digits


class Difficulty(str, Enum):
    SIMPLE = "simple"    # light object, loose fit, single point, button press
    ADJUST = "adjust"    # needs adjustment / light pressure / resistance / two points
    PRECISE = "precise"  # care, precision, heavy pressure, blind or obstructed, heavy object


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Step(BaseModel):
    description: str
    activity: Activity = Activity.WALK
    start_s: Optional[float] = None
    end_s: Optional[float] = None
    walk_steps_min: Optional[int] = None
    walk_steps_max: Optional[int] = None
    distance_in: Optional[float] = None
    heavy: bool = False
    difficulty: Difficulty = Difficulty.SIMPLE
    process_seconds: Optional[float] = None
    tool_action: Optional[ToolAction] = None
    tool_count: Optional[float] = None

    # computed by the MOST engine unless manual=True
    code: str = ""
    index: int = 0
    manual: bool = False

    oprt: str = "3"
    freq: float = 1
    div_freq: float = 1
    men: int = 1
    offline: bool = False
    cycle_time: float = 0.0

    # verification
    confidence: str = "high"          # AI self-reported: high | medium | low  ("manual" for expert-added)
    review: str = ""                  # "" = not reviewed | "ok" = verified by expert | "flag" = expert found a fault
    note: str = ""                    # expert comment
    issues: list[dict] = Field(default_factory=list)   # computed by audit.py: {level, msg}
    ai_repeat: int = 0                    # >1: the AI output this step/block N times in a row (collapsed, Freq = N)
    ai_repeat_end: Optional[float] = None  # video time where the repeated block ended


class Operation(BaseModel):
    opn_no: int
    name: str
    steps: list[Step] = Field(default_factory=list)
    cycle_time: float = 0.0
    video_time: float = 0.0


class Study(BaseModel):
    id: str
    title: str = ""
    study_by: str = ""
    date: str = ""
    source: str = "ACTUAL VIDEO PROCESS"
    video_file: str = ""
    proxy_file: str = ""
    video_duration_s: float = 0.0
    status: str = "uploaded"   # uploaded | processing | ready | error
    error: str = ""
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    tokens_think: int = 0
    ai_runs: int = 0
    cost_usd: float = 0.0        # cumulative across all AI runs of this study
    cost_inr: float = 0.0
    last_run_inr: float = 0.0
    ai_cached: bool = False      # last analysis reused the saved AI result for this exact video (Rs 0)
    operations: list[Operation] = Field(default_factory=list)
    total_cycle_time_s: float = 0.0
    issues: list[dict] = Field(default_factory=list)  # study-level audit findings
    approved_by: str = ""
    approved_at: str = ""


# ---- Schema Gemini must answer in (kept small = fewer output tokens) ----

class AIStep(BaseModel):
    description: str = Field(description="Short UPPER CASE MOST-style sub-operation text, e.g. 'WALK 5-8 STEPS', 'WITH IN REACH GRASP THE PENDENT'")
    activity: Activity
    start: str = Field(description="Start timestamp MM:SS.s")
    end: str = Field(description="End timestamp MM:SS.s")
    walk_steps_min: Optional[int] = Field(description="Walking steps (lower estimate) if the body moves, else null")
    walk_steps_max: Optional[int] = Field(description="Walking steps (upper estimate) if the body moves, else null")
    distance_in: Optional[float] = Field(description="Hand/object move distance in inches if no walking, else null")
    heavy: bool = Field(description="True if object is heavy/bulky or needs two hands")
    difficulty: Difficulty
    tool_action: Optional[ToolAction] = Field(description="Only for activity TOOL_USE: which data-card column, else null")
    repeat_count: int = Field(description="How many times this exact motion repeats back-to-back (start/end span all of them); 1 if it happens once")
    tool_count: Optional[float] = Field(description="Only for TOOL_USE: counted spins/turns/strokes/cranks/taps/strikes, fasteners (power wrench), cuts, slices, sq ft, digits, words or points, else null")
    offline: bool = Field(description="True if the task could be done while the machine runs (external/offline work)")
    confidence: Confidence = Field(description="high = clearly visible start to end; medium = partly visible or count estimated; low = mostly hidden/out of frame, you are inferring")


class AIOperation(BaseModel):
    name: str = Field(description="Main operation name in UPPER CASE, e.g. 'LIFTING - MOVING - PLACING'")
    steps: list[AIStep]


class AIResult(BaseModel):
    process_name: str = Field(description="Short name of the overall process, e.g. 'CS PRE BENDING-1'")
    operations: list[AIOperation]
