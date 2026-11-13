# PROTOCOL_RR — ENNS 2021 recovery: candidates and per-round acceptance (written 2026-11-13 BEFORE the new candidate is computed)

## Root cause (established in ../aiPHeed_final_official_20261113/06 before this protocol)
2021 HIGH misses come from FINAL's elapsed-time term: anchors are refreshed to the latest released round, but the RATE term multiplies by the
province's OWN survey gap (24 quarters in 2021, beyond every training gap <= 20), so the decline is extrapolated and partly double-counted.
In 2021 four HIGH provinces (2015 level 65-73 %) fell 7-11 points while four LOW provinces with similar 2015 levels fell 18-34 points;
a candidate must separate these, not just shift every 2021 probability up.

## Candidates (each addresses the root cause; no setting chosen with 2021 outcomes)
C1 FINAL-ET    elapsed time := quarters since the latest released round (removes the double count). Stored L1-3 (protocol c5e76bd5).
C2 FINAL-SA    RATE multiplier capped at the longest training gap (no extrapolation). Stored L1-3 (PROTOCOL_SA 15202d27).
C3 FINAL-ETMIX p = (p_g + p_s)/2. Stored L1-8 (a365da1f).
C4 FINAL-CF    one-quarter carry-forward of local prices. Stored L1-8 (054239a1).
C5 STACK       NEW. Rolling-origin forecast combination p = w*FINAL + (1-w)*PERSISTENCE, the weight w (grid 0.00-1.00 by 0.01) minimising
               log loss on the out-of-sample forecasts of EARLIER rounds whose outcomes were released before the fold's origin
               (Bates & Granger 1969 style combination). 2018 and 2019 folds have no earlier released out-of-sample round, so w = 1
               (= FINAL); the 2021 fold learns w from the 2018 + 2019 fold forecasts at the same lead. Cut-off 0.50.
C6 STACK-ET    same as C5 with FINAL-ET in place of FINAL (Leads 1-3).

## Acceptance (brief §1/§6), evaluated once at Lead 1 (Lead 2 reported):
In EVERY round (2018, 2019, 2021): recall >= .70, F1 >= .70, precision >= .70, BA >= .70, Brier <= .20, accuracy >= .75, ROC-AUC >= .70,
PR-AUC > prevalence; AND 2018 and 2019 each not worse than FINAL on F1 and BA; AND pooled Brier better than persistence.
A candidate meeting all is reported as "retrospectively passes"; it still needs prospective confirmation (sealed forecasts) because the
72 outcomes were seen before. If none passes, FINAL stays and the limitation is reported.
