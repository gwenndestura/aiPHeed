"""
Objective 5: scoring of the aiPHeed Post-Survey Questionnaire (ISO/IEC 25010 Functional Suitability and Usability, plus
forecast relevance and DA operational fit). Local only.

Input: a CSV of REAL respondent answers in the layout of docs/e196/iso25010_template.csv (one row per respondent; Likert
items 1-5; blank = not answered). The script refuses files that are, or contain, synthetic responses: survey results must
come from actual DA Region IV-A personnel.

    python -m app.e196.iso25010 <responses.csv> [--out docs/e196/ISO25010_RESULTS.md]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

SECTIONS = {
    "S2": ("Forecast Accuracy & Relevance", [
        "The province-level risk classifications (HIGH/LOW) shown by aiPHeed appear consistent with known conditions in CALABARZON.",
        "The municipal/city risk rankings reflect realistic relative vulnerability across LGUs.",
        "The SHAP-based explanations helped me understand why a forecast was classified as high or low risk.",
        "The forecast lead time (how far ahead aiPHeed predicts) is useful for planning purposes.",
        "The early-warning alerts would provide meaningful lead time for an actual intervention."]),
    "S3": ("Functionality (ISO/IEC 25010 Functional Suitability)", [
        "The dashboard provides all the functions needed to review food-insecurity risk (map, rankings, alerts, explanations, PDF export). [Functional completeness]",
        "The system performs its forecasting and reporting functions correctly, without visible errors. [Functional correctness]",
        "The admin/evaluator review workflow (PENDING -> STAGED -> PUBLISHED) is appropriate for ensuring human oversight before publication. [Functional appropriateness]",
        "The data-sufficiency flags (e.g., LIMITED_SIGNAL) gave me useful context about forecast confidence. [Functional appropriateness]"]),
    "S4": ("Usability (ISO/IEC 25010)", [
        "I could quickly tell what the system is for and how it could help my work. (Appropriateness recognizability)",
        "I could learn to use the dashboard's main features without much difficulty. (Learnability)",
        "Navigating the map, time slider, and rankings table felt straightforward. (Operability)",
        "The system helped prevent or clearly flagged potential mistakes. (User error protection)",
        "The dashboard's layout and visuals were clear and professional. (User interface aesthetics)",
        "The interface was usable regardless of my technical background. (Accessibility)"]),
    "S5": ("Alignment with DA Operations", [
        "aiPHeed's outputs could realistically support DA Region IV-A's regional S&T mandate.",
        "The forecasts and alerts could be usefully cascaded to LGU offices",
        "The SHAP-attributed explanations would be sufficient for technical review/sign-off before publishing a forecast.",
        "Relying on public data only makes aiPHeed easier to adopt operationally."]),
}
PROFILE = ["respondent_id", "consent_signature", "position", "office_unit", "province_area", "years_in_role", "response_source"]
OPEN = ["open_most_useful", "open_comparison", "open_improvements", "open_challenges", "open_recommend"]


def items():
    return [f"{s}_{i + 1}" for s, (_, q) in SECTIONS.items() for i in range(len(q))]


def verbal(m: float) -> str:
    """Conventional 5-point interpretation bands (width 0.80)."""
    if np.isnan(m):
        return "-"
    return ("Strongly Disagree" if m <= 1.80 else "Disagree" if m <= 2.60 else "Neutral" if m <= 3.40 else "Agree" if m <= 4.20 else "Strongly Agree")


def template(path: Path) -> None:
    pd.DataFrame(columns=PROFILE + items() + OPEN).to_csv(path, index=False)


def load(path: Path) -> pd.DataFrame:
    if "synthetic" in path.name.lower():
        sys.exit("refused: the file name says synthetic. ISO/IEC 25010 results must come from real DA respondents.")
    d = pd.read_csv(path)
    if "response_source" not in d or (d["response_source"].astype(str).str.lower() != "real").any():
        sys.exit("refused: every row needs response_source = real (actual DA Region IV-A respondent).")
    if d["consent_signature"].astype(str).str.strip().str.lower().isin(["", "nan"]).any():
        sys.exit("refused: a row has no consent signature (Sgd. Full Name).")
    for c in items():
        v = pd.to_numeric(d[c], errors="coerce")
        if ((v < 1) | (v > 5)).any():
            sys.exit(f"invalid Likert value in {c} (must be 1-5)")
        d[c] = v
    return d


def score(d: pd.DataFrame) -> str:
    lines = [f"# aiPHeed Post-Survey results (ISO/IEC 25010) - n = {len(d)} respondents", "",
             "Interpretation: 1.00-1.80 Strongly Disagree, 1.81-2.60 Disagree, 2.61-3.40 Neutral, 3.41-4.20 Agree, 4.21-5.00 Strongly Agree.",
             "Test: one-sample Wilcoxon signed-rank against the neutral value 3 (one-sided, greater).", ""]
    summary = []
    for s, (title, qs) in SECTIONS.items():
        lines += [f"## {title}", "", "| # | Statement | n | Mean | SD | Interpretation |", "|---|---|---|---|---|---|"]
        cols = [f"{s}_{i + 1}" for i in range(len(qs))]
        for i, (c, q) in enumerate(zip(cols, qs), 1):
            v = d[c].dropna()
            lines.append(f"| {i} | {q} | {len(v)} | {v.mean():.2f} | {v.std(ddof=1):.2f} | {verbal(v.mean())} |")
        per = d[cols].mean(axis=1).dropna()
        p = wilcoxon(per - 3, alternative="greater").pvalue if len(per) >= 6 and (per != 3).any() else float("nan")
        m = float(d[cols].stack().mean())
        lines += [f"| | **Section mean** | {len(per)} | **{m:.2f}** | {per.std(ddof=1):.2f} | **{verbal(m)}** |", "",
                  f"Respondent-level section mean > 3: Wilcoxon p = {p:.4f}" if p == p else "Too few respondents for the test.", ""]
        summary.append((title, m, verbal(m), p))
    lines += ["## Summary", "", "| Section | Mean | Interpretation | p (> neutral) |", "|---|---|---|---|"]
    lines += [f"| {t} | {m:.2f} | {v} | {p:.4f} |" if p == p else f"| {t} | {m:.2f} | {v} | - |" for t, m, v, p in summary]
    lines += ["", "## Open-ended responses", ""]
    for c in OPEN:
        if c in d:
            ans = [str(x).strip() for x in d[c].dropna() if str(x).strip()]
            lines += [f"**{c.replace('open_', '').replace('_', ' ')}** ({len(ans)} answers)", ""] + [f"- {a}" for a in ans] + [""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("responses", nargs="?")
    ap.add_argument("--out", default=None)
    ap.add_argument("--template", default=None, help="write an empty response template CSV to this path and exit")
    a = ap.parse_args()
    if a.template:
        template(Path(a.template))
        print("template written:", a.template)
        return
    if not a.responses:
        sys.exit("usage: python -m app.e196.iso25010 <responses.csv> [--out FILE] | --template FILE")
    md = score(load(Path(a.responses)))
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
        print("written:", a.out)
    else:
        print(md)


if __name__ == "__main__":
    main()
