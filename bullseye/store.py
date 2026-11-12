"""File-based storage: one folder per study. Swap for Postgres when you go multi-user."""
import threading
from pathlib import Path

from . import config
from .models import Study

_lock = threading.Lock()


def folder(study_id: str) -> Path:
    p = config.DATA_DIR / study_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def save(study: Study) -> Study:
    with _lock:
        (folder(study.id) / "study.json").write_text(study.model_dump_json(indent=2), encoding="utf-8")
    return study


def load(study_id: str) -> Study | None:
    if not study_id.isalnum():
        return None
    p = config.DATA_DIR / study_id / "study.json"
    if not p.exists():
        return None
    return Study.model_validate_json(p.read_text(encoding="utf-8"))


def all_studies() -> list[Study]:
    out = []
    for p in sorted(config.DATA_DIR.glob("*/study.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            out.append(Study.model_validate_json(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return out
