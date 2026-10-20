import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Compass, Info, Mail } from "lucide-react";
import { requestTour } from "@/lib/tour";
import logoDark from "@/assets/logo-dark.png";
import logoLight from "@/assets/logo-light.png";

export function AboutModal() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { pathname } = useLocation();
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
            aiPHeed is an estimated food-insecurity risk index for the five CALABARZON provinces,
            forecast two quarters ahead to support planning. It was developed by a student research
            team at De La Salle University - Dasmariñas, with DA Region IV-A planning staff as its
            intended users. It is not an official statistic, and DA did not develop or endorse it.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 mt-1">
          <Section title="How to read the map">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              Each province shows a <b className="text-foreground">risk index from 0 to 1</b>. A score of{" "}
              <b>0.50</b> or higher is <b className="text-foreground">High risk</b>; below 0.50 is Low risk.
              The index is not a probability. An <b className="text-foreground">active alert</b> appears
              when the regional index is <b>0.60</b> or higher. City and municipal values are a relative
              prioritization within each province, not forecasts.
            </p>
          </Section>

          <Section title="Data sources">
            <ul className="text-[11px] leading-relaxed text-muted-foreground list-disc pl-4 space-y-0.5">
              <li>Philippine Statistics Authority (PSA): prices, rice, poverty, population, production, labor force</li>
              <li>Bangko Sentral ng Pilipinas (BSP): cash remittances</li>
              <li>PAGASA: El Niño advisories · IBTrACS: typhoons</li>
              <li>Social Weather Stations (SWS): hunger, Balance Luzon (regional)</li>
              <li>Google News headlines in Filipino and English</li>
            </ul>
            <p className="text-[10px] text-muted-foreground/70 mt-1.5">
              Only data from 2021 onward is used. Estimates are issued quarterly, two quarters ahead.
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
              {/* Not yet confirmed by the research team: plain text, not a link. */}
              <span className="inline-flex items-center gap-1.5 h-8 compact:h-11 px-3 rounded-full border border-dashed edge-control text-[11px] font-medium text-muted-foreground">
                Research team: [CONFIRM: research team email]
              </span>
            </div>
          </Section>

          <div className="grid gap-2 pt-1">
            <Row k="Model" v="Risk index FIRI v2 · LightGBM price input" />
            <Row k="Price input (LightGBM, Lead-2)" v="accuracy 0.72 · F1 0.59 · AUC 0.65" />
            <Row k="Lead time" v="Two quarters ahead. No forecast horizon has yet met the reliability test." />
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

/** The phone number and email: outlined pills. */
const CONTACT_CHIP =
  "inline-flex items-center gap-1.5 h-8 compact:h-11 px-3 rounded-full border edge-control text-[11px] font-medium text-foreground hover:bg-secondary/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/** A section: a flat rounded card with a small title. */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="inner-card px-3.5 py-3">
      <h4 className="flex items-center gap-2 text-[12px] font-semibold mb-1.5">
        <span aria-hidden className="heading-dot" />
        {title}
      </h4>
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
