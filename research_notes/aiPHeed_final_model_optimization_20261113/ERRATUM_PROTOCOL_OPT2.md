# Erratum to PROTOCOL_OPT2 motivation text (2026-11-13, after LG was scored; the locked protocol file is unchanged)

PROTOCOL_OPT2 says DELTA's change inputs "were mostly missing (47-50 missing test values per fold)". That is wrong.
`evidence/DELTA_missingness.json` shows the 47-50 missing values are 2 of the 7 inputs, entirely empty (d_unemp_region, d_ag_pc:
no value at the anchor quarters). The poverty changes (d_p_poverty, d_p_subsistence, d_p_poverty_gap) and the regional-GRDP changes
(d_hh_grdp_rel, d_hh_grdp_g) are >= 95 % present in every fold. DELTA is therefore a VALID test of poverty and GRDP change since the
anchor survey, and it showed no 2021 gain (1/0/3/21, same as FINAL). The erratum does not affect LG, its checks, or its decision rule.
