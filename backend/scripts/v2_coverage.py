"""
Line coverage of the forecasting package, the hunger-forecast API router and safe_load, measured with the standard
library only (sys.settrace + threading.settrace; coverage.py / pytest-cov are not installed in the venv and nothing
was downloaded). Executable lines = the line table of every code object compiled from the file (co_lines), the same
notion of a statement line that coverage.py uses, minus nothing. Runs the given test files in-process with pytest.

    cd backend && python -I scripts/v2_coverage.py [v4]   -> docs/aipheed/<v2|v4>/results/coverage.json / coverage.txt
"""
from __future__ import annotations

import json
import sys
import threading
import types
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
OUT = BACKEND.parent / "docs" / "aipheed" / (sys.argv[1] if len(sys.argv) > 1 else "v2") / "results"   # e.g. v4
TARGETS = sorted([*(BACKEND / "app" / "forecasting").rglob("*.py"), BACKEND / "app" / "api" / "v1" / "hunger_forecast.py",
                  BACKEND / "app" / "paths.py"])
TESTS = ["tests/unit/test_v2_core.py", "tests/unit/test_forecasting_core.py", "tests/unit/test_safe_load.py",
         "tests/unit/test_protocol_lock.py", "tests/unit/test_v2_preregistration.py", "tests/unit/test_v2_paths.py",
         "tests/unit/test_v2_legacy_leakage.py", "tests/unit/test_v4_core.py",
         "tests/unit/test_v4_preregistration.py"]

WANT = {str(p.resolve()).lower() for p in TARGETS}
hits: dict[str, set[int]] = defaultdict(set)


def _tracer(frame, event, arg):
    f = frame.f_code.co_filename.lower()
    if f not in WANT:
        return None
    hits[f].add(frame.f_lineno)

    def local(fr, ev, a):
        if ev in ("line", "call"):
            hits[f].add(fr.f_lineno)
        return local
    return local


def executable(path: Path) -> set[int]:
    lines: set[int] = set()

    def walk(co: types.CodeType):
        for _, _, ln in co.co_lines():
            if ln is not None:
                lines.add(ln)
        for c in co.co_consts:
            if isinstance(c, types.CodeType):
                walk(c)
    walk(compile(path.read_text(encoding="utf-8"), str(path), "exec"))
    return lines


def main() -> None:
    import pytest
    threading.settrace(_tracer)
    sys.settrace(_tracer)
    try:
        rc = pytest.main(["-q", "-p", "no:cacheprovider", *TESTS])
    finally:
        sys.settrace(None)
        threading.settrace(None)
    rows, tot_e, tot_h = [], 0, 0
    for p in TARGETS:
        ex = executable(p)
        h = hits.get(str(p.resolve()).lower(), set()) & ex
        tot_e, tot_h = tot_e + len(ex), tot_h + len(h)
        rows.append({"file": str(p.relative_to(BACKEND)).replace("\\", "/"), "lines": len(ex), "hit": len(h),
                     "pct": round(100 * len(h) / len(ex), 1) if ex else 100.0, "missed": sorted(ex - h)})
    res = {"pytest_exit_code": int(rc), "tests": TESTS, "total_lines": tot_e, "total_hit": tot_h,
           "total_pct": round(100 * tot_h / tot_e, 1), "files": rows,
           "method": "stdlib sys.settrace + threading.settrace line tracing; executable lines from code-object line tables"}
    (OUT / "coverage.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8", newline="\n")
    txt = [f"{r['file']:55s} {r['hit']:4d}/{r['lines']:4d}  {r['pct']:5.1f}%" for r in rows]
    txt.append(f"{'TOTAL':55s} {tot_h:4d}/{tot_e:4d}  {res['total_pct']:5.1f}%   (pytest exit code {rc})")
    (OUT / "coverage.txt").write_text("\n".join(txt) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(txt))


if __name__ == "__main__":
    main()
