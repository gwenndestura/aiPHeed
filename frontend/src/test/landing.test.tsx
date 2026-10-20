import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/components/TopNavbar", () => ({ TopNavbar: () => <header>header</header> }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ status: "anonymous" }) }));
vi.mock("@/lib/tour", () => ({ requestTour: vi.fn() }));

// The hero reads the forecast quarter from /api/v1/config; each test sets what the API returns.
const config = vi.hoisted(() => ({
  state: { data: undefined as unknown, isError: false },
}));
vi.mock("@/lib/queries", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/queries")>()),
  useConfig: () => config.state,
}));
const SERVED = { quarterRange: { forecastTarget: { target_quarter: "2027-Q1" } } };

import Landing from "@/pages/Landing";
import { AboutModal } from "@/components/AboutModal";

// The footer's feedback form submits through react-query.
const renderLanding = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    </QueryClientProvider>,
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
  it("has the sections in order, each with a left-aligned sentence-case heading and the amber dot", () => {
    const { container } = renderLanding();
    const sections = [...container.querySelectorAll("main section")];
    expect(sections.map((s) => s.id)).toEqual(["about", "methodology", "accuracy", "disclaimer", "faq"]);
    for (const sec of sections) {
      const h2 = sec.querySelector("h2") as HTMLElement;
      expect(h2.querySelector(".heading-dot")).not.toBeNull();
      expect(h2.className).not.toMatch(/text-center|uppercase/);
    }
    expect(sections.map((s) => s.querySelector("h2")?.textContent)).toEqual([
      "About aiPHeed",
      "Methodology",
      "How accurate it is",
      "Data disclaimer and limitations",
      "Frequently asked questions",
    ]);
  });

  it("hero: the title, subtitle, two buttons and the coverage pills in a floating card", () => {
    config.state = { data: SERVED, isError: false };
    const { container } = renderLanding();
    const card = container.querySelector("[data-hero-card]") as HTMLElement;
    expect(card.className).toContain("surface-float");
    expect(within(card).getByRole("heading", { level: 1 }).textContent).toBe(
      "Food Insecurity Risk Forecasting System for CALABARZON",
    );
    const sub = within(card).getByText(/^A geospatial system/);
    expect(sub.textContent).toBe(
      "A geospatial system that estimates the food insecurity risk of the five CALABARZON provinces two quarters ahead, using public statistics and Filipino-English news.",
    );
    expect(sub.className).not.toContain("italic");
    expect(within(card).getByRole("link", { name: /Explore the map/ }).getAttribute("href")).toBe("/dashboard");
    expect(within(card).getByRole("link", { name: "How it works" }).getAttribute("href")).toBe("#methodology");
    const pills = within(card).getAllByRole("listitem").map((li) => li.textContent);
    expect(pills).toEqual(["5 provinces", "142 cities and municipalities", "Forecast for Q1 2027"]);
    // Nothing else in the card: no label above the title, no other text.
    expect(card.textContent).toBe(
      "Food Insecurity Risk Forecasting System for CALABARZON" + sub.textContent +
        "Explore the mapHow it works5 provinces142 cities and municipalitiesForecast for Q1 2027",
    );
    // The tint over the photo: the dark background into amber and risk red.
    const tint = container.querySelector("[data-hero-tint]") as HTMLElement;
    expect(tint.className).toMatch(/linear-gradient.*--primary.*--risk-high/);
    expect(container.querySelector("section")?.textContent).toContain("Photo by Atom Araullo on GMA News");
  });

  it("hero: hides the forecast pill when the API fails or has no forecast quarter", () => {
    config.state = { data: undefined, isError: true };
    const { container, unmount } = renderLanding();
    let pills = [...(container.querySelector("[data-hero-card]") as HTMLElement).querySelectorAll("li")].map((li) => li.textContent);
    expect(pills).toEqual(["5 provinces", "142 cities and municipalities"]);
    unmount();
    config.state = { data: { quarterRange: {} }, isError: false };
    const second = renderLanding();
    pills = [...(second.container.querySelector("[data-hero-card]") as HTMLElement).querySelectorAll("li")].map((li) => li.textContent);
    expect(pills).toEqual(["5 provinces", "142 cities and municipalities"]);
    config.state = { data: SERVED, isError: false };
  });

  it("shows the five methodology steps as numbered cards in a grid", () => {
    const { container } = renderLanding();
    const steps = container.querySelector("#methodology ol") as HTMLElement;
    expect(steps.className).toMatch(/grid/);
    expect(steps.className).toMatch(/lg:grid-cols-3/);
    const cards = [...steps.querySelectorAll(":scope > li")];
    expect(cards).toHaveLength(5);
    expect(cards.every((c) => c.className.includes("inner-card") && (c.textContent ?? "").trim().length > 40)).toBe(true);
    expect(cards.map((c) => c.querySelector("h4")?.textContent)).toEqual([
      "11. Indicator scores",
      "22. Six domains",
      "33. Combining the domains",
      "44. Classification",
      "55. City and municipal ranking",
    ]);
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

  it("has no research email and no [CONFIRM] placeholder", () => {
    const { container } = renderLanding();
    expect(container.innerHTML).not.toContain("aipheed.research@dlsud.edu.ph");
    expect(container.textContent).not.toContain("[CONFIRM");
  });

  it("lists the researchers in one order, in the footer's Contact column", () => {
    const { container } = renderLanding();
    const text = container.textContent ?? "";
    expect(text).toContain("Destura, Princess Gwenn A.; Esico, Christina M.; and Melindo, Angel Vhea P.");
    const contact = screen.getByRole("heading", { name: "Contact" }).parentElement as HTMLElement;
    const team = [...contact.querySelectorAll("a[href*='linkedin']")].map((a) => a.textContent);
    expect(team).toEqual(["Destura", "Esico", "Melindo"]);
    expect(container.querySelectorAll("footer a[href*='linkedin']")).toHaveLength(3);
    expect(within(contact).getByRole("link", { name: /Department of Agriculture Regional Field Office IV-A/ })).toBeTruthy();
  });

  it("opens the site's feedback form from the footer", () => {
    renderLanding();
    const contact = screen.getByRole("heading", { name: "Contact" }).parentElement as HTMLElement;
    fireEvent.click(within(contact).getByRole("button", { name: /Send Feedback/i }));
    expect(screen.getByRole("dialog", { name: "aiPHeed System Usability Feedback" })).toBeTruthy();
  });

  it("footer: gradient background, no credits paragraph, no 'Developed by' line, copyright kept", () => {
    const { container } = renderLanding();
    const footer = container.querySelector("footer") as HTMLElement;
    expect(footer.className).toMatch(/bg-\[linear-gradient\(135deg,hsl\(var\(--background\)\).*--primary.*--risk-high/);
    expect(footer.textContent).not.toContain("Credits:");
    expect(footer.textContent).not.toContain("Developed by");
    expect(footer.textContent).toContain("© 2026 aiPHeed. All rights reserved.");
    // The hero keeps its own photo credit.
    expect(container.querySelector("section")?.textContent).toContain("Photo by Atom Araullo on GMA News");
  });

  it("shows the LightGBM lead-time table exactly as in the report, with Lead 2 marked as the map's", () => {
    const { container } = renderLanding();
    const table = container.querySelector("#accuracy table") as HTMLTableElement;
    const rows = [...table.querySelectorAll("tbody tr")].map((tr) =>
      [...tr.querySelectorAll("td")].slice(0, 5).map((td) => td.textContent),
    );
    expect(rows).toEqual([
      ["0.85", "0.83", "0.71", "0.77", "0.90"],
      ["0.72", "0.63", "0.56", "0.59", "0.65"],
      ["0.62", "0.40", "0.43", "0.41", "0.62"],
    ]);
    const heads = [...table.querySelectorAll("tbody th")].map((th) => th.textContent);
    expect(heads[0]).toBe("One quarter ahead (Lead 1)");
    expect(heads[1]).toBe("Two quarters ahead (Lead 2)The forecast shown on the map");
    expect(heads[2]).toBe("Three quarters ahead (Lead 3)");
    expect(table.textContent).toContain("60 province-quarters, 12 quarters");
    expect(table.textContent).toContain("50 province-quarters, 10 quarters");
    expect(table.textContent).toContain("45 province-quarters, 9 quarters");
    const acc = container.querySelector("#accuracy")?.textContent ?? "";
    expect(acc).toContain("Accuracy falls the further ahead the forecast looks; the map forecasts two quarters ahead.");
    expect(acc).toContain("All results below are development evidence");
    expect(acc).toContain("The 75% accuracy goal");
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
