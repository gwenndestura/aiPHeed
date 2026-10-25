import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Compass, Info, Mail } from "lucide-react";
import { requestTour } from "@/lib/tour";
import { useFinalEvaluation, useFinalOverview } from "@/lib/queries";
import type { FinalOverview } from "@/lib/apiTypes";
import logoDark from "@/assets/logo-dark.png";
import logoLight from "@/assets/logo-light.png";

export function AboutModal() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { data: overview } = useFinalOverview(open);
  const { data: evaluation } = useFinalEvaluation(open);
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
            aiPHeed shows DA Region IV-A three things for the five CALABARZON provinces and their 142 cities and
            municipalities: an indicator-based priority score for the next quarter, the latest measured regional
            hunger (SWS), and a LightGBM hunger forecast with its tested accuracy. It was developed by a student research
            team at De La Salle University - Dasmariñas, with DA Region IV-A planning staff as its
            intended users. It is not an official statistic, and DA did not develop or endorse it.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 mt-1">
          <Section title="How to read the map">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              Each province shows a <b className="text-foreground">priority score from 0 to 1</b>, built from
              published indicators (prices, rice, poverty, climate, production, jobs, remittances, news and
              regional hunger). A score of <b>0.50</b> or higher is <b className="text-foreground">High priority</b>;
              below 0.50 is Low priority. The score is not a probability and not a measured hunger rate. An{" "}
              <b className="text-foreground">active alert</b> appears when the regional score is <b>0.60</b> or
              higher. City and municipal values rank towns within each province by poverty and density; no
              measured hunger figure exists for any province, city or municipality.
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
                <OutlookSentence overview={overview} />
                <p>{overview.localEvidence}</p>
              </div>
            ) : (
              <p className="text-[11px] text-muted-foreground">Loading the latest survey…</p>
            )}
          </Section>

          <Section title="Forecast model and its tested accuracy">
            {evaluation ? (
              <div className="grid gap-1.5">
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  One LightGBM model using all 12 indicator families forecasts SWS regional hunger. It was tested
                  quarter by quarter on 2023–2026, using only data published before each forecast. Accuracy is the
                  share of correct calls of whether hunger will be above its past-year average.
                </p>
                {evaluation.leads.map((l) => (
                  <Row
                    key={l.lead}
                    k={l.lead === 0 ? "Quarter just ended (survey not yet out)" : `${l.lead} quarter${l.lead > 1 ? "s" : ""} ahead`}
                    v={`accuracy ${l.metrics.accuracy.toFixed(2)} · latest reading ${(l.baselineAccuracy.PERSIST ?? 0).toFixed(2)} · error ${l.maePts.toFixed(1)} vs ${l.persistenceMaePts.toFixed(1)} pts`}
                  />
                ))}
                <Row k="75% accuracy target" v={evaluation.accuracyTargetReached ? "Reached" : "Not reached"} />
                <Row
                  k="Reliable forecast horizon"
                  v={evaluation.maxReliableLead === null ? "Not established" : `${evaluation.maxReliableLead} quarter(s)`}
                />
                <Row k="News" v="Context only: it did not improve the forecasts" />
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
              Only data from 2021 onward is used. Estimates are issued at the start of each quarter for the next
              quarter, three months ahead.
            </p>
          </Section>

          <Section title="Missing and limited data">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              A missing input is left out, never counted as zero, and the dashboard lists missing
              inputs. With fewer than 4 of the 6 domains the province shows "Insufficient data". News
              is used only when a province has at least 5 articles in the quarter; provinces below that
              are marked "Limited data".
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
            <Row k="Map score" v="Priority score FIRI v2 (indicator-based) · LightGBM price input" />
            <Row k="Hunger forecast" v="LightGBM, 12 indicator families (regional SWS hunger)" />
            <Row k="Price input (LightGBM, three months ahead)" v="accuracy 0.72 · F1 0.59 · AUC 0.65" />
            <Row k="Lead time" v="Map score: next quarter · hunger forecast: no reliable horizon established" />
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
const DATA_SOURCES = [
  "Philippine Statistics Authority (PSA): prices, rice, poverty, population, production, labor force",
  "Bangko Sentral ng Pilipinas (BSP): cash remittances",
  "PAGASA: El Niño advisories · IBTrACS: typhoons",
  "Social Weather Stations (SWS): hunger, Balance Luzon (regional)",
  "Google News headlines in Filipino and English",
];

/** The phone number and email: outlined pills. */
const CONTACT_CHIP =
  "inline-flex items-center gap-1.5 h-8 compact:h-11 px-3 rounded-full border edge-control text-[11px] font-medium text-foreground hover:bg-secondary/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/** Next quarter for Balance Luzon: the latest-reading outlook with its past range, and the LightGBM forecast. */
function OutlookSentence({ overview }: { overview: FinalOverview }) {
  const o = overview.outlook.latestReadingOutlook.find((x) => x.area === "BL" && x.trueHorizon === 1);
  const f = overview.outlook.lightgbmForecast.find((x) => x.area === "BL" && x.lead === 1);
  if (!o && !f) return null;
  return (
    <p>
      {o &&
        `Next quarter (${o.targetQuarter}): if hunger stays at the latest reading, ${o.level}%; in past quarters the ` +
          `next reading fell within ${o.range80[0]}–${o.range80[1]}% four times in five. `}
      {f &&
        `The LightGBM forecast for ${f.targetQuarter}, issued ${f.issueDate} before this survey was published, ` +
          `was ${f.forecastLevel.toFixed(1)}%.`}
    </p>
  );
}

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
