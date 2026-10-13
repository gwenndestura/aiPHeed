# E11 Protocol: Post-Run Record (deviations and notes)

`E11_PROTOCOL.md` is unchanged since the run. The SHA-256 recorded in the run manifest is `878b8b4d708f18fcaa399967dfd4280b86757952ff95fed2674f5d181312df81`, and the current file hash is `878b8b4d708f18fcaa399967dfd4280b86757952ff95fed2674f5d181312df81` (identical).

## Deviations

**None in procedure.** The run (`runs/20261012T145620Z`) followed every prespecified step:

- 48 arm/window outputs;
- the frame equalled E9's;
- two identical prediction passes;
- predictions sealed before the outcomes were revealed;
- no guard denial (loky core counting avoided with `LOKY_MAX_CPU_COUNT=21`).

## Notes found during analysis (not deviations)

1. **Thin inner validation.** Nested selection had 1–8 inner quarters per expanding fold and only 1 per rolling fold.
2. **Floating-point ties.** The S1 rule equals carry-forward in 6 of 7 quarters, up to floating-point rounding. The automated "quarters better" count therefore reads 2/7 where the true count is 1/7. `RESULTS_SUMMARY.md` reports 1/7 with 6 ties.
3. **Sequencing.** The sealed 2026-Q4 forecast (E10, issued 2026-10-12 14:51:50 UTC) was produced **before** E11 began. E11 results could not influence it.
