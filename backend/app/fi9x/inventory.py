"""Traceable dataset inventory (source, measurement, geography, frequency, periods, availability, size, method,
missingness, intended use, limitations), built from the manifests, the FI9 vintage table and the news archive.

    python -m app.fi9x.inventory        # writes docs/fi9x/DATA_INVENTORY.csv
"""
from __future__ import annotations

import pandas as pd

from app.fi9x import DOCS
from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
ROLE = {"sws": ("target (quarterly outcome)", "Balance Luzon, not CALABARZON; sawtooth; pre-2021 MOE assumed and release dates rule-based"),
        "cpi": ("predictor (market)", "current vintage; Region IV-A"), "palay": ("predictor (market)", "Region IV-A; current vintage"),
        "lfs": ("predictor (employment)", "national, not regional"), "nasa": ("predictor (climate)", "mean of 5 province centroids"),
        "tc": ("predictor (climate)", "regional exposure count; not province-specific"), "oni": ("predictor (climate)", "global index"),
        "remit": ("predictor (remittances)", "national, annual"), "poverty": ("predictor/context (poverty)", "triennial; 2015->2018 methodology break"),
        "gdelt": ("predictor (news, FI5)", "national news intensity; 2017+")}
DESC = {"sws": ("SWS media releases", "involuntary hunger, % families", "survey (1 item, past 3 months)"),
        "cpi": ("PSA OpenSTAT", "food / rice / all-items CPI y/y", "price index"), "palay": ("PSA OpenSTAT", "palay production y/y", "administrative"),
        "lfs": ("PSA LFS", "unemployment rate", "survey"), "nasa": ("NASA POWER", "rainfall, max temperature", "reanalysis/satellite"),
        "tc": ("IBTrACS", "storm passages", "tracks"), "oni": ("NOAA CPC", "ENSO index", "index"),
        "remit": ("BSP via World Bank WDI", "OFW cash remittances y/y", "administrative"), "poverty": ("PSA", "poverty incidence", "survey (FIES income)"),
        "gdelt": ("GDELT", "theme intensity", "text-derived")}


def build() -> pd.DataFrame:
    v = pd.read_csv(D / "fi9" / "out" / "data_vintage_long.csv")
    rows = []
    for (src, ind), g in v.groupby(["source_key", "indicator"]):
        role, lim = ROLE.get(src, ("predictor", ""))
        s, meas, meth = DESC.get(src, ("", "", ""))
        rows.append({"dataset": f"{src}:{ind}", "source": s, "measurement": meas, "geographic_coverage": g["geographic_level"].iloc[0],
                     "frequency": "quarterly" if src == "sws" else ("monthly" if src in ("cpi", "lfs", "nasa", "oni") else "event/annual/quarterly"),
                     "reference_period": f"{g['period_end'].min()} .. {g['period_end'].max()}",
                     "publication_rule": g["revision_status"].iloc[0], "first_available": g["available_from"].min(), "last_available": g["available_from"].max(),
                     "n_values": len(g), "method": meth, "missingness": "gaps by publication only (no fill)", "intended_use": role,
                     "limitations": lim, "file": "backend/data/fi5/raw (see MANIFEST.csv)"})
    m = pd.read_csv(D / "fi_labels" / "raw" / "MANIFEST.csv")
    for _, r in m.iterrows():
        rows.append({"dataset": f"label:{r['file']}", "source": r["source_url"], "measurement": r["content"], "geographic_coverage": "see content",
                     "frequency": "cross-sectional", "reference_period": str(r.get("survey_year", "")), "publication_rule": r["status"],
                     "first_available": "", "last_available": "", "n_values": "", "method": "survey estimate / document",
                     "missingness": "", "intended_use": "label: target validation / external validation / benchmark (never a quarterly target)",
                     "limitations": "HFIAS, FIES and SWS hunger are different instruments; ENNS provincial values unverified",
                     "file": f"backend/data/fi_labels/raw/{r['file']}" if r["status"] == "acquired" else "not acquired"})
    for f, meas in [("articles.parquet", "news articles (WordPress archives; 95% Rappler)"), ("events.parquet", "deduplicated food-security events with XLM-R aspect scores")]:
        x = pd.read_parquet(D / "fi6" / "news_archive" / f, columns=["published"])
        rows.append({"dataset": f"news:{f}", "source": "FI6-N publisher archives", "measurement": meas, "geographic_coverage": "Philippine news; CALABARZON tagging",
                     "frequency": "daily", "reference_period": f"{x['published'].min().date()} .. {x['published'].max().date()}", "publication_rule": "publication timestamp",
                     "first_available": str(x["published"].min().date()), "last_available": str(x["published"].max().date()), "n_values": len(x),
                     "method": "text-derived (XLM-R zero-shot, BERTopic in FI5)", "missingness": "sparse before 2012; NaN when < 30 articles in a window",
                     "intended_use": "predictor (news inside the five domains)", "limitations": "single-publisher dominance; media attention varies", "file": f"backend/data/fi6/news_archive/{f}"})
    out = pd.DataFrame(rows)
    out.to_csv(DOCS / "DATA_INVENTORY.csv", index=False, lineterminator="\n")
    return out


if __name__ == "__main__":
    print(len(build()), "datasets inventoried")
