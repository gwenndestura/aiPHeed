"""E169 feasibility: FIES -> HFIAS (moderate+severe) bridge from the 2019 ENNS provincial factsheets that report both
on the same households. Fits nothing on forecast errors. Checks the bridge on national values from other years.

    python -m app.e169.fies_bridge -> data/e169/out/fies_bridge_feasibility.json
"""
import json

import numpy as np
import pandas as pd

from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
lg = lambda p: np.log(np.asarray(p, float) / (100 - np.asarray(p, float)))
ex = lambda z: 100 / (1 + np.exp(-z))


def main():
    d = pd.read_csv(D / "hfias" / "clean" / "enns_hfias.csv")
    b = d[d.fies_mod_sev_pct.notna() & d.mod_sev_pct.notna()].reset_index(drop=True)
    h, f = b.mod_sev_pct.values, b.fies_mod_sev_pct.values
    s, i = np.polyfit(lg(f), lg(h), 1)
    res = lg(h) - (i + s * lg(f))
    rng = np.random.default_rng(169)
    bs = []
    for _ in range(4000):
        k = rng.integers(0, len(b), len(b))
        bs.append(np.polyfit(lg(f[k]), lg(h[k]), 1))
    bs = np.array(bs)
    br = lambda x: float(ex(i + s * lg(x)))
    br_ci = lambda x: [round(float(v), 1) for v in np.percentile(ex(bs[:, 1] + bs[:, 0] * lg(x)), [2.5, 97.5])]
    fies = pd.read_csv(D / "fi_labels" / "clean" / "published_fies_psa_sdg212.csv")
    nat = fies[fies.level == "national"].set_index("year")["percent"]
    iva = float(fies[(fies.level == "region") & (fies.geography == "Region IV-A") & (fies.year == 2023)]["percent"].iloc[0])
    out = {
        "pairs": {"n": len(b), "year": 2019, "source": "FNRI ENNS 2019 provincial factsheets (same households, both scales)", "areas": b.area.tolist()},
        "bridge_logit": {"intercept": round(float(i), 3), "slope": round(float(s), 3), "slope_ci95": [round(float(v), 2) for v in np.percentile(bs[:, 0], [2.5, 97.5])],
                         "residual_sd_logit": round(float(res.std(ddof=2)), 3), "corr_pct": round(float(np.corrcoef(h, f)[0, 1]), 3),
                         "mean_hfias_minus_fies_pts": round(float((h - f).mean()), 2), "province_HIGH_agreement": round(float(((h >= 50) == (ex(i + s * lg(f)) >= 50)).mean()), 2)},
        "checks_on_national_values": {
            "2019_in_sample": {"fies": float(nat[2019]), "bridged_hfias": round(br(nat[2019]), 1), "published_hfias_national": float(d[d.year == 2019].ph_mod_sev_pct.dropna().iloc[0])},
            "2021_out_of_year": {"fies": float(nat[2021]), "bridged_hfias": round(br(nat[2021]), 1), "bridged_ci95": br_ci(nat[2021]),
                                 "mean_hfias_25_test_provinces_unweighted": 41.6, "note": "no national HFIAS 2021 printed; provincial mean is unweighted, so only a rough check"}},
        "use_2023": {"calabarzon_fies_2023": iva, "bridged_hfias_2023": round(br(iva), 1), "bridged_ci95": br_ci(iva),
                     "national_fies_2023": float(nat[2023]), "national_bridged_hfias_2023": round(br(nat[2023]), 1)},
    }
    p = D / "e169" / "out" / "fies_bridge_feasibility.json"
    p.write_text(json.dumps(out, indent=1), newline="\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
