"""E25 step 0b: copy the authorized inputs that exist only in commit 5113ae5 into inputs/, byte-identical to the
hash each experiment pinned. The pins are read programmatically from the E17/E18 guards and the E24v2 acquisition
manifest in the commit snapshot (nothing is typed). A file is written only when its bytes reproduce the pinned
hash exactly (git stores LF; the pinned originals were CRLF, so the CRLF form is reconstructed and re-verified).
Also copies the E24v2 prospective seals (forecasts only, no data) and the E24 LGU table, each with its listed hash.
Usage: python -B runner/materialize_inputs.py <snapshot_root>
Writes inputs/INPUTS_MANIFEST.json.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
WT_AL = EXP.parents[1]


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load(name, p):
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def forms(b: bytes):
    lf = b.replace(b"\r\n", b"\n")
    return [("exact", b), ("crlf", lf.replace(b"\n", b"\r\n")), ("lf", lf)]


def put(src: Path, dst_rel: str, want: str, source_note: str, manifest: list):
    b = src.read_bytes()
    for kind, cand in forms(b):
        if sha_b(cand) == want:
            dst = EXP / "inputs" / dst_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(cand)
            assert sha_b(dst.read_bytes()) == want
            manifest.append({"file": f"inputs/{dst_rel}", "sha256": want, "source": source_note,
                             "bytes_form_restored": kind})
            return
    raise SystemExit(f"cannot reproduce pinned hash for {src}")


def main(snapshot_root: Path):
    snap = snapshot_root / "aipheed-backend-aligned"
    ex = snap / "experiments"
    gpaths = {"E17": ex / "2026-10-13_E17_Objectives_Evaluation" / "runner" / "guard.py",
              "E18": ex / "2026-10-13_E18_Objectives_Improvement" / "runner" / "guard.py"}
    man, pins = [], {}
    for tag, gp in gpaths.items():
        g = load(f"g{tag}", gp)
        for p, (want, flt) in g.ALLOW.items():
            p = Path(p).resolve()
            try:
                rel = p.relative_to(WT_AL.resolve())
                dst_rel = rel.as_posix().replace(
                    "experiments/2026-10-12_E12_SWS_Scoring_Comparison/runs/20261012T151208Z/", "e12/")
            except ValueError:
                rel, dst_rel = None, None          # production backend file (read in place)
            if p.exists():
                read_at = p
            else:
                if not any(m["file"] == f"inputs/{dst_rel}" for m in man):
                    put(snap / rel, dst_rel, want, f"commit 5113ae5:{rel.as_posix()} (pinned by E17/E18 guard)", man)
                read_at = (EXP / "inputs" / dst_rel).resolve()
            key = str(p)
            if key in pins and pins[key]["sha256"] != want:
                raise SystemExit(f"E17 and E18 pin different hashes for {p}")
            e = pins.setdefault(key, {"original_path": key, "read_path": str(read_at), "sha256": want,
                                      "read_time_filter": list(flt) if flt else None, "pinned_by": []})
            e["pinned_by"].append(f"{tag} guard.py sha256={sha_b(gp.read_bytes())}")
    # E24v2 in-window CPI index file (2021-2025 rows only), pinned by E24v2's acquisition manifest
    v2 = ex / "2026-10-14_E24v2_Reliable_Forecasting"
    am = json.loads((v2 / "acquisition" / "ACQUISITION_MANIFEST.json").read_text(encoding="utf-8"))
    name = "cpi_index_2021_2025_ACP22.csv"
    put(v2 / "acquisition" / name, f"e24v2/{name}", am["tidy_files"][name]["sha256"],
        "commit 5113ae5: E24v2 acquisition (public PSA OpenSTAT 0012M4ACP22, 2021-01..2025-12); pinned by "
        "E24v2 ACQUISITION_MANIFEST.json", man)
    # E24v2 seals (forecast records, no data) and E24 LGU table: verified against their experiment hash lists
    def listed(folder, lst):
        out = {}
        for ln in (ex / folder / lst).read_text(encoding="utf-8").splitlines():
            if ln.strip():
                h, r = ln.split(None, 1)
                out[r.lstrip("*").strip().removeprefix("./")] = h
        return out
    l2 = listed("2026-10-14_E24v2_Reliable_Forecasting", "E24V2_FILES_SHA256.txt")
    for rel, h in sorted(l2.items()):
        if rel.startswith("runs/SEAL_"):
            put(v2 / rel, f"e24v2/{rel}", h, f"commit 5113ae5: E24v2 {rel} (E24V2_FILES_SHA256.txt)", man)
    l24 = listed("2026-10-14_E24_Resolve_Forecasting", "E24_FILES_SHA256.txt")
    for rel, h in sorted(l24.items()):
        if rel.startswith("runs/2026101") and rel.endswith(("SEAL_T1.json", "SEAL_T2.json")):
            put(ex / "2026-10-14_E24_Resolve_Forecasting" / rel, f"e24/{rel}", h,
                f"commit 5113ae5: E24 {rel} (E24_FILES_SHA256.txt)", man)
    (EXP / "inputs" / "INPUTS_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    (EXP / "inputs" / "PINS.json").write_text(json.dumps(
        {"generated_from": "E17/E18 runner/guard.py ALLOW (commit 5113ae5), loaded programmatically",
         "authorized_2026_note": "E18 entries for the 2026 CPI file, the release-date file and the production SWS "
                                 "parquet carry the 2026-10-13 authorization of January-June 2026 (E18 "
                                 "DATA_AUTHORIZATION_RECORD.md).",
         "pins": list(pins.values())}, indent=1), encoding="utf-8")
    for m in man:
        print(m["file"], m["bytes_form_restored"], m["sha256"][:12])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
