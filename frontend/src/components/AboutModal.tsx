import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Compass, Info, Mail } from "lucide-react";
import { requestTour } from "@/lib/tour";
import { useFinalOverview, useFinalRiskEvaluation } from "@/lib/queries";
import type { FinalOverview } from "@/lib/apiTypes";
import logoDark from "@/assets/logo-dark.png";
import logoLight from "@/assets/logo-light.png";

export function AboutModal() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { data: overview } = useFinalOverview(open);
  const { data: risk } = useFinalRiskEvaluation(open);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger className="flex items-center gap-1.5 compact:min-h-11 text-[10px] text-muted-foreground hover:text-foreground transition-colors">
        <Info className="h-3 w-3" />
        About & Methodology
      </DialogTrigger>
      <DialogContent className="z-[1200] max-w-lg max-h-[85vh] overflow-y-auto thin-scrollbar w-[calc(100%-24px)] rounded-sheet border-0">
        <DialogHeader className="text-left sm:text-left">
          <img src={logoDark} alt="" className="dark-only h-10 w-auto self-start object-contain" />
          <img src={logoLight} alt="" className="light-only h-10 w-auto self-start object-contain" />
          <DialogTitle className="text-sm pt-2">About aiPHeed</DialogTitle>
          <DialogDescription className="text-[11px] leading-relaxed pt-2">
            aiPHeed with the FINAL (RATE + MIND) LightGBM model, updated automatically every quarter (in walk-forward tests all five
            accuracy measures reach 75%, pooled, one and two quarters ahead, retrospectively, so only those two quarters are shown;
            no lead passes in every single survey round). The map shows each province's forecast and a planning priority for
            its 142 cities and municipalities, with the latest measured regional hunger (SWS) as context. It was developed by a student research
            team at De La Salle University - Dasmariñas, with DA Region IV-A planning staff as its
            intended users. It is not an official statistic, and DA did not develop or endorse it.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 mt-1">
          <Section title="How to read the map">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              The map shows the <b className="text-foreground">FINAL (RATE + MIND) food-insecurity risk forecast</b>. A province is
              at <b className="text-foreground">high food-insecurity risk</b> in a quarter when 50% or more of its
              households are forecast to be moderately or severely food insecure (FNRI HFIAS). Each province shows
              the forecast{" "}
              <b className="text-foreground">share of food-insecure households</b>; <b>50%</b> or more is High risk. An{" "}
              <b className="text-foreground">active alert</b> appears when a province's forecast share is <b>60%</b> or
              higher. City and municipal values rank towns within each province by poverty and density; they are a
              priority ranking from the province forecast, not a measured or forecast municipal rate.
            </p>
          </Section>

          <Section title="Measured regional hunger (SWS)">
            {overview ? (
              <div className="space-y-1.5 text-[11px] leading-relaxed text-muted-foreground">
                <p>
                  Latest survey: <b className="text-foreground">{overview.regionalHunger.latest.quarter}</b>{" "}
                  (fieldwork {overview.regionalHunger.latest.fieldwork.replace("/", " to ")}, published{" "}
                  {overview.regionalHunger.latest.published}; {overview.regionalHunger.latest.ageDaysAtAsOf} days
                  old on {overview.asOf}). In Balance Luzon, which includes CALABARZON,{" "}
                  <b className="text-foreground">{overview.regionalHunger.latest.balanceLuzon}%</b> of families
                  experienced hunger (survey margin ±{overview.regionalHunger.latest.balanceLuzonMarginPts} points);
                  nationally {overview.regionalHunger.latest.national}%.
                </p>
                <p>{overview.localEvidence}</p>
              </div>
            ) : (
              <p className="text-[11px] text-muted-foreground">Loading the latest survey…</p>
            )}
          </Section>

          <Section title="Forecast model and its tested accuracy">
            {risk ? (
              <div className="grid gap-1.5">
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  FINAL (RATE + MIND): a constrained LightGBM forecasts each province's change per quarter from its latest
                  FNRI survey level, from food prices, local rice and palay prices, weather and farm supply, dry spells
                  and typhoons, rice and corn harvests, jobs (national), the regional economy, poverty and population, and
                  news on food stress, with HIGH and LOW cases weighted equally and the average of five fits. Each forecast keeps
                  only the 25 candidate inputs most related to the outcome; the groups it used are shown under "Why is this at risk?". It was tested on 72 provincial forecasts for the
                  2018, 2019 and 2021 survey rounds, using only data published before each forecast was issued, and
                  these same results were also used to choose this setup. Accuracy is the share of correct high/low calls.
                </p>
                {[1, 2, 3, 4, 5, 6, 7].map((k) => {
                  const l = risk.leads[String(k)];
                  if (!l) return null;
                  return (
                    <Row
                      key={k}
                      k={`${k} quarter${k > 1 ? "s" : ""} ahead`}
                      v={`accuracy ${l.metrics.accuracy.toFixed(2)} (${l.n} cases; always-low ${(l.baseline_accuracy["ALWAYS-LOW"] ?? 0).toFixed(2)}) · ${l.reliable ? "reliable" : "not reliable"}`}
                    />
                  );
                })}
                <Row
                  k="75% accuracy (project acceptance rule)"
                  v={risk.max_reliable_lead ? `Reached 1 to ${risk.max_reliable_lead} quarters ahead, each also better than the latest survey` : "Not reached"}
                />
                {risk.horizon && (
                  <>
                    <Row
                      k="Further horizons tested"
                      v={risk.horizon.leads_evaluated
                        .filter((k) => k > 7)
                        .map((k) => `${k} quarters ahead ${risk.horizon!.leads[String(k)].accuracy.toFixed(2)} (${risk.horizon!.leads[String(k)].n} cases; always-low ${risk.horizon!.leads[String(k)].always_low_accuracy.toFixed(2)})`)
                        .join(" · ")}
                    />
                    <Row
                      k="Longest horizon with enough data to test"
                      v={risk.horizon.testable_horizon_R1 ? `${risk.horizon.testable_horizon_R1} quarters ahead` : "None"}
                    />
                  </>
                )}
                <Row
                  k="Reliable forecast horizon"
                  v={
                    risk.max_reliable_lead
                      ? `${risk.max_reliable_lead} quarters ahead (pooled over 3 survey rounds; no lead passes in every single round; in the 2021 round 1 of 4 HIGH provinces was found)`
                      : "Not established"
                  }
                />
                <Row k="Forecasts further ahead" v="Not shown: from 3 quarters ahead precision and F1 fall below 75%" />
                <Row k="News" v="Counted inside the input groups; adds about 2 correct provinces of 72 at 1 quarter ahead only" />
                <Row k="Food-insecurity forecast" v="FINAL (RATE + MIND) LightGBM, data updated and a new forecast issued automatically on the 10th of every month; earlier forecasts kept in the forecast history" />
              </div>
            ) : (
              <p className="text-[11px] text-muted-foreground">Loading the evaluation…</p>
            )}
          </Section>

          <Section title="Data sources">
            <ul className="text-[11px] leading-relaxed text-muted-foreground divide-y">
              {DATA_SOURCES.map((s) => (
                <li key={s} className="py-1 first:pt-0 last:pb-0">
                  {s}
                </li>
              ))}
            </ul>
            <p className="text-[10px] text-muted-foreground/70 mt-1.5">
              Forecasts are issued for the next one and two quarters, using only data published before the
              issue date. All quarters shown come from the same information.
            </p>
          </Section>

          <Section title="Missing and limited data">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              A figure not yet published at the issue date is filled with its typical value and flagged as missing; it is
              never counted as zero or as low risk. News about a single province is the one exception: when there was none,
              that province's news counts as "no change from usual". Provinces with fewer than 5 news stories about them are
              marked "Limited data".
            </p>
          </Section>

          <Section title="Disclaimer">
            <p className="text-[11px] leading-relaxed italic text-foreground/90">
              "Results obtained serve only as potential risk indicators and are not to be construed
              as official food insecurity classifications or policy recommendations."
            </p>
          </Section>

          <Section title="Contact">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              For official agricultural services and information, contact the{" "}
              <b className="text-foreground">Department of Agriculture Regional Field Office IV-A (CALABARZON)</b>{" "}
              · LARES Compound, Brgy. Maraouy, Lipa City, Batangas 4217. For questions about aiPHeed,
              contact the research team.
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <a href="mailto:ored@calabarzon.da.gov.ph" className={CONTACT_CHIP}>
                <Mail aria-hidden className="h-3.5 w-3.5" /> ored@calabarzon.da.gov.ph
              </a>
            </div>
          </Section>

          <div className="grid gap-2 pt-1">
            <Row k="Model" v="FINAL (RATE + MIND): latest FNRI survey level + LightGBM change per quarter, missing-input flags, HIGH and LOW weighted equally" />
            <Row k="Map value" v="Forecast share of households moderately or severely food insecure (High risk at 50%)" />
            <Row k="Lead time" v="1 and 2 quarters ahead: all five measures 75% or more (pooled) · further ahead: not shown" />
            <Row k="Coverage" v="5 provinces · 142 LGUs" />
          </div>

          {/* Replays the map page's guided tour once this dialog has closed. */}
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              requestTour(navigate, pathname, 300, "map");
            }}
            className="mt-1 w-full flex items-center justify-center gap-2 h-9 compact:h-11 rounded-full border edge-control text-[12px] compact:text-[14px] font-semibold hover:bg-secondary/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Compass className="h-4 w-4" /> Take the tour
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** The data sources, one row each with a thin divider between rows. */
// FINAL (RATE + MIND) candidate-input sources (data/final/meta/feature_inventory.csv); SWS hunger (h2) is a candidate input that the
// current forecast does not use, so it is listed as context.
const DATA_SOURCES = [
  "FNRI National and Expanded National Nutrition Surveys: household food insecurity (HFIAS), by province",
  "Philippine Statistics Authority (PSA): food and rice prices, farmgate and wholesale rice prices, palay and corn production, regional GRDP, poverty, population, labor force",
  "NASA POWER: rainfall and soil moisture · IBTrACS: typhoons · NOAA: El Niño index (ONI)",
  "News, mostly in English (newspaper archives and Google News titles; about 1.6% Filipino or mixed)",
  "Social Weather Stations (SWS): hunger, Balance Luzon (regional; context, not a model input)",
];

/** The phone number and email: outlined pills. */
const CONTACT_CHIP =
  "inline-flex items-center gap-1.5 h-8 compact:h-11 px-3 rounded-full border edge-control text-[11px] font-medium text-foreground hover:bg-secondary/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/** A section: a flat rounded card with a small title. */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="inner-card px-3.5 py-3">
      <h4 className="text-[12px] font-semibold mb-1.5">{title}</h4>
      {children}
    </section>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:items-start sm:justify-between sm:gap-3 text-[11px] inner-box px-2.5 py-1.5">
      <span className="shrink-0 text-muted-foreground">{k}</span>
      <span className="font-semibold sm:text-right text-balance">{v}</span>
    </div>
  );
}
