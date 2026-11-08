# LightGBM feature ablation report (E168, Lead 1)

**Method:** the frozen selected configuration, refitted on training rows without each group, then scored out of sample. The difference is E168 − variant: **negative means the group helps.**

| Group | Brier without | Difference [95 %] | Accuracy without | Verdict |
|---|---|---|---|---|
| **Market and prices** | 0.1304 | **−0.0073 [−0.0154, −0.0001]** | 69.4 % | **Contributes** (the only significant group) |
| Climate stress | 0.1274 | −0.0044 [−0.0111, +0.0014] | 72.2 % | Possible; not significant |
| Employment | 0.1227 | +0.0003 [−0.0004, +0.0011] | 77.8 % | None (national-only data) |
| OFW remittances | 0.1230 | +0.0001 [−0.0002, +0.0003] | 76.4 % | None (national-only data) |
| Poverty & social vulnerability (incl. general news, SWS) | 0.1223 | +0.0008 [−0.0128, +0.0125] | 79.2 % | None demonstrated |

**All trigger inputs shuffled across provinces (3 seeds):** −0.0003 [−0.015, +0.018]. **No advantage of real over shuffled inputs.**

**Reading the two together:**
- **Removing market inputs hurts, but shuffling them across provinces does not.**
- Market prices carry **time-level information** (when food prices rise), not province-specific information.
- Employment and remittances cannot help until **provincial** LFS and remittance data exist.
- **News columns** sit inside the groups; the 2018/2019 origins chose GOV, which excludes news. **No out-of-sample news contribution is shown.**
