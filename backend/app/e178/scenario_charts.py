"""
E178 Part A charts for docs/e178/SCENARIO_TEST_REPORT.md, drawn from data/e178/synthetic/ only. Every figure carries the
label SYNTHETIC – FOR DEMONSTRATION.

    python -m app.e178.scenarios charts   -> docs/e178/img/*.png
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.e178 import common as K  # noqa: E402

IMG = K.DOCS / "img"
PROV = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
PCOL = {"Batangas": "#2563eb", "Cavite": "#f59e0b", "Laguna": "#059669", "Quezon": "#dc2626", "Rizal": "#7c3aed"}
GROUP_LABEL = {"weather_farm": "Weather and farm", "food_prices": "Food prices", "jobs": "Jobs", "remittances": "Remittances",
               "fish_catch": "Fish catch"}
BAR_LABEL = {"market": "Market / prices", "climate": "Climate", "employment": "Employment", "ofw_remittance": "OFW remittance",
             "fish_kill": "Fish catch", "poverty": "Poverty / density"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 110})


def _label(fig, title: str, real: bool = False) -> None:
    fig.text(0.5, 0.995, K.LABEL if not real else f"{K.LABEL} (report)  ·  this chart: real inputs", ha="center", va="top",
             fontsize=9, fontweight="bold", color="black", bbox=dict(boxstyle="square,pad=0.3", fc="#fbbf24", ec="none"))
    fig.suptitle(title, y=0.945, fontsize=11, fontweight="bold")


def _save(fig, name: str) -> None:
    IMG.mkdir(parents=True, exist_ok=True)
    fig.savefig(IMG / name, bbox_inches="tight")
    plt.close(fig)


def s0(o: pd.DataFrame) -> None:
    d = o[(o.scenario_id == "S0") & (o.lead == 1)].set_index("province").loc[PROV]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    x = np.arange(len(PROV))
    ax[0].bar(x, d.score_pct, color=[PCOL[p] for p in PROV], alpha=.85)
    ax[0].errorbar(x, d.score_pct, yerr=[d.score_pct - d.range90_low, d.range90_high - d.score_pct], fmt="none", ecolor="black", capsize=4)
    ax[0].axhline(50, color="#dc2626", ls="--", lw=1)
    ax[0].set(xticks=x, xticklabels=PROV, ylabel="Households moderately or severely food insecure (%)", title="Forecast share with 90 % range")
    ax[1].bar(x, d.probability, color=[PCOL[p] for p in PROV], alpha=.85)
    ax[1].axhline(.5, color="#dc2626", ls="--", lw=1)
    ax[1].set(xticks=x, xticklabels=PROV, ylim=(0, 1), ylabel="P(HIGH)", title="Probability of HIGH (line = 0.50)")
    _label(fig, "S0 · Baseline, real latest inputs (Lead 1, 2027-Q1) = the production numbers", real=True)
    _save(fig, "s0_baseline.png")


def s1(o: pd.DataFrame) -> None:
    s0_ = o[(o.scenario_id == "S0") & (o.lead == 1)].set_index("province")
    d = o[(o.scenario_id == "S1") & (o.lead == 1) & (o.group != "noise")]
    fig, axes = plt.subplots(1, 5, figsize=(13, 3.2), sharey=True)
    for ax, g in zip(axes, GROUP_LABEL):
        for p in PROV:
            k = d[(d.group == g) & (d.province == p)].assign(param=lambda z: z.param.astype(float)).sort_values("param")
            xs = [-2, -1, 0, 1, 2]
            ys = list(k[k.param < 0].p_high_exact) + [s0_.at[p, "p_high_exact"]] + list(k[k.param > 0].p_high_exact)
            ax.plot(xs, ys, marker="o", ms=3, color=PCOL[p], label=p)
        ax.axhline(.5, color="#dc2626", ls="--", lw=1)
        ax.set(title=GROUP_LABEL[g], xticks=[-2, -1, 0, 1, 2], xlabel="SD moved (+ = stress)")
    axes[0].set_ylabel("P(HIGH), Lead 1")
    axes[-1].legend(fontsize=7, loc="upper left")
    _label(fig, "S1 · Sensitivity: one trigger group moved by ±1 or ±2 standard deviations")
    _save(fig, "s1_sensitivity.png")
    n = o[(o.scenario_id == "S1") & (o.group == "noise") & (o.lead == 1)]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.boxplot([n[n.province == p].p_high_exact for p in PROV], labels=PROV, showfliers=True)
    ax.scatter(range(1, 6), [s0_.at[p, "p_high_exact"] for p in PROV], marker="D", color="black", zorder=3, label="real inputs")
    ax.axhline(.5, color="#dc2626", ls="--", lw=1)
    ax.set(ylabel="P(HIGH), Lead 1", title="100 draws of random ±1 SD noise on all five groups at once")
    ax.legend(fontsize=7)
    _label(fig, "S1 · Spread under joint noise")
    _save(fig, "s1_noise.png")


def s2(o: pd.DataFrame) -> None:
    s0_ = o[(o.scenario_id == "S0") & (o.lead == 1)].set_index("province")
    d = o[(o.scenario_id == "S2") & (o.lead == 1)]
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.6))
    w = 0.22
    for j, f in enumerate([0.25, 0.5, 0.75]):
        m = d[(d.group == "mask") & (d.param.astype(float) == f)]
        ax[0].boxplot([m[m.province == p].p_high_exact for p in PROV], positions=np.arange(5) + (j - 1) * w, widths=w * .9,
                      showfliers=False, patch_artist=True, boxprops=dict(facecolor=["#bfdbfe", "#93c5fd", "#3b82f6"][j]))
    ax[0].scatter(np.arange(5), [s0_.at[p, "p_high_exact"] for p in PROV], marker="D", color="black", zorder=3, label="real inputs")
    am = d[d.group == "all_missing"].set_index("province")
    ax[0].scatter(np.arange(5) + .38, [am.at[p, "p_high_exact"] for p in PROV], marker="x", color="#dc2626", zorder=3, label="all triggers missing")
    ax[0].set(xticks=np.arange(5), xticklabels=PROV, ylabel="P(HIGH), Lead 1", title="25 % / 50 % / 75 % of trigger inputs missing (20 masks each)")
    ax[0].legend(fontsize=7)
    lm = d[d.group == "latest_missing"].set_index("province")
    mk = d[d.group == "mask"].groupby("province").range90_width_pts.mean()
    x = np.arange(5)
    ax[1].bar(x - .27, [s0_.at[p, "range90_width_pts"] for p in PROV], .27, label="real inputs", color="#111827")
    ax[1].bar(x, [mk[p] for p in PROV], .27, label="inputs missing (mean)", color="#3b82f6")
    ax[1].bar(x + .27, [lm.at[p, "range90_width_pts"] for p in PROV], .27, label="latest survey (ENNS 2021) missing", color="#f59e0b")
    ax[1].set(xticks=x, xticklabels=PROV, ylabel="Width of the 90 % range (points)", title="Uncertainty: what widens the 90 % range")
    ax[1].legend(fontsize=7)
    _label(fig, "S2 · Limited data")
    _save(fig, "s2_limited_data.png")


def s3(o: pd.DataFrame, meta: dict) -> None:
    d = o[(o.scenario_id == "S3") & (o.lead == 1)]
    mx = d.groupby(["group", "param"]).p_high_exact.max().reset_index()
    fig, ax = plt.subplots(figsize=(8.5, 4))
    for i, (s, lab) in enumerate((k, v["label"]) for k, v in meta["shocks"].items()):
        z = mx[mx.group == s].assign(param=lambda q: q.param.astype(float)).sort_values("param")
        z = pd.concat([pd.DataFrame({"param": [0.0], "p_high_exact": [o[(o.scenario_id == "S0") & (o.lead == 1)].p_high_exact.max()]}), z])
        ax.plot(z.param, z.p_high_exact, marker="o", ms=3, lw=3 if s == "combined" else 1.5, label=lab)
    ax.axhline(.5, color="#dc2626", ls="--", lw=1)
    ax.axvspan(1.0, 1.55, color="#e5e7eb", alpha=.6, label="extrapolated beyond history")
    ax.set(xlabel="Shock intensity t (0 = today, 1 = worst value in the historical data)", ylabel="Highest P(HIGH) of the 5 provinces, Lead 1",
           ylim=(0, 1), xlim=(0, 1.55))
    ax.legend(fontsize=7, loc="upper left")
    fh = meta["s3_first_high"]
    _label(fig, f"S3 · High-risk shock. First HIGH: {fh['province']} under {fh['variant']}" + (" (S3-B)" if meta["s3b_used"] else ""))
    _save(fig, "s3_shock.png")
    b = o[(o.scenario_id == "S3-B") & (o.lead == 1)]
    if len(b):
        bm = b.groupby("param").p_high_exact.max()
        fig, ax = plt.subplots(figsize=(7, 3.2))
        ax.plot(bm.index.astype(float), bm.values, marker="o")
        ax.axhline(.5, color="#dc2626", ls="--", lw=1)
        ax.set(xlabel="Survey baseline raised by (logit), on top of the combined shock at t = 1", ylabel="Highest P(HIGH)")
        _label(fig, "S3-B · Combined shock plus a hypothetical worse survey baseline")
        _save(fig, "s3b_baseline.png")


def s4(o: pd.DataFrame, s4d: dict) -> None:
    d = o[o.variant == s4d["source_variant"]]
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.6), gridspec_kw={"width_ratios": [1.2, 1]})
    x = np.arange(5)
    for j, l in enumerate((1, 2, 3)):
        z = d[d.lead == l].set_index("province")
        ax[0].bar(x + (j - 1) * .27, [z.at[p, "p_high_exact"] for p in PROV], .27, label=f"Lead {l} ({z.quarter.iloc[0]})",
                  color=["#dc2626", "#f87171", "#fecaca"][j])
    ax[0].axhline(.5, color="black", ls="--", lw=1)
    ax[0].set(xticks=x, xticklabels=PROV, ylim=(0, 1), ylabel="P(HIGH)", title=f"Scenario {s4d['source_variant']}")
    ax[0].legend(fontsize=7)
    if s4d["explanations"]:
        e = s4d["explanations"][0]
        ds = sorted(e["drivers"], key=lambda r: r["group_shap"])
        ax[1].barh([r["driver_label"] for r in ds], [r["group_shap"] for r in ds],
                   color=["#dc2626" if r["group_shap"] > 0 else "#2563eb" for r in ds])
        ax[1].axvline(0, color="black", lw=.8)
        ax[1].set(title=f"Why {e['province']} is HIGH in {e['quarter']}: trigger contributions", xlabel="SHAP (log-odds of the change)")
    _label(fig, "S4 · High-risk response: the province turns HIGH, alerts and explanations follow")
    _save(fig, "s4_response.png")


def s5(m: pd.DataFrame) -> None:
    if m.empty:
        return
    keys = list(dict.fromkeys(zip(m.province, m.quarter)))[:3]
    fig, axes = plt.subplots(1, len(keys), figsize=(5.5 * len(keys), 3.8), squeeze=False)
    for ax, (p, q) in zip(axes[0], keys):
        z = m[(m.province == p) & (m.quarter == q)].sort_values("risk_index")
        ax.barh(z.municipality, z.risk_index, color="#dc2626")
        ax.set(title=f"{p}, {q}: highest-ranked cities and municipalities", xlabel="Risk index (province P(HIGH) re-weighted)")
    _label(fig, "S5 · Municipal sample: reweighted provincial estimates, not municipal forecasts")
    _save(fig, "s5_municipal.png")


def main() -> None:
    o = pd.read_csv(K.SYN / "scenarios_outputs.csv")
    summ = json.loads((K.SYN / "scenarios_summary.json").read_text(encoding="utf-8"))
    s4d = json.loads((K.SYN / "s4_response.json").read_text(encoding="utf-8"))
    m = pd.read_csv(K.SYN / "s5_municipal.csv")
    s0(o)
    s1(o)
    s2(o)
    s3(o, summ["meta"])
    s4(o, s4d)
    s5(m)
    print(sorted(p.name for p in IMG.glob("*.png")))
