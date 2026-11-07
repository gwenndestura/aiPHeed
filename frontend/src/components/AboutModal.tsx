import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Compass, Info, Mail } from "lucide-react";
import { requestTour } from "@/lib/tour";
import { useFinalOverview } from "@/lib/queries";
import logoDark from "@/assets/logo-dark.png";
import logoLight from "@/assets/logo-light.png";

export function AboutModal() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { data: overview } = useFinalOverview(open);
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
            aiPHeed forecasts food-insecurity risk in the five CALABARZON provinces with the thesis model E168
            (LightGBM). For each province it gives the probability that at least half of households will be moderately or
            severely food insecure (DOST-FNRI Household Food Insecurity Access Scale) in the coming quarter, and a planning
            priority for its 142 cities and municipalities. It was developed by a student research team at De La Salle
            University - Dasmariñas, with DA Region IV-A planning staff as its intended users. It is not an official
            statistic, and DA did not develop or endorse it.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 mt-1">
          <Section title="How to read the map">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              Each province shows the <b className="text-foreground">probability of high food-insecurity risk</b>: the
              chance that its share of households with moderate or severe food insecurity (HFIAS) is 50% or more in that
              quarter. <b>0.50</b> or more is High risk. An <b className="text-foreground">active alert</b> appears when
              the regional value is <b>0.60</b> or higher. City and municipal values rank towns within each province by
              poverty (60%) and population density (40%); they are a priority ranking, not separate forecasts.
              Quarters before 2027-Q1 are back-forecasts made with only the data available at the time; DOST-FNRI has not
              published provincial results for those quarters, so they cannot be checked.
            </p>
          </Section>

          <Section title="Regional hunger context (SWS)">
            {overview ? (
              <div className="space-y-1.5 text-[11px] leading-relaxed text-muted-foreground">
                <p>
                  Latest survey: <b className="text-foreground">{overview.regionalHunger.latest.quarter}</b>{" "}
                  (fieldwork {overview.regionalHunger.latest.fieldwork.replace("/", " to ")}, published{" "}
                  {overview.regionalHunger.latest.published}). In Balance Luzon (all of Luzon outside Metro Manila, not
                  CALABARZON alone), <b className="text-foreground">{overview.regionalHunger.latest.balanceLuzon}%</b> of
                  families experienced hunger (±{overview.regionalHunger.latest.balanceLuzonMarginPts} points); nationally{" "}
                  {overview.regionalHunger.latest.national}%. This is context only: it is not the forecast target.
                </p>
              </div>
            ) : (
              <p className="text-[11px] text-muted-foreground">Loading the latest survey…</p>
            )}
          </Section>

          <Section title="How accurate is E168?">
            <div className="grid gap-1.5">
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                Tested on 72 province results from the DOST-FNRI surveys of 2018, 2019 and 2021, each forecast made with only
                the data published before it. Accuracy is the share of correct high/low calls (always guessing low: 0.65).
              </p>
              <Row k="1 quarter ahead" v="accuracy 0.78 (56 of 72) · AUC 0.90 · passes all six strict checks" />
              <Row k="2 quarters ahead" v="accuracy 0.76 (55 of 72) · AUC 0.89 · passes 5 of 6 strict checks" />
              <Row k="3 quarters ahead" v="accuracy 0.75 (54 of 72)" />
              <Row k="Reliable horizon (study rule: at least 75% accuracy)" v="Up to 3 quarters ahead" />
              <Row k="Baselines" v="Better than all six comparison models (persistence, logistic, LightGBM on one source)" />
              <Row k="Live test" v="The 2027-Q1 forecast was sealed before any outcome existed (SHA-256 28f2c918)" />
            </div>
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
              Survey history from 2013 is used. Forecasts are issued at the start of each quarter for the next quarter,
              using only data published before the issue date.
            </p>
          </Section>

          <Section title="Missing and limited data">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              LightGBM handles a missing input as missing, not as zero. Provinces with fewer than 5 news articles
              in the quarter are marked "Limited data". Employment and remittance inputs are national series, the
              same for every province.
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
            <Row k="Model" v="E168: last DOST-FNRI survey adjusted by LightGBM (prices, climate, production, employment, remittances, news)" />
            <Row k="Map value" v="Probability of high food-insecurity risk (HFIAS moderate or severe ≥ 50%)" />
            <Row k="Lead time" v="Reliable up to 3 quarters ahead (≥ 75% accuracy)" />
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
  "DOST-FNRI provincial food-security surveys (HFIAS): 2013, 2015, 2018, 2019, 2021",
  "Philippine Statistics Authority (PSA): prices, rice, poverty, population, production, labor force",
  "Bangko Sentral ng Pilipinas (BSP): cash remittances",
  "NASA POWER: rainfall and soil moisture · IBTrACS: typhoons · NOAA: El Niño index",
  "Social Weather Stations (SWS): hunger by area (used to scale forecast confidence)",
  "Google News headlines in Filipino and English",
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
