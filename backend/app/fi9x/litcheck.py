"""Verify every reference of the fusion literature review against Crossref (title, venue, year).

    python -m app.fi9x.litcheck         # writes data/fi9x/out/literature_crossref.json
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

from app.fi9x import OUT

DOIS = {
    "kalamara2022": "10.1002/jae.2907", "barbaglia2023": "10.1080/07350015.2022.2060988",
    "teles2025": "10.1016/j.inffus.2025.102981", "zhao2024_multimodal": "10.1145/3649447",
    "hewamalage2023": "10.1007/s10618-022-00894-5", "cerqueira2020": "10.1007/s10994-020-05910-7",
    "baker2016_epu": "10.1093/qje/qjw024", "thorsrud2020": "10.1080/07350015.2018.1506344",
    "larsen2019": "10.1016/j.jeconom.2018.11.013", "shapiro2022": "10.1016/j.jeconom.2020.07.053",
    "bates_granger1969": "10.1057/jors.1969.103", "wolpert1992": "10.1016/S0893-6080(05)80023-1",
    "zou_hastie2005": "10.1111/j.1467-9868.2005.00503.x", "tibshirani1996": "10.1111/j.2517-6161.1996.tb02080.x",
    "gneiting_raftery2007": "10.1198/016214506000001437", "niculescu2005": "10.1145/1102351.1102430",
    "diebold_mariano1995": "10.1080/07350015.1995.10524599", "gama2014": "10.1145/2523813",
    "fay_herriot1979": "10.1080/01621459.1979.10482505", "he_garcia2009": "10.1109/TKDE.2008.239",
    "barber2023_conformal": "10.1214/23-AOS2276", "tashman2000": "10.1016/S0169-2070(00)00065-0",
    "cafiero2018_fies": "10.1016/j.measurement.2017.10.065", "brier1950": "10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2",
    "rao_molina2015_sae": "10.1002/9781118735855", "conneau2020_xlmr": "10.18653/v1/2020.acl-main.747",
}


def check() -> dict:
    out = {}
    for key, doi in DOIS.items():
        url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
        req = urllib.request.Request(url, headers={"User-Agent": "aiPHeed-thesis-litcheck/1.0 (mailto:none)"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                m = json.loads(r.read())["message"]
            out[key] = {"doi": doi, "found": True, "title": (m.get("title") or [""])[0],
                        "venue": (m.get("container-title") or [""])[0] or m.get("publisher", ""),
                        "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
                        "authors": [a.get("family", "") for a in m.get("author", [])][:4]}
        except Exception as exc:                       # noqa: BLE001
            out[key] = {"doi": doi, "found": False, "error": str(exc)[:120]}
        time.sleep(0.3)
    (OUT / "literature_crossref.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    r = check()
    for k, v in r.items():
        print(k, "OK" if v["found"] else "MISSING", v.get("year"), (v.get("title") or v.get("error"))[:90])
