import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";

interface Props {
  message?: string;
  onReview?: () => void;
}

export function EarlyWarningBanner({
  message = "Quezon — Severe Risk detected for Q4 2026. Review required before publication.",
  onReview,
}: Props) {
  const [open, setOpen] = useState(true);
  if (!open) return null;

  return (
    <div className="w-full bg-gradient-to-r from-destructive/95 via-destructive to-destructive/95 text-destructive-foreground border-b border-destructive/40 shadow-lg shadow-destructive/20 z-[1001]">
      <div className="flex items-center gap-3 px-4 py-2">
        <div className="relative flex items-center justify-center shrink-0">
          <span className="absolute inline-flex h-6 w-6 rounded-full bg-destructive-foreground/20 animate-ping" />
          <AlertTriangle className="h-4 w-4 relative" />
        </div>
        <p className="text-[11px] font-medium flex-1 truncate">
          <span className="font-bold uppercase tracking-wider mr-2 text-[10px]">Early Warning</span>
          {message}
        </p>
        <button
          onClick={onReview}
          className="text-[11px] font-bold px-3 py-1 rounded-md bg-destructive-foreground/15 hover:bg-destructive-foreground/25 transition-colors"
        >
          Review
        </button>
        <button
          onClick={() => setOpen(false)}
          aria-label="Dismiss"
          className="p-1 rounded-md hover:bg-destructive-foreground/15 transition-colors"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
