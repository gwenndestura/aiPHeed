"""E25 step 0: verify the hash lists of the read-only experiments E17, E18, E23, E24, E24v2 (and record the
earlier E25 attempt). Hashes are computed here and compared with each experiment's own committed hash list;
nothing is typed.

Two copies exist and both are checked:
  * COMMIT   = commit 5113ae5 (branch e25-window-2021-2026), extracted read-only with `git archive` into the
               session scratchpad (path given on the command line). This is the complete record.
  * WORKTREE = the folders in the current working tree (branch ui/no-data-quarters-risk-band), where the
               tracked files of these experiments are absent and only untracked leftovers remain.
Usage: python -B runner/verify_readonly.py <snapshot_root>   (snapshot_root contains aipheed-backend-aligned/)
Writes runs/readonly_verification.json and docs/READONLY_VERIFICATION.md.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
WT_EXPS = EXP.parent
LISTS = {
    "E17": ("2026-10-13_E17_Objectives_Evaluation", "E17_FILES_SHA256.txt"),
    "E18": ("2026-10-13_E18_Objectives_Improvement", "E18_FILES_SHA256.txt"),
    "E23": ("2026-10-13_E23_Chapter1_Complete", "E23_FILES_SHA256.txt"),
    "E24": ("2026-10-14_E24_Resolve_Forecasting", "E24_FILES_SHA256.txt"),
    "E24v2": ("2026-10-14_E24v2_Reliable_Forecasting", "E24V2_FILES_SHA256.txt"),
}
EARLIER_E25 = "2026-10-14_E25_Window_2021_2026"
SKIP_PARTS = {"node_modules", "__pycache__", ".pytest_cache", "dist", ".vite"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def parse_list(p: Path) -> dict[str, str]:
    out = {}
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        h, rest = ln.split(None, 1)
        rel = rest.lstrip("*").strip()
        if rel.startswith("./"):
            rel = rel[2:]
        out[rel.replace("\\", "/")] = h.lower()
    return out


def walk(root: Path) -> set[str]:
    if not root.exists():
        return set()
    out = set()
    for p in root.rglob("*"):
        if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_PARTS):
            out.add(p.relative_to(root).as_posix())
    return out


def eol_variants(p: Path) -> set[str]:
    """Hashes of the file after undoing git's line-ending normalization only (core.autocrlf=true stores LF;
    the listed hash may have been taken from the CRLF or the LF working-tree form, or from a shell-captured
    log with mixed endings: CRLF on the first j lines and LF on the rest, or the reverse). The text is the same."""
    b = p.read_bytes()
    lf = b.replace(b"\r\n", b"\n")
    out = {hashlib.sha256(lf).hexdigest(), hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest()}
    parts = lf.split(b"\n")
    n = len(parts) - 1
    if n <= 2000:
        for j in range(n + 1):
            for a, z in ((b"\r\n", b"\n"), (b"\n", b"\r\n")):
                ends = [a] * j + [z] * (n - j)
                out.add(hashlib.sha256(b"".join(x + e for x, e in zip(parts[:-1], ends)) + parts[-1]).hexdigest())
    return out


def check(root: Path, listed: dict[str, str], list_name: str) -> dict:
    present = walk(root)
    match, eol_only, mismatch, missing = [], [], [], []
    for rel, want in sorted(listed.items()):
        f = root / rel
        if not f.exists():
            missing.append(rel)
        elif sha(f) == want:
            match.append(rel)
        elif want in eol_variants(f):
            eol_only.append(rel)
        else:
            mismatch.append({"file": rel, "listed": want, "actual": sha(f)})
    extra = sorted(present - set(listed) - {list_name})
    return {"root": str(root), "exists": root.exists(), "listed": len(listed), "match": len(match),
            "eol_only": len(eol_only), "eol_only_files": eol_only, "mismatch": mismatch, "missing": len(missing),
            "missing_files": missing, "extra_not_in_list": extra}


def main(snapshot_root: Path):
    snap = snapshot_root / "aipheed-backend-aligned" / "experiments"
    res = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "snapshot": str(snap),
           "commit": "5113ae5 (branch e25-window-2021-2026)", "experiments": {}}
    for name, (folder, lst) in LISTS.items():
        listed = parse_list(snap / folder / lst)
        c = check(snap / folder, listed, lst)
        w = check(WT_EXPS / folder, listed, lst)
        w_present_listed = c["listed"] - w["missing"]
        res["experiments"][name] = {
            "folder": folder, "hash_list": lst, "hash_list_sha256": sha(snap / folder / lst),
            "commit": c, "worktree": w,
            "verdict_commit": "IDENTICAL to hash list" if not c["mismatch"] and not c["missing"] else "DIFFERS",
            "verdict_worktree": ("ABSENT" if not w["exists"] else
                                 ("all present listed files identical; " if not w["mismatch"] else "MISMATCH; ")
                                 + f"{w_present_listed} of {c['listed']} listed files present"),
        }
    e = snap / EARLIER_E25
    res["earlier_E25"] = {"folder": EARLIER_E25, "files": {r: sha(e / r) for r in sorted(walk(e))},
                          "worktree_files": sorted(walk(WT_EXPS / EARLIER_E25))}
    (EXP / "runs").mkdir(exist_ok=True)
    (EXP / "runs" / "readonly_verification.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    lines = ["# Read-only experiments: hash-list verification",
             "",
             f"Generated {res['generated_utc']} by `runner/verify_readonly.py` (hashes computed, not typed).",
             "",
             "A file counts as **identical** if its bytes equal the listed hash. **Line-ending only** means the bytes "
             "equal the listed hash once git's CRLF/LF normalization (core.autocrlf=true) is undone, including "
             "shell-captured logs with mixed endings; the text is unchanged. **Content differs** means no such form "
             "matches.",
             "",
             "| Experiment | Listed files | Commit 5113ae5: identical / line-ending only / content differs / missing | Working tree: identical / line-ending only / content differs / missing | Extra files in working tree (not in list) |",
             "|---|---|---|---|---|"]
    for name, r in res["experiments"].items():
        c, w = r["commit"], r["worktree"]
        lines.append(f"| {name} | {c['listed']} | {c['match']} / {c['eol_only']} / {len(c['mismatch'])} / {c['missing']} | "
                     + (f"{w['match']} / {w['eol_only']} / {len(w['mismatch'])} / {w['missing']}" if w["exists"]
                        else "folder absent")
                     + f" | {len(w['extra_not_in_list'])} |")
    lines += ["", "## Content differences and missing files", ""]
    for name, r in res["experiments"].items():
        for side in ("commit", "worktree"):
            for m in r[side]["mismatch"]:
                lines.append(f"- **{name} {side}: content differs** `{m['file']}` (listed {m['listed']}, actual {m['actual']})")
        for m in r["commit"]["missing_files"]:
            lines.append(f"- {name} commit: listed file not in commit 5113ae5: `{m}`")
        if r["worktree"]["extra_not_in_list"]:
            ex = r["worktree"]["extra_not_in_list"]
            lines.append(f"- {name} working tree has {len(ex)} file(s) not in the hash list, e.g. "
                         + ", ".join(f"`{x}`" for x in ex[:6]))
    (EXP / "docs").mkdir(exist_ok=True)
    (EXP / "docs" / "READONLY_VERIFICATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:16]))
    print(f"... {len(lines) - 16} more lines in docs/READONLY_VERIFICATION.md")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
