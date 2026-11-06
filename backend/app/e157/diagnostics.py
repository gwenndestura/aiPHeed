"""E157 diagnostics: anchor bias by round and survey age, and news categories dropped one at a time (Lead 1, rows read before). Run: python -m app.e157.diagnostics"""
import json, numpy as np, pandas as pd
from joblib import Parallel, delayed
from app.e151 import OUT as O51
from app.e151 import prov as Pv
from app.e156.audit import setup
F=pd.read_csv(O51/"prov_oof.csv"); x=F[F.lead==1].copy()
pct=lambda v:100/(1+np.exp(-v))
out={"anchor_bias":{}}
for a in ("ANCHOR","GNT","PERS"):
    e=pct(x[f"mu_{a}"])-pct(x.y_true)
    out["anchor_bias"][a]={"mean_error_points":round(float(e.mean()),2),"by_round":e.groupby(x.survey).mean().round(2).to_dict(),"by_gap_quarters":e.groupby(x.gap_q).mean().round(2).to_dict(),"slope":round(float(np.polyfit(x[f"mu_{a}"],x.y_true,1)[0]),2)}
G={"market":"_e_market","climate":"_e_climate","employment":"_e_employment","remittance":"_e_remittance","poverty":"_e_poverty","response":"_e_response","hunger_net":("_e_hunger","_e_net","_net_since","_intensity"),"topics":"_tp_","province_sentences":"_tg_"}
def drop(c,pat):
    pats=pat if isinstance(pat,tuple) else (pat,)
    return [v for v in c if not (v in Pv.NEWS_ALL and any(p in v for p in pats))]
def run(survey):
    S,P,tr,te,base=setup(survey); r=te[["key","survey"]].copy()
    for name,cols in [("full",Pv.GNT_COLS),("no_news",[c for c in Pv.GNT_COLS if c not in Pv.NEWS_ALL])]+[("drop_"+k,drop(Pv.GNT_COLS,p)) for k,p in G.items()]:
        m=Pv.Res2(cols).fit(tr); mu=base+m.predict(te); sd,_,_=m.scale(te.gap_q.values); r[name]=1/(1+np.exp(-0))*0+__import__("scipy.stats",fromlist=["norm"]).norm.cdf(mu/sd)
    return r
R=pd.concat(Parallel(n_jobs=3)(delayed(run)(s) for s in ("ENNS2018","ENNS2019","ENNS2021"))).merge(x[["key","survey","y_high","q_true"]],on=["key","survey"])
out["news_categories"]={c:{"correct":int(((R[c]>=.5)==(R.y_high==1)).sum()),"brier_soft":round(float(np.mean((R[c]-R.q_true)**2)),4)} for c in R.columns if c not in ("key","survey","y_high","q_true")}
json.dump(out,open("data/e156/out/e157_diagnostics.json","w"),indent=1)
print(json.dumps(out,indent=0))
