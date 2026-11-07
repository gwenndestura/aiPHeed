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
            aiPHeed forecasts food-insecurity risk in the five CALABARZON provinces with the approved E168 LightGBM
            model (accepted 2026-11-07 under the project rule: accuracy of at least 75% and better than the latest
            survey, one to three quarters ahead). The map shows each province's forecast and a planning priority for
            its 142 cities and municipalities, with the latest measured regional hunger (SWS) as context. It was developed by a student research
            team at De La Salle University - Dasmariñas, with DA Region IV-A planning staff as its
            intended users. It is not an official statistic, and DA did not develop or endorse it.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 mt-1">
          <Section title="How to read the map">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              The map shows the <b className="text-foreground">E168 food-insecurity risk forecast</b>. A province is
              at <b className="text-foreground">high food-insecurity risk</b> in a quarter when 50% or more of its
              households are forecast to be moderately or severely food insecure (FNRI HFIAS). Each province shows
              the forecast{" "}
              <b className="text-foreground">probability of high risk</b>; <b>0.50</b> or more is High risk. An{" "}
              <b className="text-foreground">active alert</b> appears when the regional value is <b>0.60</b> or
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
                  E168: a constrained LightGBM forecasts each province's change from its latest FNRI survey level,
                  from the five trigger groups. It was tested on 72 provincial forecasts for the 2018, 2019 and 2021
                  survey rounds, using only data published before each forecast was issued. Accuracy is the share of
                  correct high/low calls.
                </p>
                {[1, 2, 3, 4].map((k) => {
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
                        .filter((k) => k > 4)
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
                      ? `${risk.max_reliable_lead} quarters ahead (evidence from 3 survey rounds; Leads 1 and 3 are exactly at 75%)`
                      : "Not established"
                  }
                />
                <Row k="Forecasts further ahead" v="Not shown: from 4 quarters ahead accuracy is below 75%" />
                <Row k="News" v="Inside the five trigger groups; removing it did not measurably change the tested accuracy" />
                <Row k="Food-insecurity forecast" v="Approved: E168 LightGBM (2026-11-07, project acceptance rule)" />
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
              Forecasts are issued at the start of a quarter for the next one to three quarters, using only data
              published before the issue date.
            </p>
          </Section>

          <Section title="Missing and limited data">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              A missing input is left out, never counted as zero, and the dashboard lists missing
              inputs. Provinces with fewer than 5 news articles in the quarter are marked "Limited data".
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
            <Row k="Model" v="E168: latest FNRI survey level + LightGBM change from the five trigger groups" />
            <Row k="Map value" v="Probability that 50% or more of households are moderately or severely food insecure" />
            <Row k="Lead time" v="1 to 3 quarters ahead meet the acceptance rule · further ahead: not shown" />
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
// The served E168 model's sources (backend/app/e168/lgbm_only.py inputs); SWS is shown as context only.
const DATA_SOURCES = [
  "FNRI National and Expanded National Nutrition Surveys: household food insecurity (HFIAS), by province",
  "Philippine Statistics Authority (PSA): food and rice prices, farm and fisheries production, poverty, population, labor force",
  "Bangko Sentral ng Pilipinas (BSP): cash remittances",
  "NASA POWER: rainfall and soil moisture · IBTrACS: typhoons · NOAA: El Niño index (ONI)",
  "News in Filipino and English (GDELT, newspaper archives, Google News titles)",
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
