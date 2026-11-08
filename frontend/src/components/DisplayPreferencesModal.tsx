import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Sliders } from "lucide-react";
import { readStorage, writeStorage } from "@/lib/storage";

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
    return { ...DEFAULTS, ...JSON.parse(readStorage(STORAGE_KEY) ?? "{}") };
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
    writeStorage(STORAGE_KEY, JSON.stringify(prefs));
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
      <DialogContent className="z-[1200] max-w-sm w-[calc(100%-24px)] rounded-sheet border-0">
        <DialogHeader className="flex-row items-center gap-3 space-y-0 pr-8 text-left sm:text-left">
          <span aria-hidden className="tint-primary h-10 w-10 rounded-xl flex items-center justify-center shrink-0">
            <Sliders className="h-4 w-4" />
          </span>
          <span className="min-w-0 space-y-1">
            <DialogTitle className="text-[14px] leading-5">Display preferences</DialogTitle>
            <DialogDescription className="text-[11px] leading-4 text-foreground/70">Choose what the map shows</DialogDescription>
          </span>
        </DialogHeader>

        <div className="space-y-2 mt-1">
          <Toggle label="Show province labels on map" value={prefs.showProvinceLabels} onChange={(v) => set("showProvinceLabels", v)} />
          <Toggle label="Show municipality boundaries" value={prefs.showMunicipalityBoundaries} onChange={(v) => set("showMunicipalityBoundaries", v)} />
          <Toggle label="Show risk score numbers on map" value={prefs.showRiskNumbers} onChange={(v) => set("showRiskNumbers", v)} />

          <div className="inner-card px-3 py-2.5">
            <p aria-hidden className="text-[11px] font-semibold mb-2">Animation speed</p>
            <div role="group" aria-label="Animation speed" className="grid grid-cols-3 gap-1 seg-track p-1">
              {(["slow", "normal", "fast"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => set("animationSpeed", s)}
                  aria-pressed={prefs.animationSpeed === s}
                  className={`h-8 compact:h-11 seg-option text-[11px] font-semibold border transition-colors capitalize ${
                    prefs.animationSpeed === s ? "seg-on" : "hover:bg-secondary/60"
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

/** An on/off option: its label and a segmented Show | Hide choice, the active one a filled amber pill. */
function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="inner-card flex items-center justify-between gap-3 px-3 py-2">
      <p className="text-[11px] font-semibold">{label}</p>
      <div role="group" aria-label={label} className="flex shrink-0 gap-1 seg-track p-1">
        {([true, false] as const).map((on) => (
          <button
            key={String(on)}
            type="button"
            onClick={() => onChange(on)}
            aria-pressed={value === on}
            className={`h-7 compact:h-11 min-w-[52px] px-3 seg-option text-[11px] font-semibold border transition-colors ${
              value === on ? "seg-on" : "hover:bg-secondary/60"
            }`}
          >
            {on ? "Show" : "Hide"}
          </button>
        ))}
      </div>
    </div>
  );
}
