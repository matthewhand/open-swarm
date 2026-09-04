"""Lock: shipped source must not contain leftover git conflict markers (#454)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKERS = ("<<<<<<< ", ">>>>>>> ", "=======",)


def test_spa_api_ts_has_no_conflict_markers():
    text = (ROOT / "webui/frontend/src/lib/api.ts").read_text(encoding="utf-8")
    for marker in MARKERS:
        assert marker not in text, f"leftover {marker!r} in webui/frontend/src/lib/api.ts"
