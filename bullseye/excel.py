"""Export a study to Excel in the 'METHOD STEPS - MOST Report' layout."""
import io
from pathlib import Path

import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from . import config, most, report
from .models import Study


def _mmss(s):
    if s is None:
        return ""
    return f"{int(s // 60):02d}:{s % 60:04.1f}"


LOGO = Path(__file__).parent / "static" / "logo.png"
RED, DARK, GREY, LINE = "#E11B22", "#121418", "#6B7280", "#D9DDE3"


def _summary(wb, f, study: Study, rep: dict):
    """Front page: KPIs, standard time, output, breakdowns, Pareto, improvement ideas, sign-off."""
    ws = wb.add_worksheet("Summary")
    ws.hide_gridlines(2)
    ws.set_column(0, 0, 2)
    ws.set_column(1, 9, 11.5)
    ws.set_column(10, 10, 2)
    C1, CN = 1, 9  # content columns B..J

    h1 = f(bold=True, font_size=18, font_color=DARK)
    h2 = f(bold=True, font_size=11, font_color="#FFFFFF", bg_color=DARK, indent=1)
    lab = f(font_color=GREY, font_size=8)
    val = f(bold=True, font_size=10)
    th = f(bold=True, font_size=8, font_color=GREY, bottom=1, bottom_color=DARK, text_wrap=True, valign="bottom")
    td = f(bottom=1, bottom_color=LINE, text_wrap=True)
    tdc = f(bottom=1, bottom_color=LINE, align="center")
    tdn = f(bottom=1, bottom_color=LINE, align="right", num_format="0.0")
    tdp = f(bottom=1, bottom_color=LINE, align="right", num_format="0%")
    tot = f(bold=True, top=1, align="right", num_format="0.0")
    totp = f(bold=True, top=1, align="right", num_format="0%")
    totl = f(bold=True, top=1)

    # ---- header ----
    ws.set_row(0, 8)
    ws.set_row(1, 40)
    if LOGO.exists():
        ws.insert_image(1, C1, str(LOGO), {"x_scale": 0.55, "y_scale": 0.55, "x_offset": 2, "y_offset": 8, "object_position": 3})
    ws.merge_range(1, 3, 1, CN, "TIME STUDY REPORT  ·  BasicMOST", f(bold=True, font_size=16, align="right", font_color=DARK))
    ws.merge_range(2, C1, 2, CN, "", f(bottom=2, bottom_color=RED))
    ws.merge_range(3, C1, 3, CN, study.title or "PROCESS", h1)
    ws.set_row(3, 26)

    info = [("Study done by", study.study_by or "-"), ("Date", study.date or "-"),
            ("Source", study.source), ("Video", f"{study.video_file}  ({_mmss(study.video_duration_s)})"),
            ("Method", "BasicMOST data card, 1 index = 10 TMU = 0.36 s (Sec/Index on 'Method Steps' N3)"),
            ("Elements", f"{rep['steps']} sub-operations in {len(rep['by_op'])} operations")]
    r = 4
    for k, v in info:
        ws.write(r, C1, k, lab)
        ws.merge_range(r, C1 + 1, r, CN, v, val)
        r += 1
    if study.approved_by:
        stamp, sf = f"VERIFIED BY {study.approved_by.upper()}  ({study.approved_at})", f(bold=True, align="center", font_color="#FFFFFF", bg_color="#12805C")
    else:
        stamp, sf = "DRAFT - NOT VERIFIED BY EXPERT", f(bold=True, align="center", font_color="#FFFFFF", bg_color=RED)
    ws.merge_range(r, C1, r, CN, stamp, sf)
    ws.set_row(r, 20)
    r += 2

    # ---- KPI tiles (live formulas: change the yellow cells) ----
    most_cell = "'Method Steps'!$G$4*60"
    tile_lab = f(font_color=GREY, font_size=8, align="center", top=1, left=1, right=1, top_color=LINE, left_color=LINE, right_color=LINE)
    tile_sub = f(font_color=GREY, font_size=8, align="center", bottom=1, left=1, right=1, bottom_color=LINE, left_color=LINE, right_color=LINE)
    tile_sub_in = f(font_size=8, align="center", bottom=1, left=1, right=1, bottom_color=LINE, left_color=LINE, right_color=LINE,
                    bg_color="#FFF2CC", num_format='0" min per shift"')

    def tile(row, col, label, value, fmt, sub, color=DARK, sub_fmt=None, is_input=False):
        vf = f(bold=True, font_size=20, align="center", font_color=color, num_format=fmt, left=1, right=1,
               left_color=LINE, right_color=LINE, bg_color="#FFF2CC" if is_input else "#FFFFFF")
        ws.merge_range(row, col, row, col + 2, label, tile_lab)
        if isinstance(value, str) and value.startswith("="):
            ws.merge_range(row + 1, col, row + 1, col + 2, "", vf)
            ws.write_formula(row + 1, col, value, vf)
        else:
            ws.merge_range(row + 1, col, row + 1, col + 2, value, vf)
        if isinstance(sub, str) and sub.startswith("="):
            ws.merge_range(row + 2, col, row + 2, col + 2, "", sub_fmt or tile_sub)
            ws.write_formula(row + 2, col, sub, sub_fmt or tile_sub)
        else:
            ws.merge_range(row + 2, col, row + 2, col + 2, sub, sub_fmt or tile_sub)
        ws.set_row(row + 1, 30)
        return xl_rowcol_to_cell(row + 1, col, row_abs=True, col_abs=True)

    v_cell = tile(r, 1, "VIDEO TIME (observed)", rep["video_s"] / 60, '0.00" min"', f"{rep['video_s']:.1f} s of video", "#0284C7")
    m_cell = tile(r, 4, "MOST NORMAL TIME", f"={most_cell}/60", '0.00" min"', "at 100 % performance (normal pace)", "#E26B0A")
    a_row = r + 4
    a_cell = xl_rowcol_to_cell(a_row + 1, 1, row_abs=True, col_abs=True)
    s_cell = tile(r, 7, "STANDARD TIME", f"={m_cell}*(1+{a_cell}/100)", '0.00" min"', "MOST normal time + allowance", RED)
    tile(a_row, 1, "ALLOWANCE (PF&D) %", rep["allowance_pct"], '0" %"', "personal, fatigue & delay - edit", is_input=True)
    tile(a_row, 4, "OUTPUT PER HOUR", f"=IF({s_cell}>0,60/{s_cell},0)", "0.0", "pieces / hour at standard time")
    shift_cell = xl_rowcol_to_cell(a_row + 2, 7, row_abs=True, col_abs=True)  # editable sub-row of the tile
    tile(a_row, 7, "OUTPUT PER SHIFT", f"=IF({s_cell}>0,{shift_cell}/{s_cell},0)", "0", rep["shift_min"], sub_fmt=tile_sub_in)
    b_row = a_row + 4
    tile(b_row, 1, "METHOD EFFICIENCY", f"=IF({v_cell}>0,{m_cell}/{v_cell},0)", "0%", "MOST time / video time", "#12805C")
    tile(b_row, 4, "OFF-LINE (EXTERNAL) WORK", rep["offline_s"], '0.0" s"', "can run while the machine works")
    pot = sum(k["saving_s"] for k in rep["kaizen"])
    tile(b_row, 7, "IMPROVEMENT POTENTIAL", pot, '0.0" s"', f"{(pot / rep['most_s'] if rep['most_s'] else 0):.0%} of MOST time per cycle", "#7C3AED")
    r = b_row + 4

    # ---- time by operation + chart ----
    ws.merge_range(r, C1, r, CN, "TIME BY OPERATION", h2); r += 1
    for c0, c1, t in [(1, 1, "OPN"), (2, 5, "OPERATION"), (6, 6, "STEPS"), (7, 7, "VIDEO s"), (8, 8, "MOST s"), (9, 9, "% OF MOST")]:
        (ws.merge_range(r, c0, r, c1, t, th) if c1 > c0 else ws.write(r, c0, t, th))
    r += 1
    first = r
    for o in rep["by_op"]:
        ws.write(r, 1, o["opn"], tdc)
        ws.merge_range(r, 2, r, 5, o["name"], td)
        ws.write(r, 6, o["steps"], tdc)
        ws.write(r, 7, o["video_s"], tdn)
        ws.write(r, 8, o["most_s"], tdn)
        ws.write_formula(r, 9, f"=IF(SUM($I${first + 1}:$I${first + len(rep['by_op'])})>0,I{r + 1}/SUM($I${first + 1}:$I${first + len(rep['by_op'])}),0)", tdp)
        r += 1
    last = r - 1
    ws.merge_range(r, 1, r, 5, "TOTAL", totl)
    ws.write_formula(r, 6, f"=SUM(G{first + 1}:G{last + 1})", f(bold=True, top=1, align="center"))
    ws.write(r, 7, rep["video_s"], tot)
    ws.write_formula(r, 8, f"=SUM(I{first + 1}:I{last + 1})", tot)
    ws.write(r, 9, 1 if rep["by_op"] else 0, totp)
    r += 2
    if rep["by_op"]:
        ch = wb.add_chart({"type": "bar"})
        for col, name, color in [(7, "Video (observed)", "#00B0F0"), (8, "MOST normal time", "#E26B0A")]:
            ch.add_series({"name": name, "categories": ["Summary", first, 2, last, 2],
                           "values": ["Summary", first, col, last, col], "fill": {"color": color}, "gap": 60,
                           "data_labels": {"value": True, "num_format": "0", "font": {"size": 7}}})
        ch.set_title({"name": "Video vs MOST time per operation (s)", "name_font": {"size": 10}})
        ch.set_legend({"position": "bottom", "font": {"size": 8}})
        ch.set_y_axis({"reverse": True, "num_font": {"size": 7}})
        ch.set_x_axis({"num_font": {"size": 7}, "major_gridlines": {"visible": True, "line": {"color": LINE}}})
        ch.set_size({"width": 800, "height": max(200, 60 + 38 * len(rep["by_op"]))})
        ws.insert_chart(r, 1, ch)
        r += max(11, int((60 + 38 * len(rep["by_op"])) / 20) + 1)

    # ---- where the time goes: category + MOST parameter (starts page 2) ----
    ws.set_h_pagebreaks([r])
    ws.merge_range(r, C1, r, CN, "WHERE THE TIME GOES", h2); r += 1
    ws.merge_range(r, 1, r, 3, "CATEGORY", th); ws.write(r, 4, "MOST s", th); ws.write(r, 5, "%", th)
    r += 1
    cat_first = r
    total = rep["most_s"] or 1
    for name, v in rep["by_cat"].items():
        ws.merge_range(r, 1, r, 3, name, td); ws.write(r, 4, v, tdn); ws.write(r, 5, v / total, tdp); r += 1
    r += 1
    ws.merge_range(r, 1, r, 3, "MOST PARAMETER", th); ws.write(r, 4, "MOST s", th); ws.write(r, 5, "%", th)
    r += 1
    from .report import CAT_COLORS
    names = {"A": "Action distance", "AG": "Reach + grasp", "G": "Gain control", "B": "Body motion", "P": "Placement",
             "M": "Controlled move / process", "I": "Alignment / inspect", "X": "Process time", "F": "Fasten",
             "L": "Loosen", "C": "Cut", "S": "Surface treat", "R": "Record", "T": "Think / read / inspect",
             "W": "Keyboard", "K": "Keypad"}
    for code, v in rep["by_code"].items():
        ws.write(r, 1, code, f(bold=True, bottom=1, bottom_color=LINE, align="center"))
        ws.merge_range(r, 2, r, 3, names.get(code, ""), td); ws.write(r, 4, v, tdn); ws.write(r, 5, v / total, tdp); r += 1
    pie = wb.add_chart({"type": "doughnut"})
    pie.add_series({"name": "Category", "categories": ["Summary", cat_first, 1, cat_first + 3, 1],
                    "values": ["Summary", cat_first, 4, cat_first + 3, 4],
                    "points": [{"fill": {"color": c}} for c in CAT_COLORS],
                    "data_labels": {"percentage": True, "font": {"size": 8, "bold": True, "color": "#FFFFFF"}}})
    pie.set_title({"name": "MOST time by category", "name_font": {"size": 10}})
    pie.set_legend({"position": "bottom", "font": {"size": 8}})
    pie.set_hole_size(55)
    pie.set_size({"width": 330, "height": 250})
    ws.insert_chart(cat_first - 1, 6, pie, {"x_offset": 10})
    r = max(r, cat_first + 12) + 1

    # ---- Pareto ----
    ws.merge_range(r, C1, r, CN, "TOP 10 ELEMENTS (PARETO)", h2); r += 1
    ws.write(r, 1, "RANK", th); ws.write(r, 2, "OPN.#", th); ws.merge_range(r, 3, r, 7, "SUB-OPERATION", th)
    ws.write(r, 8, "CODE", th); ws.write(r, 9, "MOST s", th)
    r += 1
    for i, p in enumerate(rep["pareto"], 1):
        ws.write(r, 1, i, tdc); ws.write(r, 2, f"{p['opn']}.{p['n']}", tdc)
        ws.merge_range(r, 3, r, 7, p["desc"], td); ws.write(r, 8, p["code"], tdc); ws.write(r, 9, p["most_s"], tdn)
        r += 1
    r += 1

    # ---- improvement opportunities ----
    ws.merge_range(r, C1, r, CN, "IMPROVEMENT OPPORTUNITIES (from the data card, estimated MOST saving per cycle)", h2); r += 1
    ws.write(r, 1, "#", th); ws.merge_range(r, 2, r, 3, "OPPORTUNITY", th); ws.merge_range(r, 4, r, 7, "RECOMMENDED ACTION", th)
    ws.write(r, 8, "STEPS (OPN.#)", th); ws.write(r, 9, "SAVING s", th)
    r += 1
    if not rep["kaizen"]:
        ws.merge_range(r, 1, r, CN, "No data-card based improvement found.", td); r += 1
    for i, k in enumerate(rep["kaizen"], 1):
        ws.write(r, 1, i, tdc)
        ws.merge_range(r, 2, r, 3, f"{k['title']} ({k['count']})", f(bold=True, bottom=1, bottom_color=LINE, text_wrap=True))
        ws.merge_range(r, 4, r, 7, k["action"], td)
        ws.write(r, 8, k["where"], f(bottom=1, bottom_color=LINE, text_wrap=True, font_size=7))
        ws.write(r, 9, k["saving_s"], tdn)
        ws.set_row(r, 36)
        r += 1
    if rep["idle_s"] > 1:
        ws.merge_range(r, 1, r, CN, f"Note: {rep['idle_s']:.0f} s of the video is not covered by any element (waiting, searching, "
                       "talking or missed work) - check it in the video.", f(italic=True, font_color=GREY, text_wrap=True))
        ws.set_row(r, 24)
        r += 1
    r += 2

    # ---- sign-off ----
    for c0, label, name in [(1, "PREPARED BY", study.study_by), (4, "VERIFIED BY (IE expert)", study.approved_by), (7, "APPROVED BY", "")]:
        ws.merge_range(r, c0, r, c0 + 2, name or "", f(bottom=1, align="center", bold=True))
        ws.merge_range(r + 1, c0, r + 1, c0 + 2, label, f(font_color=GREY, font_size=8, align="center"))
    ws.set_row(r, 30)
    r += 3
    ws.merge_range(r, C1, r, CN, "MOST normal time = time for a trained operator at 100 % performance (BasicMOST). "
                   "Standard time adds the PF&D allowance. Generated by Bulls Eye; every element is traceable to the video "
                   "('Video Timeline') and to the data card ('DATA CARD BASIS').", f(italic=True, font_size=7, font_color=GREY, text_wrap=True))
    ws.set_row(r, 30)

    ws.set_portrait()
    ws.set_paper(9)
    ws.set_margins(0.4, 0.4, 0.5, 0.5)
    ws.fit_to_pages(1, 0)
    ws.print_area(0, 0, r, 10)
    ws.set_footer(f"&L&8Bulls Eye · {(study.title or '').replace('&', '&&')}&R&8Page &P of &N")
    ws.activate()


def export(study: Study) -> bytes:
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})

    base = {"font_name": "Arial", "font_size": 9, "valign": "vcenter"}
    f = lambda **k: wb.add_format({**base, **k})
    _summary(wb, f, study, report.analyse(study))
    ws = wb.add_worksheet("Method Steps")
    title = f(bold=True, font_name="Times New Roman", font_size=14, underline=1, align="center", border=1)
    meta = f(bold=True, align="center")
    hdr = f(bold=True, align="center", text_wrap=True, border=1, bg_color="#C4D79B", font_size=8)
    hdr_red = f(bold=True, align="center", text_wrap=True, border=1, bg_color="#C4D79B", font_color="#FF0000", font_size=8)
    blue_tot = f(bold=True, align="center", bg_color="#00B0F0", num_format="0.00")
    orange_tot = f(bold=True, align="center", bg_color="#E26B0A", num_format="0.00")
    op_txt = f(bold=False, bg_color="#FDE9D9", border=1)
    op_c = f(align="center", bg_color="#FDE9D9", border=1)
    op_blue = f(align="center", bg_color="#00B0F0", border=1, num_format="0.0")
    op_yel = f(align="center", bg_color="#FFFF00", border=1, num_format="0.0")
    txt = f(bottom=4, left=1, right=1)
    c = f(align="center", bottom=4, left=1, right=1)
    c1 = f(align="center", bottom=4, left=1, right=1, num_format="0.0#")
    small = f(italic=True, font_color="#808080")

    widths = [12, 6, 52, 9, 6, 7, 9, 6, 6, 6, 6, 7]
    for i, w in enumerate(widths):
        ws.set_column(i, i, w)
    ws.set_column(13, 13, 14)

    ws.merge_range(0, 0, 0, 11, '" METHOD STEPS " - MOST  Report', title)
    ws.merge_range(1, 0, 1, 2, study.title or "PROCESS", meta)
    ws.merge_range(1, 3, 1, 7, f"STUDY DONE BY : {study.study_by}", meta)
    ws.merge_range(1, 8, 1, 11, f"DATE : {study.date}", meta)
    ws.merge_range(2, 0, 2, 5, f"SOURCE: {study.source}", meta)
    if study.approved_by:
        ws.merge_range(2, 6, 2, 11, f"VERIFIED BY : {study.approved_by}  ({study.approved_at})",
                       f(bold=True, align="center", font_color="#12805C"))
    else:
        ws.merge_range(2, 6, 2, 11, "DRAFT - NOT VERIFIED BY EXPERT",
                       f(bold=True, align="center", font_color="#FFFFFF", bg_color="#E11B22"))

    # Sec/Index factor cell (editable, drives every formula)
    ws.write(1, 13, "Sec / Index", small)
    ws.write(2, 13, config.SECONDS_PER_INDEX, f(bold=True, bg_color="#FFF2CC", border=1))
    spi = "$N$3"

    heads = ["PRO. OPN No.", "# No.", "OPERATION / SUB OPERATIONS", "VIDEO TIME", "", "INDEX",
             "CYCLE TIME", "OPRT", "FREQ.", "DIV. FREQ", "MIX / MEN", "OFF LINE"]
    for i, h in enumerate(heads):
        ws.write(4, i, h, hdr_red if h in ("VIDEO TIME", "CYCLE TIME") else hdr)
    ws.set_row(4, 24)

    row = 5
    op_cells = []
    for op in study.operations:
        for col in range(12):
            ws.write_blank(row, col, None, op_c)
        ws.write(row, 1, op.opn_no, op_c)
        ws.write(row, 2, op.name, op_txt)
        ws.write(row, 3, op.video_time, op_blue)
        op_row = row
        row += 1
        first = row
        for n, s in enumerate(op.steps, 1):
            ws.write(row, 0, "", c)
            ws.write(row, 1, n, c)
            ws.write(row, 2, s.description, txt)
            ws.write(row, 3, "", c)
            ws.write(row, 4, s.code, c)
            ws.write(row, 5, s.index, c)
            idx, fr, dv = (xl_rowcol_to_cell(row, k) for k in (5, 8, 9))
            ws.write_formula(row, 6, f"={idx}*{spi}*{fr}/{dv}", c1, s.cycle_time)
            ws.write(row, 7, s.oprt, c)
            ws.write(row, 8, s.freq, c)
            ws.write(row, 9, s.div_freq, c)
            ws.write(row, 10, s.men, c)
            ws.write(row, 11, "YES" if s.offline else "No", c)
            row += 1
        rng = f"{xl_rowcol_to_cell(first, 6)}:{xl_rowcol_to_cell(max(first, row - 1), 6)}"
        ws.write_formula(op_row, 6, f"=SUM({rng})", op_yel, op.cycle_time)
        op_cells.append(xl_rowcol_to_cell(op_row, 6))

    # Totals in minutes above the header (blue = video, orange = MOST cycle time)
    ws.write(3, 3, round(study.video_duration_s / 60, 2), blue_tot)
    total = "+".join(op_cells) if op_cells else "0"
    ws.write_formula(3, 6, f"=({total})/60", orange_tot, round(study.total_cycle_time_s / 60, 2))
    ws.write(3, 2, "Totals in minutes  →", f(align="right", italic=True, font_color="#808080"))

    ws.freeze_panes(5, 0)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    ws.repeat_rows(4)
    ws.set_footer(f"&L&8Bulls Eye · {(study.title or '').replace('&', '&&')}&R&8Page &P of &N")

    # Audit sheet: where each step is in the video
    tl = wb.add_worksheet("Video Timeline")
    th = ["OPN", "#", "SUB OPERATION", "ACTIVITY", "START", "END", "VIDEO (s)", "MOST (s)",
          "STEPS MIN", "STEPS MAX", "DIST (in)", "HEAVY", "DIFFICULTY", "TOOL", "COUNT",
          "DATA CARD BASIS", "AI CONF.", "EXPERT", "MANUAL EDIT"]
    for i, h in enumerate(th):
        tl.write(0, i, h, hdr)
    tl.set_row(0, 24)
    tl.set_column(2, 2, 48)
    tl.set_column(3, 3, 14)
    tl.set_column(13, 13, 20)
    tl.set_column(15, 15, 44)
    r = 1
    for op in study.operations:
        for n, s in enumerate(op.steps, 1):
            dur = (s.end_s - s.start_s) if s.start_s is not None and s.end_s is not None else None
            vals = [op.opn_no, n, s.description, s.activity.value, _mmss(s.start_s), _mmss(s.end_s),
                    round(dur, 1) if dur is not None else "", s.cycle_time, s.walk_steps_min, s.walk_steps_max,
                    s.distance_in, "Y" if s.heavy else "", s.difficulty.value,
                    s.tool_action.value if s.tool_action else "", s.tool_count, most.basis(s), s.confidence,
                    {"ok": "VERIFIED", "flag": "FLAGGED"}.get(s.review, ""), "Y" if s.manual else ""]
            for i, v in enumerate(vals):
                tl.write(r, i, "" if v is None else v, txt if i in (2, 15) else c)
            r += 1
    tl.freeze_panes(1, 3)
    tl.autofilter(0, 0, max(1, r - 1), len(th) - 1)

    # Audit sheet: expert verification trail + automatic findings + AI cost
    au = wb.add_worksheet("Audit")
    au.set_column(0, 1, 7)
    au.set_column(2, 2, 50)
    au.set_column(3, 4, 12)
    au.set_column(5, 5, 70)
    au.set_column(6, 6, 40)
    au.write(0, 0, "VERIFICATION", f(bold=True, font_size=11))
    au.write(1, 0, "Status:")
    au.write(1, 2, f"APPROVED by {study.approved_by} on {study.approved_at}" if study.approved_by else "DRAFT - not approved",
             f(bold=True, font_color="#12805C" if study.approved_by else "#E11B22"))
    au.write(2, 0, "AI:")
    au.write(2, 2, f"{study.model} · {study.ai_runs} run(s) · {study.tokens_in:,} in / {study.tokens_out:,} out / "
                   f"{study.tokens_think:,} thinking tokens (last run) · total cost Rs {study.cost_inr:.2f}")
    ah = ["OPN", "#", "SUB OPERATION", "EXPERT", "LEVEL", "FINDING", "EXPERT NOTE"]
    for i, h in enumerate(ah):
        au.write(4, i, h, hdr)
    lvl_fmt = {"error": f(font_color="#C0262D", bold=True), "warn": f(font_color="#9A6700", bold=True), "info": f(font_color="#6B7280")}
    r = 5
    for i in study.issues:
        au.write(r, 2, "(whole study)"); au.write(r, 4, i["level"].upper(), lvl_fmt[i["level"]]); au.write(r, 5, i["msg"]); r += 1
    for op in study.operations:
        for n, s in enumerate(op.steps, 1):
            rev = {"ok": "VERIFIED", "flag": "FLAGGED"}.get(s.review, "NOT CHECKED")
            rows = s.issues or [{"level": "", "msg": ""}]
            for i in rows:
                au.write(r, 0, op.opn_no); au.write(r, 1, n); au.write(r, 2, s.description)
                au.write(r, 3, rev, f(bold=True, font_color={"VERIFIED": "#12805C", "FLAGGED": "#C0262D"}.get(rev, "#6B7280")))
                if i["level"]:
                    au.write(r, 4, i["level"].upper(), lvl_fmt[i["level"]])
                au.write(r, 5, i["msg"]); au.write(r, 6, s.note)
                r += 1
    au.freeze_panes(5, 0)

    wb.close()
    return buf.getvalue()
