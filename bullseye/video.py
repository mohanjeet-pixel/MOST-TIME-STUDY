"""MTS/MP4 -> small 'proxy' MP4 that is cheap to upload, analyse and play in the browser.

Uses the FFmpeg binary bundled with imageio-ffmpeg, so no system install is needed.
"""
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def probe_duration(path: Path) -> float:
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)],
                       capture_output=True, text=True, errors="ignore")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
    if not m:
        return 0.0
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def make_proxy(src: Path, dst: Path, height: int = 480, fps: int = 10) -> Path:
    """Deinterlace (MTS is usually 1080i), scale to 480p, drop audio, H.264.

    A 5-minute 1080i MTS (~600 MB) becomes ~10-20 MB. Gemini samples 1 frame/s anyway,
    and 10 fps keeps browser playback smooth enough for frame-accurate review.
    """
    cmd = [
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
        "-vf", f"yadif=deint=interlaced,scale=-2:{height},fps={fps}",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {r.stderr[-800:]}")
    return dst
