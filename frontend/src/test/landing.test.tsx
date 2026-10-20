import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("@/components/TopNavbar", () => ({ TopNavbar: () => <header>header</header> }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ status: "anonymous" }) }));
vi.mock("@/lib/tour", () => ({ requestTour: vi.fn() }));

import Landing from "@/pages/Landing";
import { AboutModal } from "@/components/AboutModal";

const renderLanding = () =>
  render(
    <MemoryRouter>
      <Landing />
    </MemoryRouter>,
  );

const openAbout = () => {
  render(
    <MemoryRouter>
      <AboutModal />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByText("About & Methodology"));
  return screen.getByRole("dialog");
};

describe("Landing page", () => {
  it("has the DOST-style sections in order, each with a heading", () => {
    const { container } = renderLanding();
    const ids = [...container.querySelectorAll("main section")].map((s) => s.id);
    expect(ids).toEqual(["about", "methodology", "accuracy", "disclaimer", "faq"]);
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Estimated food-insecurity risk for CALABARZON");
    expect(screen.getByRole("link", { name: /Explore the map/ }).getAttribute("href")).toBe("/dashboard");
  });

  it("drops the tagline, stats row, live estimate card and capability grid", () => {
    const { container } = renderLanding();
    const text = container.textContent ?? "";
    for (const gone of [
      "Mapped.",
      "LOWER RISK",
      "Cities and municipalities",
      "CALABARZON regional estimate",
      "What moved the current regional estimate",
      "What the system shows",
    ]) {
      expect(text).not.toContain(gone);
    }
  });

  it("uses no serif font anywhere", () => {
    const { container } = renderLanding();
    const styled = [...container.querySelectorAll<HTMLElement>("[style]")].map((e) => e.getAttribute("style") ?? "");
    expect(styled.some((s) => /Georgia|serif/i.test(s))).toBe(false);
  });

  it("says forecasts are public unless rejected, and rejected ones are withheld", () => {
    const { container } = renderLanding();
    const text = container.textContent ?? "";
    expect(text).not.toMatch(/Review before publication|before it appears on the public map|reviewed before/);
    expect(text).toContain("Every province estimate is shown publicly unless an authorized administrator rejects it.");
    fireEvent.click(screen.getByRole("button", { name: "How often is it updated?" }));
    expect(screen.getByText(/a rejected province-quarter is withheld and shown as withheld/)).toBeTruthy();
  });

  it("describes the system without 'ensemble machine learning'", () => {
    const { container } = renderLanding();
    expect(container.textContent).not.toMatch(/ensemble/i);
    expect(container.textContent).toContain("It uses the FIRI v2 risk index, with a LightGBM food-price-pressure forecast as one input");
  });

  it("shows the research email only as an unlinked [CONFIRM] placeholder", () => {
    const { container } = renderLanding();
    expect(container.innerHTML).not.toContain("aipheed.research@dlsud.edu.ph");
    const placeholder = screen.getByText("[CONFIRM: research team email]");
    expect(placeholder.closest("a")).toBeNull();
  });

  it("lists the researchers in one order", () => {
    const { container } = renderLanding();
    const text = container.textContent ?? "";
    expect(text).toContain("Destura, Princess Gwenn A.; Esico, Christina M.; and Melindo, Angel Vhea P.");
    const team = [...container.querySelectorAll("footer a[href*='linkedin']")].map((a) => a.textContent);
    expect(team).toEqual(["Destura", "Esico", "Melindo"]);
  });

  it("states both quarter counts in the small-sample limitation", () => {
    renderLanding();
    expect(screen.getByText(/9 to 12 quarters of evidence for each lead time/).textContent).toContain("17 quarters");
  });

  it("opens one FAQ row at a time, with aria-expanded", () => {
    renderLanding();
    const q = screen.getByRole("button", { name: "What is aiPHeed?" });
    expect(q.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(q);
    expect(q.getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: "How far ahead does it forecast?" }));
    expect(q.getAttribute("aria-expanded")).toBe("false");
  });
});

describe("About dialog", () => {
  it("labels the performance row as the price input and words the lead time plainly", () => {
    const dlg = openAbout();
    expect(dlg.textContent).toContain("Price input (LightGBM, Lead-2)");
    expect(dlg.textContent).toContain("accuracy 0.72 · F1 0.59 · AUC 0.65");
    expect(dlg.textContent).toContain("Two quarters ahead. No forecast horizon has yet met the reliability test.");
  });

  it("drops the research email and shows an unlinked placeholder", () => {
    const dlg = openAbout();
    expect(dlg.innerHTML).not.toContain("aipheed.research@dlsud.edu.ph");
    expect(screen.getByText(/\[CONFIRM: research team email\]/).closest("a")).toBeNull();
  });
});
