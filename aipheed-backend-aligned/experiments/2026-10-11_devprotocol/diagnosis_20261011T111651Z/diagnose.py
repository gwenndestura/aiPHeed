import warnings; warnings.filterwarnings("ignore")
import json, numpy as np, pandas as pd
from scipy.stats import spearmanr
import scripts.supplementary.devprotocol_rule_l as D
import scripts.supplementary.window2021_study as W
RUN="experiments/2026-10-11_devprotocol/runs/20261011T111651Z/"
OUT="experiments/2026-10-11_devprotocol/diagnosis_20261011T111651Z/"
import os; os.makedirs(OUT, exist_ok=False)
cfg=json.load(open(RUN+"config.json"))
names={"PH040100000":"Cavite","PH040200000":"Laguna","PH040300000":"Quezon","PH040400000":"Rizal","PH040500000":"Batangas"}
lab=W.window_labels(14.345); lab=lab[lab.quarter<="2025-Q4"][["quarter","province_code","stress_score"]]
# 1. decomposition: quarter mean vs within-quarter deviation
lab["q_mean"]=lab.groupby("quarter").stress_score.transform("mean"); lab["dev"]=lab.stress_score-lab.q_mean
tot=lab.stress_score.var(ddof=0); between=lab.q_mean.var(ddof=0); within=lab.dev.var(ddof=0)
sws=pd.read_parquet("data/processed/labels.parquet")
cols=[c for c in sws.columns if "sws" in c.lower()]
print("label cols with sws:", cols)
print(f"variance: total {tot:.2f}, between-quarter {between:.2f} ({between/tot:.0%}), within-quarter {within:.2f} ({within/tot:.0%})")
qs=lab.groupby("quarter").agg(q_mean=("stress_score","mean"),dev_sd=("dev","std"),dev_maxabs=("dev",lambda s: s.abs().max()),
     high_global=("stress_score",lambda s:int((s>14.345).sum())))
qs["mixed_global"]=qs.high_global.between(1,4)
print("quarters mixed at 14.345:", int(qs.mixed_global.sum()), "of", len(qs)); print(qs.round(2).to_string())
qs.round(3).to_csv(OUT+"quarter_decomposition.csv")
# 2. test quarters: tau_T vs regional level vs SWS input at origin
f,usable=D.development_frame()
r=pd.read_csv(RUN+"scored_rows.csv")
b=r[(r.group=="primary")&(r.sensitivity=="base")]
rows=[]
for a in ["A-origin","A-global"]:
    x=b[b.analysis==a]
    for q,g in x.groupby("target_quarter"):
        tau=g.tau.iloc[0]; te=f[f.target_quarter==q]
        rows.append({"analysis":a,"quarter":q,"tau":round(tau,2),"regional_mean_stress":round(qs.loc[q,"q_mean"],2),
          "level_minus_tau":round(qs.loc[q,"q_mean"]-tau,2),"max_abs_prov_dev":round(qs.loc[q,"dev_maxabs"],2),
          "sws_input_at_origin":te.sws_hunger.iloc[0],"sws_input_round":te.sws_round.iloc[0],
          "test_high":int(g[g.model=="MODEL-B2"].y.sum()),
          "B2_pred_high":int(g[g.model=="MODEL-B2"].pred.sum()),"B2_mean_p":round(g[g.model=="MODEL-B2"].p.mean(),3),
          "A_pred_high":int(g[g.model=="MODEL-A"].pred.sum()),"A_mean_p":round(g[g.model=="MODEL-A"].p.mean(),3),
          "Eq3_pred_high":int(g[g.model=="Eq3-rule"].pred.sum()),"CF_pred_high":int(g[g.model=="carry-forward"].pred.sum())})
tq=pd.DataFrame(rows); print(tq.to_string()); tq.to_csv(OUT+"test_quarter_level.csv",index=False)
# 3. missingness of B2 inputs: test rows vs training rows
B2=cfg["feature_sets"]["base"]["MODEL-B2"]; A=cfg["feature_sets"]["base"]["MODEL-A"]
miss=[]
for q in cfg["test_primary"]:
    te=f[f.target_quarter==q]; tr=f[f.target_quarter.isin(cfg["eligible_training_quarters"][q])]
    miss.append({"quarter":q,"B2_test_nan_share":round(te[B2].isna().mean().mean(),3),"B2_train_nan_share":round(tr[B2].isna().mean().mean(),3),
       "A_test_nan_share":round(te[A].isna().mean().mean(),3),"A_train_nan_share":round(tr[A].isna().mean().mean(),3),
       "B2_cols_all_nan_in_test":int(te[B2].isna().all().sum()),"B2_cols_all_nan_in_train":int(tr[B2].isna().all().sum())})
mm=pd.DataFrame(miss); print(mm.to_string()); mm.to_csv(OUT+"missingness.csv",index=False)
# 4. within-quarter discrimination: Spearman between score and actual stress across 5 provinces
L=lab.set_index(["quarter","province_code"]).stress_score
wq=[]
for a in ["A-origin"]:
    x=b[b.analysis==a]
    for (q,m),g in x.groupby(["target_quarter","model"]):
        if m.startswith("always"): continue
        s=L.loc[q].reindex(g.province_code).values
        rho=spearmanr(g.p.values,s).correlation if np.nanstd(g.p.values)>0 else np.nan
        wq.append({"quarter":q,"model":m,"rho_score_vs_stress":rho})
w=pd.DataFrame(wq).pivot(index="quarter",columns="model",values="rho_score_vs_stress").round(2)
print(w.to_string()); print("mean rho:", w.mean().round(2).to_dict()); w.to_csv(OUT+"within_quarter_spearman.csv")
# 5. errors by province and quarter, primary B2
e=b[(b.analysis=="A-origin")&(b.model.isin(["MODEL-B2","MODEL-A","Eq3-rule","carry-forward"]))].copy()
e["err"]=(e.y!=e.pred).astype(int); e["province"]=e.province_code.map(names)
pt=e.pivot_table(index=["province"],columns=["model"],values="err",aggfunc="sum"); print(pt.to_string())
eq=e[e.model=="MODEL-B2"].pivot_table(index="province",columns="target_quarter",values="err",aggfunc="sum"); print(eq.to_string())
e.to_csv(OUT+"errors_primary.csv",index=False)
# 6. label persistence: how often does a province's label equal its last published label (training-period, global threshold)
lab["y_g"]=(lab.stress_score>14.345).astype(int); qq=sorted(lab.quarter.unique())
same=[(lab[lab.quarter==qq[i]].set_index("province_code").y_g==lab[lab.quarter==qq[i-1]].set_index("province_code").y_g).mean() for i in range(1,len(qq))]
print("consecutive-labelled-quarter label agreement (14.345):", round(float(np.mean(same)),3))
# quarter mean stress vs SWS input relation over all quarters
fq=f.groupby("target_quarter").sws_hunger.first()
j=qs.join(fq.rename("sws_input"),how="inner")
print("corr(regional level, SWS input at origin):", round(j.q_mean.corr(j.sws_input),3), "n=",len(j))
print("corr(level change, input change):", round(j.q_mean.diff().corr(j.sws_input.diff()),3))
