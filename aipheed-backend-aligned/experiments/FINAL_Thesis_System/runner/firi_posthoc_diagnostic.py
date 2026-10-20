"""POST-HOC diagnostic (not pre-registered, never used to change FIRI v1): how much of the FIRI HIGH rate comes from the
household-economy domain E, whose 2021-2023 anchors are the post-lockdown recovery (E1 P90 = -1.07 points, so ordinary
unemployment changes score 1). Recomputes FIRI from the stored domain scores with and without E on the Lead-2 rows.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/FINAL_Thesis_System/runner/firi_posthoc_diagnostic.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

OUT = Path(__file__).resolve().parents[1] / "out"
DOMS = ["dom_A", "dom_V", "dom_C", "dom_E", "dom_N", "dom_H"]


def firi(row, drop):
    v = [row[c] for c in DOMS if c not in drop and pd.notna(row[c])]
    return np.mean(v) if len(v) >= 4 else np.nan


def main():
    r = pd.read_csv(OUT / "firi_rows_all_leads.csv")
    r = r[r.lead == 2].copy()
    lines = ["POST-HOC diagnostic, Lead-2, label T43 (not pre-registered; FIRI v1 is unchanged)",
             f"rows {len(r)}; domain E mean {r.dom_E.mean():.3f}; E1 anchors P10/P90 = -2.65/-1.07 points"]
    for name, drop in [("FIRI v1 as frozen", []), ("FIRI without domain E", ["dom_E"])]:
        f = r.apply(lambda x: firi(x, drop), axis=1)
        ok = f.notna()
        yh, y = (f[ok] >= 0.5).astype(int), r.y[ok]
        lines.append(f"{name}: rows {ok.sum()}, accuracy {(yh == y).mean():.3f}, HIGH share {yh.mean():.3f}, "
                     f"AUC {roc_auc_score(y, f[ok]):.3f}, recall HIGH {((yh == 1) & (y == 1)).sum() / (y == 1).sum():.3f}, "
                     f"recall LOW {((yh == 0) & (y == 0)).sum() / (y == 0).sum():.3f}")
    assert np.allclose(r.apply(lambda x: firi(x, []), axis=1), r.FIRI, atol=1e-5)
    (OUT / "firi_posthoc_diagnostic.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
