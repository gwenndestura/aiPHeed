import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { GlossaryPanel } from "@/components/GlossaryPanel";

// BIAS_AUDIT: driver shares are relative model influence, not causes of food insecurity, and municipal values are a
// priority ranking. The glossary must not say otherwise.
describe("driver and risk wording", () => {
  it("describes SHAP shares as model influence, not percentages of food insecurity caused", () => {
    render(<GlossaryPanel open onClose={() => {}} />);
    const shap = screen.getByText(/splits one model prediction/);
    expect(shap.textContent).toContain("not the percentage of food insecurity caused by each factor");
    expect(shap.textContent).toContain("change from the province's latest survey level");
  });

  it("does not present municipal values as food-insecurity probabilities", () => {
    render(<GlossaryPanel open onClose={() => {}} />);
    const risk = screen.getByText(/shown as a percentage/);
    expect(risk.textContent).toContain("The food insecurity risk of a province");
    expect(risk.textContent).toContain("not a measured provincial rate");
    const towns = screen.getByText(/Towns and cities ranked by priority/);
    expect(towns.textContent).toContain("They are not separat");
    expect(towns.textContent).not.toMatch(/probability/i);
  });
});
