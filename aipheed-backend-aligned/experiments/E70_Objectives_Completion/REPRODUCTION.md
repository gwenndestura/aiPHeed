# E70 clean-checkout reproduction

**Performed 2026-10-20 from two fresh `git archive` trees.** No working-copy file was used.

```bash
R=<empty scratch folder>
mkdir -p $R/lib $R/branch
# 1. pinned model library (origin/final-thesis-system)
git archive 089bdf2 aipheed-backend-aligned/experiments backend/data backend/config | tar -x -C $R/lib
# 2. this branch's E70 folder
git archive <E70 commit> aipheed-backend-aligned/experiments/E70_Objectives_Completion | tar -x -C $R/branch
# 3. the three parquet inputs that are untracked on final-thesis-system (copied into E70/inputs, sha256 below)
cp -r $R/branch/aipheed-backend-aligned/experiments/E70_Objectives_Completion/inputs/aipheed-backend-aligned/data $R/lib/aipheed-backend-aligned/
# 4. re-run (backend venv: LightGBM, joblib, pandas, pyarrow, scipy)
cd $R/branch/aipheed-backend-aligned/experiments/E70_Objectives_Completion
export AIPHEED_EXP=$R/lib/aipheed-backend-aligned/experiments
python -B runner/e70_predict.py main     --out $R/out --jobs 12
python -B runner/e70_predict.py ablation --out $R/out --jobs 12
sha256sum $R/out/*.csv        # compare with sealed/*.sha256
# optional, about 15 minutes (bootstrap): python -B runner/e70_score.py ; python -B runner/e70_leak.py
```

| File | Re-run sha256 (first 16) | Sealed sha256 (first 16) | Result |
|---|---|---|---|
| predictions.csv | b2175b72e5ea7b6b | b2175b72e5ea7b6b | identical |
| prospective.csv | 31f7304048826b9f | 31f7304048826b9f | identical |
| ablations.csv | 30c09f6214aba63e | 30c09f6214aba63e | identical |

The reference arm R0 reproduced the sealed E63 file (max |Δ| 5.0e-13, all 31 configurations equal).

**Untracked inputs copied into `inputs/`** (from `C:\Users\admin\aipheed\aipheed-backend-aligned\data\processed`, unchanged):
- `pagasa_climate.parquet` `4e198c73…`
- `bsp_macro.parquet` `233476fd…`
- `psa_rice_prices.parquet` `c1e3cecd…`

Every one of them is checked against the 2021+ window by the library before any row is loaded.

**Limit.** The re-run used the same Python environment (`C:\Users\admin\aipheed\backend\venv`, scikit-learn 1.8.0, LightGBM as installed). A different LightGBM version may differ in the last bits.
