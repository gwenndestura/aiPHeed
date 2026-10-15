"""E34: promote the E31 dashboard (dashboard_dev) into frontend/ with a per-file three-way merge.

base   = frontend/ at 1658d31 (the commit dashboard_dev was copied from: 131/139 files identical, the best match)
main   = frontend/ now (adds 702adb4 lakes/component-city names/glossary and 2f22552 About title after the base)
e31    = E31 dashboard_dev/ (E25-E31 pages, records, PDFs and fixes)

Per file: identical -> skip; only E31 changed -> take E31; only main changed -> keep main; both changed -> `git merge-file`
(conflicts are written to runs/e34_frontend_conflicts.txt and the file is left untouched). Files present only in main are
kept. Only src/ and public/ are touched. Run on branch e34-main-app-integration; `git checkout -- frontend` and deleting
the listed new files reverts it.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"C:\Users\admin\aipheed")
DD = ROOT / "aipheed-backend-aligned" / "experiments" / "E31_Chapter1_Completion" / "dashboard_dev"
FE = ROOT / "frontend"
BASE = "1658d31"
OUT = Path(__file__).resolve().parents[1] / "runs"


def lf(b: bytes | None) -> bytes | None:
    """core.autocrlf=true leaves CRLF in the working tree; compare and merge on LF (git normalises on commit)."""
    return None if b is None else b.replace(b"\r\n", b"\n")


def base_bytes(rel: str) -> bytes | None:
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE}:frontend/{rel}"], capture_output=True)
    return lf(r.stdout) if r.returncode == 0 else None


def main(dry: bool):
    log = {"taken_from_e31": [], "new_from_e31": [], "kept_main": [], "merged": [], "conflicts": [], "identical": 0}
    for sub in ("src", "public"):
        for p in sorted((DD / sub).rglob("*")):
            if p.is_dir():
                continue
            rel = p.relative_to(DD).as_posix()
            e31 = lf(p.read_bytes())
            q = FE / rel
            main_b = lf(q.read_bytes()) if q.exists() else None
            if main_b == e31:
                log["identical"] += 1
                continue
            base = base_bytes(rel)
            if main_b is None:
                log["new_from_e31"].append(rel)
                if not dry:
                    q.parent.mkdir(parents=True, exist_ok=True)
                    q.write_bytes(e31)
            elif main_b == base:
                log["taken_from_e31"].append(rel)
                if not dry:
                    q.write_bytes(e31)
            elif e31 == base:
                log["kept_main"].append(rel)
            else:
                with tempfile.TemporaryDirectory() as td:
                    a, b, c = Path(td, "main"), Path(td, "base"), Path(td, "e31")
                    a.write_bytes(main_b), b.write_bytes(base or b""), c.write_bytes(e31)
                    r = subprocess.run(["git", "merge-file", "-p", "-L", "main", "-L", "base", "-L", "e31",
                                        str(a), str(b), str(c)], capture_output=True)
                    if r.returncode == 0:
                        log["merged"].append(rel)
                        if not dry:
                            q.write_bytes(r.stdout)
                    else:
                        log["conflicts"].append({"file": rel, "n_conflicts": r.returncode})
                        (OUT / ("conflict_" + rel.replace("/", "__"))).write_bytes(r.stdout)
    (OUT / ("e34_frontend_promotion" + ("_dry" if dry else "") + ".json")).write_text(json.dumps(log, indent=1),
                                                                                        encoding="utf-8")
    print(json.dumps({k: (v if isinstance(v, int) else len(v)) for k, v in log.items()}),
          "\nmerged:", log["merged"], "\nkept_main:", log["kept_main"], "\nconflicts:", log["conflicts"])


if __name__ == "__main__":
    main(dry="--apply" not in sys.argv)
