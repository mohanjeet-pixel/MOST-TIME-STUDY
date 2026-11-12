# Bulls Eye — MOST Video Time Study

Upload an MP4/MTS shop-floor video → AI breaks it into MOST sub-operations →
engineer reviews against the video → download the "METHOD STEPS - MOST Report" Excel.

## Run (Windows)

```powershell
.\run.ps1          # creates .venv, installs, creates .env
# put GEMINI_API_KEY in .env (https://aistudio.google.com/apikey), then run again
```
Open http://localhost:8000

## How it works

| Stage | File | Cost |
|---|---|---|
| MTS/MP4 → 480p, deinterlaced, no audio proxy (FFmpeg bundled via imageio-ffmpeg) | `bullseye/video.py` | free |
| Gemini watches proxy at 1 fps, low media resolution, returns strict JSON | `bullseye/gemini.py` | ~1 Gemini call / video |
| MOST rules engine: activity → code + index → cycle time | `bullseye/most.py` | free |
| Review UI: click row → jump video, set start/end, override index | `bullseye/static/` | free |
| Excel in report layout with live formulas + "Video Timeline" audit sheet | `bullseye/excel.py` | free |

Cycle time = Index × Sec/Index × Freq ÷ Div.Freq. `SECONDS_PER_INDEX` = **0.36** (BasicMOST data card:
index × 10 = TMU, 1 TMU = 0.036 s) is in `.env` and in cell N3 of the Excel export. The old
CS PRE BENDING-1 sheet used 1.2 — 3.3× the card value, which is why its MOST time ran above the video.

All tables in `bullseye/most.py` are copied from the data cards: General Move (A B G P incl. extended
action distances), Controlled Move (M incl. push/pull extended values, I, X), Tool Use (F/L, C, S, M, R, T),
Equipment Use (W, K) and the TMU interval limits.

## Excel report

| Sheet | Content |
|---|---|
| **Summary** | Logo, study info, VERIFIED/DRAFT stamp; video time, MOST normal time, **standard time** (MOST + PF&D allowance), output per hour / shift, method efficiency, off-line work; time by operation (chart), by category and MOST parameter (chart), top-10 Pareto, data-card based improvement opportunities with estimated saving, sign-off boxes. Yellow cells (allowance %, shift minutes) are editable and recalculate. |
| **Method Steps** | The original "METHOD STEPS - MOST Report" layout with live formulas (Sec/Index in N3). |
| **Video Timeline** | Every element with video start/end, MOST time, inputs and the **data card basis** (e.g. `A16: 8 steps`, `F10: wrist turns x 5`). |
| **Audit** | Expert verification trail, automatic findings, AI tokens and cost. |

`ALLOWANCE_PCT` (default 15) and `SHIFT_MIN` (default 480) are in `.env`. Report logic: `bullseye/report.py`.

## Accuracy check

`.venv\Scripts\python.exe -m tests.test_most`:
- 25 spot checks straight from the data cards — all must match.
- Replays the CS PRE BENDING-1 report (at its 1.2 factor): 24/25 rows match; the one difference is a
  manual M2 judgement in the original (2 is not on the MOST index scale).

## Consistency (same video = same result)

- Gemini runs at temperature 0 with a fixed seed (`AI_SEED`). Google only treats this as "best effort":
  measured on the same 33 s clip, two forced runs still gave 25 vs 18 steps.
- So every AI answer is saved in `data/ai_cache/`, keyed by the video's SHA-256 hash + prompt + model + settings + hint.
  Uploading or re-running the same video returns the **identical** steps at ₹0. Only a changed video, prompt,
  model, setting or hint (or Shift+click "Re-run AI") calls Gemini again.
- Repetition loops are collapsed and counted once; impossible elements (MOST > 3× the video time of that element)
  and a total MOST > 130 % of the video are errors that block approval.

## Expert verification (no unverified AI data in reports)

- `bullseye/audit.py` — free automatic fault finder: timestamps beyond the video (invented steps),
  overlaps/gaps, MOST standard (index × 0.36 s) vs observed time, impossible walking speed,
  text-vs-data mismatch, AI low confidence, expert flags.
- Every step must be marked ✓ by the expert (key **V** = verify & next, **F** = flag fault).
- Approval is blocked until all steps are verified and no errors remain; any later change removes it.
- Excel is stamped **DRAFT – NOT VERIFIED** (red) until approved, then **VERIFIED BY name (date)**;
  the *Audit* sheet lists every finding and expert note.

## Cost

Each AI run records input / output / thinking tokens and the cost in ₹ (prices in `bullseye/config.py`,
rate `USD_INR` in `.env`). Measured: 33 s video ≈ ₹1.1 on gemini-2.5-flash. If Google is overloaded
(429/5xx) or the connection drops ("Server disconnected"), the upload and the call retry,
then fall back to `FALLBACK_MODEL` (flash-lite, ~5× cheaper).

## Tuning
- Index tables: `bullseye/most.py` (verify against your MOST data card).
- What the AI is told: `PROMPT` in `bullseye/gemini.py`.
- Cheaper: `GEMINI_MODEL=gemini-2.5-flash-lite`. More accurate step counts: `gemini-2.5-flash`.

## Roadmap
- Phase 2: local pose model (RTMPose/MediaPipe, CPU) for step counting + activity boundaries.
- Gemini Batch API for -50% cost; Postgres + login for multi-user; correction data → own model.
