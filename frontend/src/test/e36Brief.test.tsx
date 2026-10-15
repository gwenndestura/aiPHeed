import { existsSync, readFileSync } from "fs";
import path from "path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { E36BriefView } from "@/pages/E36Brief";
import { NewsEvidenceView } from "@/pages/NewsEvidence";
import { E36Record, PROVINCE_ORDER } from "@/lib/e31Record";
import { RISK_BADGE_TEXT } from "@/components/ui/status-badge";

const file = path.resolve(__dirname, "../../public/e36_record.json");
const rec = (existsSync(file) ? JSON.parse(readFileSync(file, "utf-8")) : null) as E36Record | null;

describe.skipIf(!rec)("E36 DA brief", () => {
  it("labels the one-quarter-ahead forecast with its origin, cutoff and previous-quarter news window", () => {
    render(<E36BriefView rec={rec!} />);
    const fc = rec!.quarters.find((q) => q.mode === "FORECAST")!;
    expect(screen.getByTestId("mode-FORECAST").textContent).toContain(`${fc.quarter}: Forecast`);
    expect(screen.getByTestId("mode-FORECAST").textContent).toContain(fc.origin);
    expect(screen.getByTestId("window-FORECAST").textContent).toContain("2026-Q3 articles");
    expect(screen.getByTestId("model").textContent).toContain("LightGBM");
  });

  it("shows each province's forecast with its SHAP drivers and calls the band an estimate", () => {
    render(<E36BriefView rec={rec!} />);
    PROVINCE_ORDER.forEach((c) => {
      const e = rec!.provinces_now[c].forecast;
      const box = screen.getByTestId(`fc-${c}`);
      expect(box.textContent).toContain(`${Math.round(e.p_high * 100)}%`);
      expect(box.textContent).toContain("model estimate, not validated");
      expect(screen.getByTestId(`fc-${c}-driver-${e.drivers![0].key}`)).toBeTruthy();
      expect(screen.getByTestId(`why-${c}`).textContent).toContain(rec!.provinces_now[c].province);
    });
  });

  it("reports all six Chapter I baselines with exact counts and the honest 75% verdict", () => {
    render(<E36BriefView rec={rec!} />);
    ["E36-LGBM", "B1_PERSISTENCE", "B2_LR_COMB", "B3_LR_GOV", "B4_LR_NLP", "B5_LGBM_GOV", "B6_LGBM_NLP", "ALWAYS_HIGH"]
      .forEach((k) => expect(screen.getByTestId(`row-${k}`)).toBeTruthy());
    const m = rec!.validation.model_evaluation.rows.find((r) => r.key === "E36-LGBM")!;
    expect(screen.getByTestId("row-E36-LGBM").textContent).toContain(`${m.correct}/${m.n}`);
    expect(screen.getByTestId("threshold-verdict").textContent).toContain("not demonstrated");
    expect(screen.getByTestId("threshold-verdict").textContent).toContain("Always-HIGH");
    expect(screen.getByTestId("disclaimer").textContent).toContain("not official");
  });

  it("news evidence page works on the served record", () => {
    render(<NewsEvidenceView rec={rec!} />);
    expect(screen.getByTestId("n-fssi")).toBeTruthy();
  });
});

describe("risk band wording (E35-D1)", () => {
  it("never says a bare High risk / Low risk", () => {
    expect(RISK_BADGE_TEXT.high).toBe("Estimated high");
    expect(RISK_BADGE_TEXT.low).toBe("Estimated low");
  });
});
