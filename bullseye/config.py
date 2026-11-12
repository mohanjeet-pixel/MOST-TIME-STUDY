import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data" / "studies"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# BasicMOST data card: index x 10 = TMU, 1 TMU = 0.036 s  ->  1 index = 0.36 s.
# A bigger value (e.g. the 1.2 in the old CS PRE BENDING-1 sheet) inflates every element 3.3x
# and makes MOST time exceed the real video time.
SECONDS_PER_INDEX = float(os.getenv("SECONDS_PER_INDEX", "0.36"))
# Standard time = MOST normal time x (1 + PF&D allowance). Editable in the Excel report too.
ALLOWANCE_PCT = float(os.getenv("ALLOWANCE_PCT", "15"))
SHIFT_MIN = float(os.getenv("SHIFT_MIN", "480"))  # available minutes per shift, for output per shift
STEP_RANGE_POLICY =os.getenv("STEP_RANGE_POLICY", "min")
PROCESS_CODE = os.getenv("PROCESS_CODE", "M")
DEFAULT_OPRT = os.getenv("DEFAULT_OPRT", "3")

# ---- Cost control ----
# USD per 1M tokens (input, output). Thinking tokens are billed as output.
# Source: ai.google.dev/gemini-api/docs/pricing (paid tier). Update if Google changes prices.
PRICES = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
}
PRICE_IN = float(os.getenv("PRICE_IN_USD_PER_M", PRICES.get(GEMINI_MODEL, (0.30, 2.50))[0]))
PRICE_OUT = float(os.getenv("PRICE_OUT_USD_PER_M", PRICES.get(GEMINI_MODEL, (0.30, 2.50))[1]))
USD_INR = float(os.getenv("USD_INR", "88"))
# Used automatically if the main model is overloaded (503). Empty = no fallback.
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-2.5-flash-lite")
# Consistency: temperature is fixed at 0 in gemini.py; fixed seed; saved results reused for the same video
AI_SEED = int(os.getenv("AI_SEED", "42"))
CACHE_DIR = DATA_DIR.parent / "ai_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
# Hidden reasoning tokens cost the same as output. 0 = off (cheapest), -1 = model decides.
THINKING_BUDGET = int(os.getenv("THINKING_BUDGET", "1024"))
# Frames per second the AI looks at: more = sharper timestamps, more input tokens.
MAX_FPS = float(os.getenv("MAX_FPS", "3"))
FRAME_BUDGET = int(os.getenv("FRAME_BUDGET", "600"))
# MOST standard: 1 index = 10 TMU = 0.36 s. Used by the audit to compare against observed video time.
STD_SECONDS_PER_INDEX = 0.36


def cost_usd(tokens_in: int, tokens_out: int, tokens_think: int, model: str = "") -> float:
    p_in, p_out = PRICES.get(model, (PRICE_IN, PRICE_OUT)) if model and model != GEMINI_MODEL else (PRICE_IN, PRICE_OUT)
    return (tokens_in * p_in + (tokens_out + tokens_think) * p_out) / 1_000_000
