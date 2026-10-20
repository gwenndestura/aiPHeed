import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Compass, Info, Mail, Phone } from "lucide-react";
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
            aiPHeed is an interactive geospatial food-insecurity forecasting system for DA Region IV-A.
            It uses zero-shot multilingual NLP and ensemble machine learning to publish quarterly,
            3-month-ahead risk forecasts at province and municipal level. The system is intended to
            support anticipatory action — it does not replace official food-insecurity classifications.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 mt-1">
          <Section title="Forecast vs Active Alert">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              Each forecast displays a <b className="text-foreground">risk probability</b> and a{" "}
              <b className="text-foreground">HIGH / LOW</b> label using a <b>0.50</b> internal display cutoff.
              The <b className="text-foreground">active alert</b> system is gated separately at{" "}
              <b>0.60</b>, a stricter threshold designed for anticipatory action.
            </p>
          </Section>

          <Section title="Data sources">
            <ul className="text-[11px] leading-relaxed text-muted-foreground list-disc pl-4 space-y-0.5">
              <li>Philippine Statistics Authority (PSA) — CPI, FIES, LFS</li>
              <li>SWS Hunger Surveys (retrospective verification)</li>
              <li>Geocoded news corpus — Inquirer, PhilStar, BusinessWorld, ABS-CBN</li>
              <li>PAGASA climate / typhoon advisories</li>
              <li>BSP OFW remittance series · BFAR fish-kill bulletins</li>
            </ul>
            <p className="text-[10px] text-muted-foreground/70 mt-1.5">
              Publication cadence: quarterly forecasts, 3-month lead time.
            </p>
          </Section>

          <Section title="Limited data">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              Provinces with fewer than 5 geocoded articles in a quarter are marked "Limited data".
              The mark carries over to every LGU in that province (Algorithm Rule 5).
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
              For verified social protection assistance, contact{" "}
              <b className="text-foreground">DA Region IV-A (CALABARZON)</b> · BPI Compound, Marawoy,
              Lipa City, Batangas
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <a href="tel:+63437742005" className={CONTACT_CHIP}>
                <Phone aria-hidden className="h-3.5 w-3.5" /> (043) 774-2005
              </a>
              <a href="mailto:ord@calabarzon.da.gov.ph" className={CONTACT_CHIP}>
                <Mail aria-hidden className="h-3.5 w-3.5" /> ord@calabarzon.da.gov.ph
              </a>
            </div>
          </Section>

          <div className="grid grid-cols-2 gap-2 pt-1">
            <Row k="Model" v="LightGBM + SMOTE" />
            <Row k="Performance" v="F1 0.82 · AUC 0.87" />
            <Row k="Coverage" v="5 provinces · 142 LGUs" />
            <Row k="Refresh" v="Quarterly · 3-mo lead" />
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
    <div className="flex items-center justify-between text-[11px] inner-box px-2 py-1.5">
      <span className="text-muted-foreground">{k}</span>
      <span className="font-semibold text-right">{v}</span>
    </div>
  );
}
