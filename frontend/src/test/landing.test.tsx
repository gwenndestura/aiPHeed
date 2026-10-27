import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/components/TopNavbar", () => ({ TopNavbar: () => <header>header</header> }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ status: "anonymous" }) }));
vi.mock("@/lib/tour", () => ({ requestTour: vi.fn() }));

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import Landing from "@/pages/Landing";
import { AboutModal } from "@/components/AboutModal";

// Every figure the page states about the served forecast (FINAL_SYSTEM_SELECTION/runner/landing_figures.py).
const FIGURES = JSON.parse(
  readFileSync(
    resolve(__dirname, "../../../aipheed-backend-aligned/experiments/FINAL_SYSTEM_SELECTION/out/landing_figures.json"),
    "utf-8",
  ),
);

// The footer's feedback form submits through react-query.
const renderLanding = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    </QueryClientProvider>,
  );

// The dialog reads the final engine (latest SWS survey, model evaluation) through react-query.
const openAbout = () => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <AboutModal />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByText("About & Methodology"));
  return screen.getByRole("dialog");
};

describe("Landing page", () => {
  it("has the sections in order, each with a centred heading in bold spaced capitals and no dot", () => {
    const { container } = renderLanding();
    const sections = [...container.querySelectorAll("main section")];
    expect(sections.map((s) => s.id)).toEqual(["about", "methodology", "accuracy", "disclaimer", "faq"]);
    for (const sec of sections) {
      const h2 = sec.querySelector("h2") as HTMLElement;
      expect(h2.className).toMatch(/text-center/);
      expect(h2.className).toMatch(/font-bold/);
      expect(h2.className).toMatch(/uppercase/);
      expect(h2.className).toMatch(/tracking-\[0\.14em\]/);
    }
    expect(container.querySelector(".heading-dot")).toBeNull();
    expect(sections.map((s) => s.querySelector("h2")?.textContent)).toEqual([
      "About aiPHeed",
      "Methodology",
      "How accurate it is",
      "Data disclaimer and limitations",
      "Frequently asked questions",
    ]);
  });

  it("hero: the title, subtitle and two buttons, directly on the photo, with no pills", () => {
    const { container } = renderLanding();
    expect(container.querySelector("[data-hero-card]")).toBeNull();
    const hero = container.querySelector("section") as HTMLElement;
    expect(hero.querySelector(".surface-float, .surface-card")).toBeNull();
    const card = container.querySelector("[data-hero-text]") as HTMLElement;
    expect(card.className).toContain("text-left");
    expect(within(card).getByRole("heading", { level: 1 }).textContent).toBe(
      "Food Insecurity Risk Forecasting System for Region IV-A",
    );
    const sub = within(card).getByText(/^A geospatial system/);
    expect(sub.textContent).toBe(
      "A geospatial system that estimates the food insecurity risk of the five CALABARZON provinces.",
    );
    expect(sub.className).not.toContain("italic");
    expect(within(card).getByRole("link", { name: /Explore the map/ }).getAttribute("href")).toBe("/dashboard");
    expect(within(card).getByRole("link", { name: "How it works" }).getAttribute("href")).toBe("#methodology");
    // No pills, no label above the title, no other text.
    expect(card.querySelector("ul, li, .qt-pill")).toBeNull();
    expect(card.textContent).toBe(
      "Food Insecurity Risk Forecasting System for Region IV-A" + sub.textContent + "Explore the mapHow it works",
    );
    // The tint over the photo: the dark background into amber and risk red.
    const tint = container.querySelector("[data-hero-tint]") as HTMLElement;
    expect(tint.className).toMatch(/linear-gradient.*--primary.*--risk-high/);
    expect(container.querySelector("section")?.textContent).toContain("Photo by Atom Araullo on GMA News");
  });

  it("shows the five methodology steps as numbered paragraphs, not cards", () => {
    const { container } = renderLanding();
    expect(container.querySelector("#methodology ol")).toBeNull();
    expect(container.querySelector("#methodology .inner-card")).toBeNull();
    const titles = [...container.querySelectorAll("#methodology h4")].map((h) => h.textContent);
    expect(titles.slice(0, 5)).toEqual([
      "1.What High risk means",
      "2.Hunger condition",
      "3.Food-price condition",
      "4.Classification",
      "5.City and municipal ranking",
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
    expect(container.textContent).toContain(
      "It combines a regional hunger outlook from SWS with a LightGBM food-price forecast on 12 indicator families",
    );
  });

  it("words the lead time one way: three months ahead, never two quarters or Lead-2", () => {
    const { container } = renderLanding();
    const text = container.textContent ?? "";
    expect(text).not.toMatch(/two quarters|two-quarter|Lead-2|\(Lead 2\)/i);
    expect(text).toContain("one for the quarter just starting and one for the next quarter, three months ahead");
    fireEvent.click(screen.getByRole("button", { name: "How far ahead does it forecast?" }));
    expect(
      screen.getByText(/^Forecasts are issued on the first day of each quarter.*the forecast three months ahead, for the next quarter, is experimental\.$/),
    ).toBeTruthy();
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

  it("shows the served forecast's lead-time table exactly as in landing_figures.json, with Lead 1 marked reliable", () => {
    const { container } = renderLanding();
    const table = container.querySelector("#accuracy table") as HTMLTableElement;
    const rows = [...table.querySelectorAll("tbody tr")].map((tr) =>
      [...tr.querySelectorAll("td")].slice(0, 5).map((td) => td.textContent),
    );
    const f2 = (v: number) => v.toFixed(2);
    expect(rows).toEqual(
      ["1", "2", "3"].map((k) => {
        const l = FIGURES.leads[k];
        return [f2(l.accuracy), f2(l.precision), f2(l.recall), f2(l.f1), f2(l.auc)];
      }),
    );
    const heads = [...table.querySelectorAll("tbody th")].map((th) => th.textContent);
    expect(heads[0]).toBe("Lead 1: current quarterPassed the reliability test");
    expect(heads[1]).toBe("Lead 2: three months ahead (experimental)");
    expect(heads[2]).toBe("Lead 3: six months ahead");
    for (const k of ["1", "2", "3"]) {
      const l = FIGURES.leads[k];
      expect(table.textContent).toContain(`${l.rows} province-quarters, ${l.quarters} quarters`);
    }
    expect(FIGURES.leads["1"].reliable).toBe(true);
    expect(FIGURES.leads["2"].reliable).toBe(false);
    const acc = container.querySelector("#accuracy")?.textContent ?? "";
    expect(acc).toContain("the next quarter is labelled experimental");
    expect(acc).toContain("All results below are development evidence");
    expect(acc).toContain("The 75% accuracy goal");
    expect(acc).toContain("SHA-256 " + FIGURES.seal);
  });

  it("shows the Lead-1 Brier comparison exactly as in landing_figures.json", () => {
    const { container } = renderLanding();
    const tables = [...container.querySelectorAll("#accuracy table")];
    const brier = tables[tables.length - 1];
    const cells = [...brier.querySelectorAll("tr")].map((tr) => [
      tr.querySelector("th")?.textContent,
      tr.querySelector("td")?.textContent,
    ]);
    const m = FIGURES.lead1_brier.models;
    expect(cells).toEqual([
      ["LightGBM (served forecast)", m["LightGBM (served, P0H4)"].brier.toFixed(3)],
      ["Naive persistence", m["I. Naive persistence"].brier.toFixed(3)],
      ["Logistic regression, combined", m["Logistic regression, combined"].brier.toFixed(3)],
      ["Logistic regression, government data only", m["Logistic regression, government data only"].brier.toFixed(3)],
      ["Logistic regression, news only", m["Logistic regression, news only"].brier.toFixed(3)],
      ["LightGBM, government data only", m["LightGBM, government data only"].brier.toFixed(3)],
      ["LightGBM, news only", m["LightGBM, news only"].brier.toFixed(3)],
    ]);
    // the note's claims follow the Holm-corrected tests
    expect(m["I. Naive persistence"].established).toBe(false);
    expect(m["LightGBM, government data only"].p0h4_minus).toBeGreaterThan(0);
    for (const k of [
      "Logistic regression, combined",
      "Logistic regression, government data only",
      "Logistic regression, news only",
      "LightGBM, news only",
    ])
      expect(m[k].established).toBe(true);
    expect(container.querySelector("#accuracy")?.textContent).toContain(
      `Same ${FIGURES.lead1_brier.rows} province-quarters. The advantage is statistically established against the three logistic regressions and the news-only LightGBM, but not against naive persistence`,
    );
  });

  it("states the quarter counts in the small-sample limitation", () => {
    renderLanding();
    expect(screen.getByText(/12 to 14 quarters of evidence for each lead time/)).toBeTruthy();
  });

  it("describes the served forecast (P0H4), never the FIRI v2 index", () => {
    const { container } = renderLanding();
    const text = container.textContent ?? "";
    expect(text).not.toMatch(/FIRI|risk index|six domains|proxy index|not a probability|Combining the domains/i);
    expect(text).toContain("The number shown is the forecast probability of High risk, from 0 to 1");
    expect(text).toContain("regional hunger measured by SWS (Balance Luzon) is above 11.3%");
    expect(text).toContain("The forecast probability is the hunger chance multiplied by the food-price chance.");
    expect(container.querySelector("#methodology")?.textContent).toContain("How the forecast is built");
    // the sources the served forecast uses, with the periods available at the 1 October 2026 issue date
    const src = container.querySelector("#methodology table")?.textContent ?? "";
    expect(src).toContain("World Bank Commodity Price Data (Pink Sheet)");
    expect(src).toContain("GDELT news event database");
    expect(src).toMatch(/Bangko Sentral ng Pilipinas cash remittances.*2021 to 2026-Q2/);
    expect(FIGURES.issue_2026_10_01.available_at_issue.E2).toBe(true);
    expect(FIGURES.issue_2026_10_01.psa_cpi_through).toBe("2026-08");
    // the two influence cautions the dashboard shows
    expect(text).toContain("The unemployment input mostly follows the calendar trend");
    expect(text).toContain("The Food Stress Sentiment Index has no measured effect on the forecast");
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
  it("shows the data sources as rows with a thin divider, not bullets, and no heading dots", () => {
    const dlg = openAbout();
    expect(dlg.querySelector(".heading-dot")).toBeNull();
    expect(dlg.querySelector(".list-disc")).toBeNull();
    const rows = within(dlg).getByText(/^Philippine Statistics Authority/).closest("ul") as HTMLElement;
    expect(rows.className).toContain("divide-y");
    expect([...rows.querySelectorAll("li")].map((li) => li.textContent)).toEqual([
      "Philippine Statistics Authority (PSA): prices, rice, poverty, population, production, labor force",
      "Bangko Sentral ng Pilipinas (BSP): cash remittances",
      "PAGASA: El Niño advisories · IBTrACS: typhoons",
      "World Bank Commodity Price Data (Pink Sheet): world rice, cereal, oil and fertilizer prices",
      "Social Weather Stations (SWS): hunger, Balance Luzon (regional)",
      "Google News headlines in Filipino and English",
    ]);
    const titles = [...dlg.querySelectorAll("h4")].map((h) => h.textContent);
    expect(titles).toEqual([
      "How to read the map",
      "Measured regional hunger (SWS)",
      "Forecast model and its tested accuracy",
      "Data sources",
      "Missing and limited data",
      "Disclaimer",
      "Contact",
    ]);
  });

  it("states the model, the map value and the tested lead time", () => {
    const dlg = openAbout();
    expect(dlg.textContent).toContain("LightGBM, 12 indicator families · risk = hunger condition × food-price condition");
    const lead = within(dlg).getByText("Lead time").parentElement as HTMLElement;
    expect(lead.textContent).toBe(
      "Lead timeReliable: the quarter starting on the issue date · further ahead: experimental",
    );
    expect(dlg.textContent).toContain("no measured hunger figure exists for any province, city or municipality");
    expect(dlg.textContent).not.toContain("reliability test");
  });

  it("has no research email and no [CONFIRM] text", () => {
    const dlg = openAbout();
    expect(dlg.innerHTML).not.toContain("aipheed.research@dlsud.edu.ph");
    expect(dlg.textContent).not.toContain("[CONFIRM");
    expect(dlg.textContent).not.toContain("Research team:");
  });
});
