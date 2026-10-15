import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Sliders } from "lucide-react";

const STORAGE_KEY = "aipheed_display_prefs_v2";

export interface DisplayPrefs {
  showProvinceLabels: boolean;
  showMunicipalityBoundaries: boolean;
  showRiskNumbers: boolean;
  animationSpeed: "slow" | "normal" | "fast";
}

const DEFAULTS: DisplayPrefs = {
  showProvinceLabels: true,
  showMunicipalityBoundaries: true,
  showRiskNumbers: false,
  animationSpeed: "normal",
};

export function loadDisplayPrefs(): DisplayPrefs {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}") };
  } catch {
    return DEFAULTS;
  }
}

function applyPrefs(p: DisplayPrefs) {
  const root = document.documentElement;
  root.dataset.provinceLabels = p.showProvinceLabels ? "on" : "off";
  root.dataset.muniBoundaries = p.showMunicipalityBoundaries ? "on" : "off";
  root.dataset.riskNumbers = p.showRiskNumbers ? "on" : "off";
  root.dataset.animSpeed = p.animationSpeed;
  const ms = p.animationSpeed === "slow" ? "600ms" : p.animationSpeed === "fast" ? "120ms" : "300ms";
  root.style.setProperty("--motion-duration", ms);
  // Notify listeners (map etc.)
  window.dispatchEvent(new CustomEvent("aipheed:prefs", { detail: p }));
}

export function DisplayPreferencesModal({ trigger }: { trigger?: React.ReactNode }) {
  const [prefs, setPrefs] = useState<DisplayPrefs>(() => loadDisplayPrefs());

  useEffect(() => {
    applyPrefs(prefs);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  }, [prefs]);

  const set = <K extends keyof DisplayPrefs>(k: K, v: DisplayPrefs[K]) => setPrefs((p) => ({ ...p, [k]: v }));

  return (
    <Dialog>
      <DialogTrigger asChild>
        {trigger ?? (
          <button className="w-full flex items-center gap-3 px-2 py-2 rounded-md hover:bg-secondary/60 transition-colors text-left">
            <Sliders className="h-3.5 w-3.5 text-muted-foreground" />
            <div className="flex-1 min-w-0">
              <div className="text-[11px] font-medium">Display preferences</div>
              <div className="text-[9px] text-muted-foreground/70 truncate">Labels, boundaries, animation</div>
            </div>
          </button>
        )}
      </DialogTrigger>
      <DialogContent className="z-[1200] max-w-sm">
        <DialogHeader>
          <DialogTitle className="text-sm">Display preferences</DialogTitle>
          <DialogDescription className="text-[11px]">Tune how aiPHeed feels for you.</DialogDescription>
        </DialogHeader>

        <div className="space-y-3 mt-2">
          <Toggle label="Show province labels on map" value={prefs.showProvinceLabels} onChange={(v) => set("showProvinceLabels", v)} />
          <Toggle label="Show municipality boundaries" value={prefs.showMunicipalityBoundaries} onChange={(v) => set("showMunicipalityBoundaries", v)} />
          <Toggle label="Show risk score numbers on map" value={prefs.showRiskNumbers} onChange={(v) => set("showRiskNumbers", v)} />

          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground/70 font-semibold mb-1.5">Animation speed</p>
            <div className="grid grid-cols-3 gap-1.5">
              {(["slow", "normal", "fast"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => set("animationSpeed", s)}
                  className={`h-8 rounded-md text-[11px] font-semibold border transition-colors capitalize ${
                    prefs.animationSpeed === s
                      ? "bg-primary text-primary-foreground border-primary"
                      : "border-border/50 hover:bg-secondary/60"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!value)}
      className="w-full flex items-center justify-between gap-3 p-2 rounded-md hover:bg-secondary/40 transition-colors text-left"
    >
      <p className="text-[11px] font-semibold">{label}</p>
      <span
        className={`relative w-9 h-5 rounded-full transition-colors shrink-0 ${
          value ? "bg-primary" : "bg-secondary border border-border/60"
        }`}
      >
        <span
          className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
            value ? "translate-x-4" : "translate-x-0"
          }`}
        />
      </span>
    </button>
  );
}
