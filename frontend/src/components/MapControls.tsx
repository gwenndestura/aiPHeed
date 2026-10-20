import { Plus, Minus, type LucideIcon } from "lucide-react";

interface Props {
  /**
   * "column" (default): top right of the map, beside the right panel, with
   * the panel toggle below the zoom buttons. "row": the two zoom buttons side
   * by side at 44px, placed by the parent (the phone layout).
   */
  layout?: "column" | "row";
  rightOffset?: number;
  toggleLabel?: string;
  toggleIcon?: LucideIcon;
  onToggle?: () => void;
}

export function MapControls({ layout = "column", rightOffset = 0, toggleLabel, toggleIcon: ToggleIcon, onToggle }: Props) {
  const zoomIn = () => window.dispatchEvent(new CustomEvent("aipheed:zoom-in"));
  const zoomOut = () => window.dispatchEvent(new CustomEvent("aipheed:zoom-out"));

  if (layout === "row") {
    // Two round floating buttons.
    const cell = "w-11 h-11 flex items-center justify-center surface-float rounded-full border hover:bg-secondary/70 text-foreground";
    return (
      <div className="flex shrink-0 gap-1.5">
        <button onClick={zoomIn} aria-label="Zoom in" className={cell}>
          <Plus className="h-5 w-5" />
        </button>
        <button onClick={zoomOut} aria-label="Zoom out" className={cell}>
          <Minus className="h-5 w-5" />
        </button>
      </div>
    );
  }

  return (
    <div
      className="absolute top-4 z-[1002] flex flex-col gap-1.5 transition-[right] duration-300"
      style={{ right: rightOffset + 12 }}
    >
      {/* Border sits on each button (not the wrapper) so every cell is the same
          32x32 box as the panel toggle below; -mt-px collapses the shared edge.
          The wrapper is the rounded floating surface. */}
      <div className="flex flex-col surface-float rounded-md overflow-hidden">
        <button
          onClick={zoomIn}
          aria-label="Zoom in"
          className="w-8 h-8 flex items-center justify-center border edge-faint hover:bg-secondary/70 text-foreground"
        >
          <Plus className="h-4 w-4" />
        </button>
        <button
          onClick={zoomOut}
          aria-label="Zoom out"
          className="w-8 h-8 -mt-px flex items-center justify-center border edge-faint hover:bg-secondary/70 text-foreground"
        >
          <Minus className="h-4 w-4" />
        </button>
      </div>
      {onToggle && ToggleIcon && (
        <button
          onClick={onToggle}
          aria-label={toggleLabel}
          title={toggleLabel}
          className="w-8 h-8 surface-float rounded-md flex items-center justify-center border hover:bg-secondary/70 hover:border-primary/50 text-foreground"
        >
          <ToggleIcon className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
