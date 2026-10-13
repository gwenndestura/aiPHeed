"""
scripts/iso25010_summary.py

Objective 5 / Hypotheses 4 and 5: summarise the ISO/IEC 25010 questionnaires.

Section 3.7 collects two instruments through Google Forms: the System Accuracy
Questionnaire (Functional Suitability and Accuracy; 25 DA Region IV-A system
evaluators) and the Usability Questionnaire (appropriateness recognizability,
learnability, operability, user interface aesthetics; 25 DEPDev Region IV-A
evaluators), both with Likert-scale items.

This script only summarises responses that were actually collected. It never
generates, imputes or simulates a response. Given each form's CSV export and a
mapping from item columns to ISO/IEC 25010 characteristics, it reports per item
and per characteristic: number of responses, mean and standard deviation.

Chapter III does not state the Likert scale's verbal interpretation bands, so
none is assumed. If the researchers' adviser approves a scale, pass it with
--scale (a JSON list of {"min": .., "max": .., "label": ..}) and each mean is
labelled with it; otherwise means are reported without a label.

Mapping file (JSON):
    {"instrument": "System Accuracy Questionnaire",
     "group": "DA Region IV-A system evaluators",
     "characteristics": {
        "Functional completeness": ["Q1 ...", "Q2 ..."],
        "Functional correctness":  ["Q3 ..."]}}

Usage:
    python -m scripts.iso25010_summary --csv responses.csv --mapping mapping.json \
        [--scale scale.json] [--out data/evaluation/system_accuracy_summary.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _label(mean: float, scale: list[dict] | None) -> str | None:
    if not scale or pd.isna(mean):
        return None
    for band in scale:
        if band["min"] <= mean <= band["max"]:
            return band["label"]
    return None


def summarise(csv_path: Path, mapping: dict, scale: list[dict] | None = None) -> dict:
    df = pd.read_csv(csv_path)
    missing = [c for cols in mapping["characteristics"].values() for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Item columns not found in {csv_path}: {missing}")

    out = {"instrument": mapping.get("instrument"), "group": mapping.get("group"),
           "n_respondents": int(len(df)), "characteristics": {},
           "scale_applied": bool(scale)}
    all_items = []
    for name, cols in mapping["characteristics"].items():
        items = df[cols].apply(pd.to_numeric, errors="coerce")
        all_items.append(items)
        per_resp = items.mean(axis=1)
        out["characteristics"][name] = {
            "items": {c: {"n": int(items[c].notna().sum()),
                          "mean": round(float(items[c].mean()), 3),
                          "sd": round(float(items[c].std(ddof=1)), 3)} for c in cols},
            "n": int(per_resp.notna().sum()),
            "mean": round(float(per_resp.mean()), 3),
            "sd": round(float(per_resp.std(ddof=1)), 3),
            "interpretation": _label(per_resp.mean(), scale),
        }
    overall = pd.concat(all_items, axis=1).mean(axis=1)
    out["overall"] = {"n": int(overall.notna().sum()),
                      "mean": round(float(overall.mean()), 3),
                      "sd": round(float(overall.std(ddof=1)), 3),
                      "interpretation": _label(overall.mean(), scale)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--mapping", required=True, type=Path)
    ap.add_argument("--scale", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    mapping = json.loads(a.mapping.read_text(encoding="utf-8"))
    scale = json.loads(a.scale.read_text(encoding="utf-8")) if a.scale else None
    result = summarise(a.csv, mapping, scale)
    text = json.dumps(result, indent=2)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
