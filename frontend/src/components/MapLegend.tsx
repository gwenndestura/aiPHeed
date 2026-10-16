import { LGU_MAP_COLORS, RISK_COLORS } from "@/data/types";

const LEVELS: Array<{ key: keyof typeof RISK_COLORS; label: string }> = [
  { key: "low", label: "Low" },
  { key: "high", label: "High" },
];

// E45: the municipal layer is coloured by a vulnerability / prioritization index (PSA poverty and density), not by
// a forecast, so it gets its own legend and colour scale; "insufficient data" is a visible gray.
const LGU_LEVELS: Array<{ key: keyof typeof LGU_MAP_COLORS; label: string }> = [
  { key: "low", label: "Lower" },
  { key: "medium", label: "Middle" },
  { key: "high", label: "Higher" },
  { key: "insufficient_data", label: "Insufficient data" },
];

/** `compact`: a slimmer box, for the phone layout's top-left corner. `municipal`: also explain the LGU colours. */
export function MapLegend({ compact = false, municipal = false }: { compact?: boolean; municipal?: boolean }) {
  return (
    <div className={`qt-panel ${compact ? "qt-bar-compact" : "qt-bar"} gap-3 whitespace-nowrap flex-wrap`}>
      <span className="font-medium">Province risk</span>
      <ul className="flex items-center gap-3">
        {LEVELS.map((l) => (
          <li key={l.key} className="flex items-center gap-1.5">
            <span aria-hidden className="qt-swatch" style={{ background: RISK_COLORS[l.key] }} />
            <span className="qt-muted">{l.label}</span>
          </li>
        ))}
      </ul>
      {municipal && (
        <>
          <span className="font-medium" title="PSA 2021 poverty (60%) and population density (40%), relative within the province. Not a municipal forecast.">
            City/municipality vulnerability (not a forecast)
          </span>
          <ul className="flex items-center gap-3" aria-label="City and municipality vulnerability legend">
            {LGU_LEVELS.map((l) => (
              <li key={l.key} className="flex items-center gap-1.5">
                <span aria-hidden className="qt-swatch" style={{ background: LGU_MAP_COLORS[l.key] }} />
                <span className="qt-muted">{l.label}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
