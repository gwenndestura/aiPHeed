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

// Every lead-time figure the page states about the served FINAL forecast (walk-forward evaluation, backend/data/final/meta).
const META = resolve(__dirname, "../../../backend/data/final/meta");
const HORIZON = JSON.parse(readFileSync(resolve(META, "lead_horizon.json"), "utf-8")).leads;
const FIGURES = JSON.parse(readFileSync(resolve(META, "thesis_metrics.json"), "utf-8"));
const pctTxt = (v: number) => `${(Math.round(v * 1000) / 10).toFixed(1).replace(/\.0$/, "")}%`;

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
      "A geospatial system that forecasts food-insecurity risk in the five CALABARZON provinces one and two quarters ahead, using the FINAL (RATE + MIND) LightGBM model, updated automatically on the 10th of every month.",
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

  it("shows the methodology steps as numbered paragraphs, not cards", () => {
    const { container } = renderLanding();
    expect(container.querySelector("#methodology ol")).toBeNull();
    expect(container.querySelector("#methodology .inner-card")).toBeNull();
    const titles = [...container.querySelectorAll("#methodology h4")].map((h) => h.textContent);
    expect(titles.slice(0, 6)).toEqual([
      "1.What High risk means",
      "2.Survey starting point",
      "3.Forecast change (LightGBM, RATE + MIND)",
      "4.Classification",
      "5.Why each forecast came out as it did",
      "6.City and municipal ranking",
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
      "a LightGBM forecast of the change from each province's latest FNRI survey level",
    );
  });

  it("words the lead time one way: one and two quarters ahead, issued automatically, never Lead-2", () => {
    const { container } = renderLanding();
    const text = container.textContent ?? "";
    expect(text).not.toMatch(/Lead-2|\(Lead 2\)|experimental|local preview/i);
    expect(text).toContain("a new forecast is issued automatically on the 10th of every month");
    expect(text).not.toContain("1 November 2026");                       // no issue date frozen into the page
    fireEvent.click(screen.getByRole("button", { name: "How far ahead does it forecast?" }));
    expect(screen.getByText(/^One and two quarters ahead\. A new forecast is issued on the 10th of every month/)).toBeTruthy();
    expect(text).not.toContain("10 November 2026");                      // no issue date frozen into the page
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

  it("shows FINAL's lead-time table (backend/data/final/meta), Leads 1-2 marked as passing", () => {
    const { container } = renderLanding();
    const table = container.querySelector("#accuracy table") as HTMLTableElement;
    const rows = [...table.querySelectorAll("tbody tr")].map((tr) =>
      [...tr.querySelectorAll("td")].slice(0, 6).map((td) => td.textContent),
    );
    expect(rows).toHaveLength(5);
    rows.forEach((r, i) => {
      const L = String(i + 1);
      const m = FIGURES[L].HCW;
      // weighted F1 from the pooled confusion counts (Lead 1: TP 20, FP 5, FN 5, TN 42 -> 0.861)
      const WF1 = ["86.1%", "84.8%", "82%", "82.2%", "79.4%"];
      expect(r).toEqual([pctTxt(HORIZON[L].accuracy), pctTxt(m.precision_high), pctTxt(m.recall_high), pctTxt(m.f1_high), WF1[i], m.auc_roc.toFixed(3)]);
    });
    const heads = [...table.querySelectorAll("tbody th")].map((th) => th.textContent);
    expect(heads.slice(0, 2).every((h) => h?.includes("All five measures 75% or more (pooled)"))).toBe(true);
    expect(heads.slice(2).some((h) => h?.includes("All five measures"))).toBe(false);
    expect(table.textContent).toContain("72 provincial forecasts, 3 survey rounds");
    const acc = container.querySelector("#accuracy")?.textContent ?? "";
    expect(acc).toContain("The map shows only the forecasts 1 and 2 quarters ahead");
    expect(acc).toContain("All results below are development evidence");
    expect(acc).toContain("The 75% goal");
  });

  it("shows the one-quarter-ahead Brier comparison on the same 72 forecasts", () => {
    const { container } = renderLanding();
    const tables = [...container.querySelectorAll("#accuracy table")];
    const brier = tables[tables.length - 1];
    const cells = [...brier.querySelectorAll("tr")].map((tr) => [
      tr.querySelector("th")?.textContent,
      tr.querySelector("td")?.textContent,
    ]);
    expect(cells).toEqual([
      ["LightGBM FINAL (RATE + MIND)", "0.123"],
      ["Naive persistence (latest survey)", "0.253"],
      ["PSA indicators only (logistic)", "0.274"],
      ["News only (logistic)", "0.244"],
      ["Logistic regression, all inputs", "0.320"],
    ]);
    expect(container.querySelector("#accuracy")?.textContent).toContain(
      "Same 72 provincial forecasts. The advantage over naive persistence is statistically established",
    );
  });

  it("states the survey-round counts in the small-sample limitation", () => {
    renderLanding();
    expect(screen.getByText(/72 provincial forecasts from three FNRI survey rounds/)).toBeTruthy();
  });

  it("describes the served forecast (FINAL), never the FIRI v2 index or the price-pressure index", () => {
    const { container } = renderLanding();
    const text = container.textContent ?? "";
    expect(text).not.toMatch(/FIRI|risk index|price-pressure|six domains|proxy index|11\.3%|Combining the domains/i);
    expect(text).toContain("The number shown is the food insecurity risk, from 0% to 100%");
    expect(text).toContain("Household Food Insecurity Access Scale (HFIAS)");
    expect(container.querySelector("#methodology")?.textContent).toContain("How the forecast is built");
    expect(text).not.toMatch(/did not (measurably )?change the tested accuracy/);
  });

  it("does not list or explain the forecast model's input variables", () => {
    const { container } = renderLanding();
    const text = container.textContent ?? "";
    expect(container.querySelector("#methodology table")).toBeNull();
    expect(container.querySelector("#methodology")?.textContent).not.toContain("Data sources");
    expect(text).not.toMatch(
      /trigger group|remittance|fisheries production|Fish production|Oceanic Ni|El Niño index|GRDP|regional accounts|Consumer Price Index|Labor Force Survey|NASA POWER|IBTrACS|XLM-RoBERTa|BERTopic|Other model inputs|Used now/,
    );
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
    const rows = within(dlg).getByText(/^FNRI National/).closest("ul") as HTMLElement;
    expect(rows.className).toContain("divide-y");
    expect([...rows.querySelectorAll("li")].map((li) => li.textContent)).toEqual([
      "FNRI National and Expanded National Nutrition Surveys: household food insecurity (HFIAS), by province",
      "Philippine Statistics Authority (PSA): food and rice prices, farmgate and wholesale rice prices, palay and corn production, regional GRDP, poverty, population, labor force",
      "NASA POWER: rainfall and soil moisture · IBTrACS: typhoons · NOAA: El Niño index (ONI)",
      "News, mostly in English (newspaper archives and Google News titles; about 1.6% Filipino or mixed)",
      "Social Weather Stations (SWS): hunger, Balance Luzon (regional; context, not a model input)",
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
    expect(dlg.textContent).toContain("FINAL (RATE + MIND): latest FNRI survey level + LightGBM change per quarter");
    expect(dlg.textContent).not.toMatch(/LOCAL PREVIEW|local preview/);
    const lead = within(dlg).getByText("Lead time").parentElement as HTMLElement;
    expect(lead.textContent).toBe("Lead time1 and 2 quarters ahead: all five measures 75% or more (pooled) · further ahead: not shown");
    expect(dlg.textContent).toContain("not a measured or forecast municipal rate");
    expect(dlg.textContent).not.toContain("reliability test");
  });

  it("has no research email and no [CONFIRM] text", () => {
    const dlg = openAbout();
    expect(dlg.innerHTML).not.toContain("aipheed.research@dlsud.edu.ph");
    expect(dlg.textContent).not.toContain("[CONFIRM");
    expect(dlg.textContent).not.toContain("Research team:");
  });
});
