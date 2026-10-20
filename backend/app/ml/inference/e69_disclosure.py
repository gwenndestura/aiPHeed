"""
E69 (AIPHEED_LEAD2_MODEL=e69 only): the two-scale food-insecurity risk framework beside the unchanged Lead-2 score.

The score, colours and ranks are the E58 record's (E56-TUNED LightGBM, Lead-2), with every e68 layer. E69
(aipheed-backend-aligned/experiments/E69_Food_Insecurity_Risk_Framework) adds, from data/e69/e69_disclosure.json
built only from the E69 outputs (runner/r3_build_disclosure.py):
  * regionalHungerOutlook: the Lead-2 outlook of the one food-insecurity outcome measured every quarter (SWS hunger,
    Balance Luzon), its interval and its back-test (no method beat the latest reading);
  * riskOutlook: a transparent evidence-fusion tier per province (ELEVATED / WATCH / NO ELEVATED SIGNAL /
    INSUFFICIENT DATA) from the hunger outlook, affordability hazard, climate hazard and local production exposure;
  * vulnerabilityProfile: PSA subsistence and poverty with their sampling errors (context, not in the tier).
The tier is not a probability and not a validated provincial forecast; a LOW price score cannot hide it.
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
from pathlib import Path

from app.ml.inference import e68_disclosure as D68

DISCLOSURE = Path(os.getenv("AIPHEED_E69_DISCLOSURE", "data/e69/e69_disclosure.json"))
TIERS = ("ELEVATED", "WATCH", "NO ELEVATED SIGNAL", "INSUFFICIENT DATA")


class DisclosureError(RuntimeError):
    pass


@functools.lru_cache(maxsize=2)
def _load(path: str, mtime_ns: int) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    body = {k: v for k, v in d.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != d.get("content_sha256"):
        raise DisclosureError("E69 disclosure failed its integrity check")
    return d


def disclosure() -> dict | None:
    if not DISCLOSURE.exists():
        return None
    return _load(str(DISCLOSURE), DISCLOSURE.stat().st_mtime_ns)


def _reasons(c: dict) -> str:
    out = []
    if c["regionalHungerElevated"]:
        out.append(f"regional hunger is expected to stay above 11.3% ({c['probabilityHungerElevated']:.0%})")
    if c["affordabilityHazard"]:
        if c["pricePressureScore"] is not None and c["pricePressureScore"] >= 0.5:
            out.append(f"food-price pressure is likely ({c['pricePressureScore']:.0%})")
        else:
            out.append(f"headline inflation ({c['headlineAtIssue']:.1f}%) is above its usual 2021-2022 level "
                       f"({c['headlineUsual']:.1f}%)")
    if c["climateHazard"]:
        out.append("a PAGASA El Nino advisory is in force" + (
            " and local palay or corn production fell 10% or more" if c["localProductionExposure"] else ""))
    return "; ".join(out)


def for_summary(rec: dict, quarter: str, province_code: str | None, kind: str, result: str,
                cfsw: dict | None) -> dict | None:
    base = D68.for_summary(rec, quarter, province_code, kind, result, cfsw)
    d = disclosure()
    if base is None or d is None:
        return base
    ro = d["riskOutlook"].get(quarter)
    rh = d["regionalHungerOutlook"].get(quarter)
    if not ro or not rh:
        return base
    hunger = (f"Regional hunger outlook ({rh['geography']}): about {rh['expectedHunger']:.1f}% expected (80% range "
              f"{rh['interval80'][0]:.1f}-{rh['interval80'][1]:.1f}%), {rh['probabilityAbove11_3']:.0%} chance above 11.3%, from the "
              "latest reading (the score's own hunger part uses a different model and can give a different chance). "
              f"{rh['evaluation']}")
    if province_code:
        name = rec["provinces"][province_code]["name"]
        o = ro.get(name)
        if o is None:
            return base
        tier_text = (f"Food-insecurity risk outlook for {name}: {o['tier']}" +
                     (f", because {_reasons(o['components'])}." if o["tier"] in ("ELEVATED", "WATCH") else ".") +
                     (" A LOW food-price score above does not mean low food-insecurity risk." if result == "LOW" and
                      o["tier"] in ("ELEVATED", "WATCH") else "") +
                     " This outlook is an evidence summary, not a probability and not a validated provincial forecast.")
        outlook = {"tier": o["tier"], "issueDate": o["issueDate"], "components": o["components"],
                   "rule": d["tierRule"], "framework": d["framework"]}
        vul = {"province": name, **d["vulnerabilityProfile"][name], "note": d["vulnerabilityNote"]}
    else:
        counts = {t: [n for n, o in ro.items() if o["tier"] == t] for t in TIERS}
        tier_text = ("Food-insecurity risk outlook: " + "; ".join(f"{t} in {', '.join(v)}" for t, v in counts.items() if v)
                     + ". An evidence summary, not a probability and not a validated provincial forecast.")
        outlook = {"tiers": {n: o["tier"] for n, o in ro.items()}, "rule": d["tierRule"], "framework": d["framework"]}
        vul = None
    sentence = f"{tier_text} {hunger} {base['sentence']} {d['provinceSkill']} {d['goalStatus']}"
    ident = {**base["modelIdentity"], "servingMode": "e69"}
    return {**base, "sentence": sentence, "modelIdentity": ident, "riskOutlook": outlook,
            "regionalHungerOutlook": {k: rh[k] for k in rh if k != "evaluation"} | {"evaluation": rh["evaluation"]},
            "vulnerabilityProfile": vul}
