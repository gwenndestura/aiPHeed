import { useFoodInsecurityStatus } from "@/lib/queries";
import { isLoadFailure } from "@/lib/loadError";

/**
 * The official food-insecurity forecast area. It reads only GET /api/v1/final/food-insecurity/outlook, which serves a
 * model the release gate has approved and otherwise answers `validation_pending` with no forecast values. Nothing here
 * falls back to a candidate, a placeholder or another model.
 */
export function FoodInsecurityStatusCardBody() {
  const { data, error, isLoading } = useFoodInsecurityStatus();

  if (isLoading) return <p className="text-[10px] text-muted-foreground py-2">Loading forecast status…</p>;
  if (error || !data) {
    return (
      <div className="space-y-1" data-testid="fi-status-unavailable">
        <h3 className="text-[13px] font-semibold leading-tight">Food-insecurity forecast</h3>
        <p className="text-[10px] text-muted-foreground">
          {isLoadFailure(error) ? "The forecast status could not be loaded." : "Unavailable."} No forecast is shown.
        </p>
      </div>
    );
  }

  if (data.status !== "approved") {
    return (
      <div className="space-y-2" data-testid="fi-status-pending">
        <div className="flex items-center gap-2">
          <h3 className="text-[13px] font-semibold leading-tight">Food-insecurity forecast</h3>
          <span className="ml-auto px-1.5 py-0.5 rounded-md bg-muted text-muted-foreground text-[9px] font-bold uppercase tracking-wider">
            validation pending
          </span>
        </div>
        <p className="text-[10px] leading-snug">{data.message}</p>
        <p className="text-[9px] text-muted-foreground leading-snug">
          The colours and scores on the map are a price-pressure risk index (food prices together with regional hunger),
          shown as context. They are not a food-insecurity forecast.
        </p>
        {data.candidates.length > 0 && (
          <p className="text-[9px] text-muted-foreground leading-snug" data-testid="fi-status-candidates">
            Models under evaluation:{" "}
            {data.candidates
              .map((c) => `${c.model_id} (${c.status}; ${c.failed_checks.length} of ${c.checks_total ?? data.acceptance_checks_total} checks not yet passed)`)
              .join("; ")}
            .
          </p>
        )}
      </div>
    );
  }

  // An approved model exists: show its identity only. Its forecast display is added when a model is approved.
  return (
    <div className="space-y-1" data-testid="fi-status-approved">
      <h3 className="text-[13px] font-semibold leading-tight">Food-insecurity forecast</h3>
      <p className="text-[10px] text-muted-foreground">
        Approved model {data.production?.model_id} ({data.production?.version}), approved {data.production?.approved_utc}.
      </p>
    </div>
  );
}
