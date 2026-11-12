"""Checks the MOST engine against the CS PRE BENDING-1 reference report (Gurumurthy, 12/05/2021).

Run:  .venv\\Scripts\\python.exe -m tests.test_most
"""
from bullseye import excel, most
from bullseye.models import Operation, Step, Study

W, GET, G, MO, PP, PA, PL, PO, IA, IN, PR = ("WALK", "GET", "GRASP", "MOVE_OBJECT", "PUSH_PULL", "PLACE_ASIDE",
                                              "PLACE", "POSITION", "INSERT_ALIGN", "INSPECT", "PROCESS")

# (description, activity, kwargs, expected code, expected index)
REF = {
    "MAGNETIC TACKLE ENGAGEMENT WITH SHEET": [
        ("WALK 5-8 STEPS", W, dict(walk_steps_min=5, walk_steps_max=8), "A", 10),
        ("WITH IN REACH GRASP THE PENDENT", GET, {}, "AG", 2),
        ("WALK 2-3 STEPS", W, dict(walk_steps_min=2, walk_steps_max=3), "A", 3),
        ("WITH IN REACH GET THE MAGNETIC TACKLE", GET, dict(heavy=True), "AG", 4),
        ("PUSH /PULL 3 INCHES LEVER TO OPEN THE TACKLE", PP, dict(distance_in=3), "M", 1),
        ("MOVE TACKLE 3 INCHES WITH ORIENTATION", MO, dict(distance_in=3), "A", 1),
        ("INSERT 2 INCHES INTO SHEET", IA, {}, "I", 1),
        ("PUSH /PULL 3 INCHES LEVER TO LOCK THE TACKLE", PP, dict(distance_in=3), "M", 1),
        ("INSPECT THE LOCK CONDITION", IN, {}, "I", 1),
    ],
    "LIFTING - MOVING - PLACING": [
        ('PUSH THE PENDENT BUTTON TO LIFT <=1"', PP, dict(distance_in=1), "M", 1),
        ("GRASP THE SHEET IN ONE HAND FOR GUIDE", G, {}, "G", 1),
        ("WALK 33 STEPS", W, dict(walk_steps_min=33, walk_steps_max=33), "A", 54),
        ("POSITION THE PLATE INTO STAND", PO, dict(difficulty="precise"), "P", 6),
        ("PLACE THE PLATE INTO STAND", PL, dict(difficulty="adjust"), "P", 3),
        ('PUSH /PULL TO RELEASE THE TACKLE IN PNEDENT<1"', PP, dict(distance_in=1), "M", 1),
        ('PUSH /PULL TO RELEASE THE TACKLE BY LEVER <12"', PP, dict(distance_in=12, difficulty="adjust"), "M", 2),
        ("GRASP THE TACKLE IN HAND", G, {}, "G", 1),
        ("MOVE THE 2-3 STEPS", W, dict(walk_steps_min=2, walk_steps_max=3), "A", 3),
        ("PUSH THE PENDENT BUTTON TO MOVE 2-3 STEPS", PP, {}, "M", 1),
        ("PLACES ASIDE THE PENDENT AND TACKLE", PL, dict(difficulty="adjust"), "P", 3),
    ],
    "SURFACE TREATMENT": [
        ("WALK 5-6 STEP", W, dict(walk_steps_min=5, walk_steps_max=6, offline=True), "A", 10),
        ("GRASP THE METAL SCRUBER/ METAL BRUSH", G, dict(offline=True), "G", 1),
        ("SURFACE TREAT 15 SQ.FT", PR, dict(start_s=0, end_s=65, offline=True), "M", 54),
        ("PLACE ASIDE METAL BRUSH", PA, dict(offline=True), "P", 1),
        ("TURN AND WALK 2-3 STEP BACK TO HOME POSITION", W, dict(walk_steps_min=2, walk_steps_max=3, offline=True), "A", 3),
    ],
}
EXPECTED_OP_CT = [28.8, 91.2, 82.8]


def card(step_kw, code, index):
    s = most.compute_step(Step(description=step_kw.pop("description", "X"), **step_kw))
    ok = s.code == code and s.index == index
    print(f"{'OK ' if ok else 'XX '} card {code:>2} {index:>3}  got {s.code:>2} {s.index:>3}  {step_kw}")
    return not ok


def data_cards() -> int:
    """Spot checks taken straight from the BasicMOST data cards."""
    bad = 0
    bad += card(dict(activity=W, walk_steps_min=1, walk_steps_max=2), "A", 3)
    bad += card(dict(activity=W, walk_steps_min=8, walk_steps_max=10), "A", 16)
    bad += card(dict(activity=W, walk_steps_min=45, walk_steps_max=45), "A", 81)      # 41-49
    bad += card(dict(activity=W, walk_steps_min=60, walk_steps_max=60), "A", 113)     # 58-67
    bad += card(dict(activity=W, walk_steps_min=150, walk_steps_max=150), "A", 270)   # 143-158
    bad += card(dict(activity="BEND_ARISE"), "B", 6)
    bad += card(dict(activity="SIT_STAND"), "B", 3)
    bad += card(dict(activity=PO), "P", 6)
    bad += card(dict(activity=PP, distance_in=20), "M", 3)            # > 12 in
    bad += card(dict(activity=PP, distance_in=30), "M", 6)            # 2 stages > 24 in
    bad += card(dict(activity=PP, walk_steps_min=4, walk_steps_max=4), "M", 10)   # 3-5 steps
    bad += card(dict(activity=PP, walk_steps_min=15, walk_steps_max=15), "M", 32)  # ext 14-17
    bad += card(dict(activity="TOOL_USE", tool_action="WRIST_TURNS", tool_count=5), "F", 10)
    bad += card(dict(activity="TOOL_USE", tool_action="WRENCH_ARM_STROKES", tool_count=4, description="LOOSEN NUT"), "L", 24)
    bad += card(dict(activity="TOOL_USE", tool_action="POWER_WRENCH", difficulty="simple"), "F", 3)
    bad += card(dict(activity="TOOL_USE", tool_action="HAMMER_STRIKES", tool_count=8), "F", 16)
    bad += card(dict(activity="TOOL_USE", tool_action="WIPE_CLOTH", tool_count=1), "S", 10)
    bad += card(dict(activity="TOOL_USE", tool_action="MEASURE_TAPE"), "M", 32)
    bad += card(dict(activity="TOOL_USE", tool_action="WRITE_DIGITS", tool_count=4), "R", 6)
    bad += card(dict(activity="TOOL_USE", tool_action="INSPECT_POINTS", tool_count=9), "T", 10)
    bad += card(dict(activity="TOOL_USE", tool_action="READ_WORDS", tool_count=24), "T", 10)
    bad += card(dict(activity="TOOL_USE", tool_action="KEYPAD_DIGITS", tool_count=11), "K", 6)
    bad += card(dict(activity="TOOL_USE", tool_action="KEYBOARD_WORDS", tool_count=0), "W", 1)
    # Process time card: X 10 = 4.5 s, X 16 = 7.0 s (at 0.36 s/index)
    bad += card(dict(activity=PR, start_s=0, end_s=4.5), "M", 10)
    bad += card(dict(activity=PR, start_s=0, end_s=7.0), "M", 16)
    return bad


def main():
    from bullseye import config
    print("--- BasicMOST data cards (0.36 s / index) ---")
    config.SECONDS_PER_INDEX = 0.36
    bad = data_cards()
    print(f"data-card mismatches: {bad}\n")

    # The CS PRE BENDING-1 sheet was made with 1.2 s/index, so replay it with that factor
    config.SECONDS_PER_INDEX = 1.2
    print("--- CS PRE BENDING-1 replay (sheet used 1.2 s / index) ---")
    study = Study(id="ref", title="CS PRE BENDING-1", study_by="GURUMURTHY", date="12/05/2021",
                  video_duration_s=5.54 * 60)
    for name, rows in REF.items():
        study.operations.append(Operation(opn_no=0, name=name, steps=[
            Step(description=d, activity=a, **kw) for d, a, kw, _, _ in rows]))
    most.compute_study(study)

    mism = 0
    for op, (name, rows) in zip(study.operations, REF.items()):
        for s, (_, _, _, ec, ei) in zip(op.steps, rows):
            ok = s.code == ec and s.index == ei
            mism += not ok
            print(f"{'OK ' if ok else 'XX '} {s.description:<48} got {s.code:>2} {s.index:>3}  expected {ec:>2} {ei:>3}")
    for op, exp in zip(study.operations, EXPECTED_OP_CT):
        print(f"OPN {op.opn_no}: cycle {op.cycle_time:6.1f} s   expected {exp}")
    print(f"TOTAL: {study.total_cycle_time_s / 60:.2f} min (expected 3.38)   mismatches: {mism}")

    out = "data/reference_test.xlsx"
    with open(out, "wb") as f:
        f.write(excel.export(study))
    print("Excel written:", out)


if __name__ == "__main__":
    main()
