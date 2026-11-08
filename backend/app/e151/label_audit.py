"""
E151 audit of the survey percentages behind HIGH and LOW: which are clearly above or below 50 given their margin of error, and which move between rounds by more than noise.

    python -m app.e151.label_audit -> data/e151/out/label_audit.json, label_audit_rows.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.e147 import features as Fe
from app.e147 import labels as Lb
from app.e151 import OUT
from app.paths import BACKEND_DIR

CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
DATA = BACKEND_DIR / "data"


def rows() -> pd.DataFrame:
    Fe.LT = 0.0
    b = Fe.base_rows()[["key", "province", "region", "survey", "year", "p", "se_p"]].copy()
    k = b.drop_duplicates("key").set_index("key")
    L = pd.read_csv(Lb.SEALED)
    w = L.pivot_table(index="key", columns="fs_survey_category", values="pct").reset_index()
    w = w[w["key"].isin(k.index)]
    e = pd.DataFrame({"key": w["key"], "province": w["key"].map(k["province"]), "region": w["key"].map(k["region"]), "survey": "ENNS2021", "year": 2021, "p": w["Food Insecure Households"], "se_p": 3.0})
    a = pd.concat([b, e], ignore_index=True)
    a["low90"], a["high90"] = a["p"] - 1.645 * a["se_p"], a["p"] + 1.645 * a["se_p"]
    a["cls"] = np.where(a["p"] >= 50, "HIGH", "LOW")
    a["certainty"] = np.select([a["low90"] >= 50, a["high90"] < 50], ["clearly HIGH", "clearly LOW"], "too close to call")
    # moderate plus severe where the source gives categories
    h = pd.read_csv(DATA / "hfias" / "clean" / "enns_hfias.csv")
    h["key"] = h["area"].str.lower()
    h["modsev"] = h["moderate_pct"] + h["severe_pct"]
    h["survey"] = "ENNS" + h["year"].astype(str)
    a = a.merge(h[["key", "survey", "modsev"]], on=["key", "survey"], how="left")
    w["survey"] = "ENNS2021"
    w["modsev2"] = w["Moderately Food Insecure Households"] + w["Severely Food Insecure Households"]
    a = a.merge(w[["key", "survey", "modsev2"]], on=["key", "survey"], how="left")
    a["modsev"] = a["modsev"].fillna(a["modsev2"])
    return a.drop(columns=["modsev2"]).sort_values(["key", "year"]).reset_index(drop=True)


def main():
    a = rows()
    a.round(2).to_csv(OUT / "label_audit_rows.csv", index=False, lineterminator="\n")
    res = {"by_round": {}}
    for s, g in a.groupby("survey", sort=False):
        res["by_round"][s] = {"n": int(len(g)), "mean": float(g["p"].mean()), "median": float(g["p"].median()), "min": float(g["p"].min()), "max": float(g["p"].max()), "share_high": float((g["p"] >= 50).mean()), "n_low": int((g["p"] < 50).sum()), "clearly_high": int((g["certainty"] == "clearly HIGH").sum()), "clearly_low": int((g["certainty"] == "clearly LOW").sum()), "too_close": int((g["certainty"] == "too close to call").sum()), "mean_se": float(g["se_p"].mean()), "n_modsev": int(g["modsev"].notna().sum()), "mean_modsev": float(g["modsev"].mean()) if g["modsev"].notna().any() else None, "share_modsev_ge50": float((g["modsev"].dropna() >= 50).mean()) if g["modsev"].notna().any() else None}
    res["pooled"] = {"n": int(len(a)), "n_low": int((a["p"] < 50).sum()), "share_high": float((a["p"] >= 50).mean()), "clearly_low": int((a["certainty"] == "clearly LOW").sum()), "too_close": int((a["certainty"] == "too close to call").sum())}
    # round-to-round moves
    m = []
    for k, g in a.groupby("key"):
        g = g.sort_values("year")
        for j in range(1, len(g)):
            d = g["p"].iloc[j] - g["p"].iloc[j - 1]
            se = float(np.hypot(g["se_p"].iloc[j], g["se_p"].iloc[j - 1]))
            m.append({"province": g["province"].iloc[0], "from": g["survey"].iloc[j - 1], "to": g["survey"].iloc[j], "gap_y": int(g["year"].iloc[j] - g["year"].iloc[j - 1]), "d": d, "se": se, "real_move": bool(abs(d) > 1.645 * se), "flip": bool((g["p"].iloc[j] >= 50) != (g["p"].iloc[j - 1] >= 50))})
    M = pd.DataFrame(m)
    res["moves"] = {f"{a_}>{b_}": {"n": int(len(g)), "mean_change": float(g["d"].mean()), "mean_abs_change": float(g["d"].abs().mean()), "share_beyond_noise": float(g["real_move"].mean()), "flips": int(g["flip"].sum()), "flips_high_to_low": int(((g["flip"]) & (g["d"] < 0)).sum()), "flips_low_to_high": int(((g["flip"]) & (g["d"] > 0)).sum())} for (a_, b_), g in M.groupby(["from", "to"], sort=False)}
    res["moves"]["all"] = {"n": int(len(M)), "mean_abs_change": float(M["d"].abs().mean()), "share_beyond_noise": float(M["real_move"].mean()), "flips": int(M["flip"].sum())}
    res["calabarzon"] = a[a["province"].isin(CAL)][["province", "survey", "p", "se_p", "low90", "high90", "cls", "certainty", "modsev"]].round(1).to_dict(orient="records")
    res["lowest_rows"] = a.sort_values("p").head(15)[["province", "survey", "p", "se_p", "certainty"]].round(1).to_dict(orient="records")
    res["near_50"] = a[(a["p"] >= 45) & (a["p"] < 55)][["province", "survey", "p", "se_p", "certainty"]].round(1).sort_values("p").to_dict(orient="records")
    res["always_low_or_mostly"] = a.groupby("province")["p"].agg(["size", "min", "max", "mean"]).assign(n_low=a.assign(l=a["p"] < 50).groupby("province")["l"].sum()).query("n_low >= 2").round(1).reset_index().to_dict(orient="records")
    res["never_low_share"] = float((a.groupby("province")["p"].min() >= 50).mean())
    (OUT / "label_audit.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps({k: res[k] for k in ("by_round", "pooled", "moves", "calabarzon", "lowest_rows", "near_50", "always_low_or_mostly", "never_low_share")}, default=float))


if __name__ == "__main__":
    main()
