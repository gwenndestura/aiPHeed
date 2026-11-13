"""List the inputs FINAL actually selects in the official live fits (leads 1-2, 5 seeds) and the rank of every candidate."""
import json, os, sys
from pathlib import Path
import pandas as pd
PREV = Path(r"C:\Users\admin\aipheed_final\research_notes\aiPHeed_final_dashboard_preview_20261113")
os.environ.setdefault("PREVIEW_CAND", str(PREV / "out_final" / "cand_panel.parquet"))
sys.path.insert(0, str(PREV / "scripts"))
from app.hcw import engine as H
LOG = []
orig = H.Model._select
def sel(self, d):
    k = self.ckey + (self.prune, self.tag)
    hit = k in self.cache
    use = orig(self, d)
    if not hit:
        pool = [c for c in self.cols if c in d and d[c].notna().any() and d[c].nunique() > 1]
        r = d[pool].rank().corrwith(d["e"].rank()).abs().fillna(0.0).sort_values(ascending=False)
        LOG.append({"cols_pool": list(self.cols), "valid": pool, "rank": r.round(4).to_dict(), "use": list(use), "n": len(d)})
    return use
H.Model._select = sel
import build_corrected as BC
out = []
for lead in (1, 2):
    for seed in BC.SEEDS:
        LOG.clear()
        r = BC._one(lead, seed)
        final = r["cols"]
        # the selection log entry that produced the final columns (full training set)
        ent = [e for e in LOG if e["use"] == list(final)]
        out.append({"lead": lead, "seed": seed, "cols": final, "rank": ent[-1]["rank"] if ent else None,
                    "pool": ent[-1]["cols_pool"] if ent else None, "valid": ent[-1]["valid"] if ent else None, "n": ent[-1]["n"] if ent else None})
        print(lead, seed, len(final), flush=True); Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
