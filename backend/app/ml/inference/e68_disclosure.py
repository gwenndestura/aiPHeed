"""
E68 (AIPHEED_LEAD2_MODEL=e68 only): the E67 layered system with the E68 corrections to what the dashboard says.

Numbers are unchanged (E58 record: E56-TUNED LightGBM, Lead-2, E58-EW warning; E66 climate watch; exact LGU ranks).
No E68 model variant beat the served model by the pre-registered rule
(aipheed-backend-aligned/experiments/E68_Resolve_E67_Critical_Failures), so E68 changes the meaning shown, not the
score. data/e68/e68_disclosure.json, built only from the E68 outputs (runner/r4_build_disclosure.py), adds:
  * inputStatus: every input at the issue date classified as observed | observed_zero | missing | stale |
    substituted | too_few_articles | not_collected, with its period and data age;
  * affordability: observed headline and food inflation against the province's usual 2021-2022 level;
  * the target wording (an exploratory food-stress score, not household food insecurity);
  * the E68 El Nino finding (the only in-window episode coincided with falling inflation, so its price effect cannot
    be estimated) and the national-input finding.
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
from pathlib import Path

from app.ml.inference import e67_disclosure as D67

DISCLOSURE = Path(os.getenv("AIPHEED_E68_DISCLOSURE", "data/e68/e68_disclosure.json"))
PROBLEM = ("missing", "stale", "substituted", "too_few_articles", "not_collected")
WORDS = {"missing": "missing", "stale": "out of date", "substituted": "stored as a placeholder",
         "too_few_articles": "too few news articles", "not_collected": "not collected"}


class DisclosureError(RuntimeError):
    pass


@functools.lru_cache(maxsize=2)
def _load(path: str, mtime_ns: int) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    body = {k: v for k, v in d.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != d.get("content_sha256"):
        raise DisclosureError("E68 disclosure failed its integrity check")
    return d


def disclosure() -> dict | None:
    if not DISCLOSURE.exists():
        return None
    return _load(str(DISCLOSURE), DISCLOSURE.stat().st_mtime_ns)


def event() -> str:
    return ("the exploratory food-stress score (high regional hunger together with provincial food-price pressure; "
            "not a measure of household food insecurity)")


def _inputs_text(items: list[dict]) -> str:
    groups: dict[str, list[str]] = {}
    for i in items:
        if i["status"] in PROBLEM:
            groups.setdefault(i["status"], []).append(i["label"].split(" (")[0])
    n_obs = sum(i["status"] in ("observed", "observed_zero") for i in items)
    parts = [f"{WORDS[s]}: {', '.join(dict.fromkeys(v))}" for s, v in groups.items()]
    return (f"Inputs at the issue date: {n_obs} of {len(items)} observed" + ("; " + "; ".join(parts) if parts else "")
            + ". Missing or uncollected inputs are treated as unknown, not as no risk.")


def for_summary(rec: dict, quarter: str, province_code: str | None, kind: str, result: str,
                cfsw: dict | None) -> dict | None:
    if kind not in ("forecast", "earlier_forecast"):
        return None
    d = disclosure()
    e67 = D67.for_summary(rec, quarter, province_code, kind, result, cfsw)
    if d is None or e67 is None:
        return None
    parts = []
    names = [rec["provinces"][province_code]["name"]] if province_code else list(d["inputStatus"].get(quarter, {}))
    status = d["inputStatus"].get(quarter, {})
    afford = d["affordability"].get(quarter, {})
    watch_on = bool(cfsw and (str(cfsw.get("level", "")).startswith("CLIMATE WATCH") or cfsw.get("sentence")))
    if province_code:
        name = names[0]
        low = (D67.disclosure() or {}).get("lowUnderWatch", {}).get(quarter, {}).get(name)
        if low and result == "LOW" and watch_on:
            parts.append(D67._low_text(quarter, name, low))
        if result == "LOW" and watch_on:
            parts.append(d["elNinoFinding"])
        a = afford.get(name)
        if a and a["headlineAbove"]:
            parts.append(f"Affordability: headline inflation in {name} ({a['headline']:.1f}%) is above its usual 2021-2022 "
                         f"level ({a['headlineUsual']:.1f}%). The score counts this as less food-price pressure, but for "
                         "households it means a peso buys less.")
        items = (status.get(name) or {}).get("inputs", [])
    else:
        if result == "LOW" and watch_on:
            parts.append(d["elNinoFinding"])
        above = [n for n, a in afford.items() if a["headlineAbove"]]
        if above:
            parts.append(f"Affordability: headline inflation is above its usual 2021-2022 level in {', '.join(above)}; the "
                         "score counts this as less food-price pressure, although a peso buys less.")
        # region scope: only the input problems shared by every province (national/regional inputs), no list
        per = [{(i["key"], i["status"]) for i in (status.get(n) or {}).get("inputs", [])} for n in names]
        common = set.intersection(*per) if per else set()
        items = [i for i in (status.get(names[0]) or {}).get("inputs", []) if (i["key"], i["status"]) in common] if names else []
    if items:
        parts.append(_inputs_text(items) if province_code else _inputs_text(items).replace(
            "Inputs at the issue date: ", "Inputs common to all provinces at the issue date: "))
    ident = {**e67["modelIdentity"], "servingMode": "e68", "lead2Accuracy": d["evaluation"]}
    parts.append(f"Model: {ident['servedModel']}, Lead-2, issued {ident['issued']}. {d['evaluation']}")
    return {"sentence": " ".join(parts), "modelIdentity": ident, "triggerCoverage": e67["triggerCoverage"],
            "inputStatus": items if province_code else None, "affordability": afford.get(names[0]) if province_code and names else None}
