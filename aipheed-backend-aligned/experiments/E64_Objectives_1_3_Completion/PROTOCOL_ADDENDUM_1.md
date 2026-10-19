# E64 protocol addendum 1 (implementation details fixed before any N3 feature or candidate score exists)

Written after PROTOCOL.md was frozen (sha 2a37c236…) and **before** `data/n3_features.csv` or any sealed candidate file existed. Nothing here depends on an outcome. All three points are faithful implementations of §4 "Equation 2 on admitted articles".

1. **FSSI-v3 bias weight.** The median article count is taken over the provinces with at least one admitted article that quarter, exactly as the deployed `app.ml.corpus.bias_weighter` does. It is not taken over all five provinces.

2. **No 0.30 intensity threshold in FSSI-v3.** Relevance is decided by classifier v2. FSSI-v3's n, status and value describe the same articles.
   - **Defect found (D-E64-2):** the deployed FSSI-v2 applies the 0.30 threshold inside `compute_fssi`, although its docstring says it does not. Its value uses 55 of 140 admitted articles, while its n and status use all 140.

3. **Intensity scores of the current classifier source only.** `app.news.scoring.current_model_key` now hashes the LF-normalised source.
   - **Defect found (D-E64-1):** a CRLF checkout of identical code had changed the key and orphaned the stored scores. After the fix, FSSI-v2 rebuilds byte-identically.
   - Scores written during E64 under the CRLF-derived key of the same source are accepted; scores of any other source are not.
