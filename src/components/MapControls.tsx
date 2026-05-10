import { Plus, Minus, PanelsTopLeft, PanelsRightBottom } from "lucide-react";

interface Props {
  leftOffset: number;
  rightOffset: number;
  bothCollapsed: boolean;
  onToggleBoth: () => void;
}

export function MapControls({ leftOffset, rightOffset, bothCollapsed, onToggleBoth }: Props) {
  const zoomIn = () => window.dispatchEvent(new CustomEvent("aipheed:zoom-in"));
  const zoomOut = () => window.dispatchEvent(new CustomEvent("aipheed:zoom-out"));

  return (
    <div
      className="absolute top-4 z-[1002] flex flex-col gap-1.5 transition-[right] duration-300"
      style={{ right: rightOffset + 12 }}
    >
      <div className="flex flex-col rounded-md overflow-hidden border border-border/60 bg-card/95 backdrop-blur-sm shadow-lg">
        <button
          onClick={zoomIn}
          aria-label="Zoom in"
          className="w-8 h-8 flex items-center justify-center hover:bg-secondary/70 text-foreground border-b border-border/50"
        >
          <Plus className="h-4 w-4" />
        </button>
        <button
          onClick={zoomOut}
          aria-label="Zoom out"
          className="w-8 h-8 flex items-center justify-center hover:bg-secondary/70 text-foreground"
        >
          <Minus className="h-4 w-4" />
        </button>
      </div>
      <button
        onClick={onToggleBoth}
        aria-label={bothCollapsed ? "Open both panels" : "Collapse both panels"}
        title={bothCollapsed ? "Open both panels" : "Collapse both panels"}
        className="w-8 h-8 rounded-md flex items-center justify-center border border-border/60 bg-card/95 backdrop-blur-sm shadow-lg hover:bg-secondary/70 hover:border-primary/50 text-foreground"
      >
        {bothCollapsed ? <PanelsTopLeft className="h-4 w-4" /> : <PanelsRightBottom className="h-4 w-4" />}
      </button>
    </div>
  );
}
