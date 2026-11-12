"""Create a DEMO study from the CS PRE BENDING-1 reference (synthetic test-pattern video).

Run:  .venv\\Scripts\\python.exe -m tests.seed_demo
"""
import subprocess

from bullseye import most, store, video
from bullseye.models import Operation, Step, Study
from tests.test_most import REF


def main():
    sid = "demo0000ref1"
    d = store.folder(sid)
    study = Study(id=sid, title="DEMO - CS PRE BENDING-1", study_by="GURUMURTHY", date="12/05/2021",
                  video_file="original.mp4", proxy_file="proxy.mp4", status="ready", model="reference data")
    t = 2.0
    for name, rows in REF.items():
        steps = []
        for desc, act, kw, _, _ in rows:
            kw = dict(kw)
            kw.pop("start_s", None), kw.pop("end_s", None)
            s = Step(description=desc, activity=act, **kw)
            most.compute_step(s)
            dur = 65.0 if act == "PROCESS" else max(s.cycle_time * 0.9, 1.0)
            s.start_s, s.end_s = round(t, 1), round(t + dur, 1)
            t += dur + 1.5
            steps.append(s)
        study.operations.append(Operation(opn_no=0, name=name, steps=steps))
    total = int(t + 5)
    subprocess.run([video.FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", f"testsrc2=size=854x480:rate=10:duration={total}", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "32", "-pix_fmt", "yuv420p", str(d / "proxy.mp4")], check=True)
    (d / "original.mp4").write_bytes(b"")
    study.video_duration_s = total
    most.compute_study(study)
    store.save(study)
    print(f"Demo study created: {sid}  ({total}s video, {study.total_cycle_time_s / 60:.2f} min MOST)")


if __name__ == "__main__":
    main()
