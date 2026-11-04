# Proposal (NOT implemented): showing rice stocks if C-E6 is ever served

**Status:** proposal only. The dashboard, API and the 8081 demo are unchanged, and C-E2 is still served.

## The problem

C-E6 adds two inputs (ST1, ST2), which carry about 8% of mean |SHAP|. They are food **availability**, not prices,
climate, fisheries, employment or remittances.
- Folding them into Market/Prices would misstate that group.
- Dropping them from the explanation would hide 8% of the model's push.

## Backward-compatible option (recommended if adopted)

**API:**
- Keep the five groups and their order unchanged in `/api/v1/explainability`.
- Add an **optional** sixth entry with `key: "supply"`, `label: "Rice supply"`, and the same fields (percent, direction,
  status, evidence).
- Old clients ignore unknown keys; the current frontend maps only known keys.

**Backend:**
- `foodinsecurity_system.SHOWN_GROUPS` gains `"supply"` only when the served `evaluation.json` lists it in a new
  `extra_driver_groups` field. C-b and C-E2 exports do not, so their output is byte-identical.

**Shares:** computed over six groups when the sixth is present. In the relative view, the sixth group's usual push is
its own mean |SHAP|, like the others.

**Frontend:** one more row in the existing risk-driver card, using the existing row component and colours. No layout
change. This is a frontend change, so it needs separate approval.

**Tests:**
- The five-group output is unchanged for C-b and C-E2.
- With C-E6, the six shares sum to 100 and each sign equals the SHAP sign.

## Alternative

Keep the five rows. Add one sentence under the card: "Rice supply (national stocks) contributes X% and is not shown
as a bar." This needs only a text change, but it hides the contribution from the chart.
