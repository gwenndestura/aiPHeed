# Owner decision: keep C-B6 as the served model (2026-11-04)

The owner answered "OKAY CB6 then", after reviewing these attempts:
- C-B6E (+ employment, OFW remittances);
- C-B6E-OPT (nested 32-setting search);
- T-B6 and T-B6E (stable 12-origin tuning, top-3 average);
- C-B6N and C-B6C (FI6-N archive news, CALABARZON news).

**Decision:**
- **Served model:** C-B6 (`backend/data/foodinsecurity_engine_cb6`), unchanged.
- **Inputs:** employment and OFW remittances stay outside the model. The dashboard shows them as "not used in this
  forecast".
- **Text:** the dashboard text fixes (5fc787a3) stay.

**Reasons** (see `DEEP_ANALYSIS.md`):
- C-B6 has the best accuracy, 0.806 at both leads.
- It is the only model passing R1–R7 at Leads 1–2.
- Every variant tested was lower on accuracy and failed R1–R7.

**Still required:**
- adviser approval;
- prospective confirmation from the 2027-01-01 seal.
