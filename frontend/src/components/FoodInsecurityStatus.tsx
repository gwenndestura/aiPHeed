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
            not yet approved
          </span>
        </div>
        <p className="text-[10px] leading-snug">{data.message}</p>
        <p className="text-[9px] text-muted-foreground leading-snug">
          Until a forecast is approved, no food-insecurity forecast numbers are shown here.
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

  // An approved model exists: say in plain words what it is and how often it was right in past tests.
  const acc = data.accuracy_by_lead?.["1"]?.accuracy;
  const approved = data.production?.approved_utc?.slice(0, 10);
  return (
    <div className="space-y-1" data-testid="fi-status-approved">
      <h3 className="text-[13px] font-semibold leading-tight">About this forecast</h3>
      <p className="text-[10px] leading-snug">
        A computer model estimates each province's chance of high food insecurity, using food prices, weather, jobs, money
        from OFWs, fish catch and news.
        {typeof acc === "number" && ` When tested on past government surveys, it was right ${Math.round(acc * 100)}% of the time one quarter ahead.`}
      </p>
      <p className="text-[9px] text-muted-foreground">
        Model {data.production?.model_id}{approved ? `, approved ${approved}` : ""}.
      </p>
    </div>
  );
}
