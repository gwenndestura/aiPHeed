import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { RegionData, RISK_COLORS, RISK_LABELS } from "@/data/types";
import { Info, MapPin, CloudRain, Briefcase, Plane, Store, X } from "lucide-react";

interface Props {
  region: RegionData | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RegionMetadataPopup({ region, open, onOpenChange }: Props) {
  if (!region) return null;
  const color = RISK_COLORS[region.riskLevel];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="z-[1300] max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2.5">
            <div className="rounded-lg p-1.5" style={{ backgroundColor: `${color}20` }}>
              <MapPin className="h-4 w-4" style={{ color }} />
            </div>
            <div>
              <DialogTitle className="text-sm">{region.name}</DialogTitle>
              <DialogDescription className="text-[10px]">CALABARZON · Province metadata</DialogDescription>
            </div>
            <span
              className="ml-auto text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
              style={{ backgroundColor: `${color}20`, color }}
            >
              {RISK_LABELS[region.riskLevel]}
            </span>
          </div>
        </DialogHeader>

        <div className="space-y-4 mt-2">
          {/* Metadata */}
          <Section icon={Info} title="Metadata">
            <Row k="Risk Level" v={region.riskScore.toFixed(2)} accent={color} />
            <Row k="FPSI" v={`${region.fpsi}%`} />
            <Row k="QoQ Change" v={`${region.momChange > 0 ? "+" : ""}${region.momChange}%`} />
            <Row k="Households at risk" v={region.householdsAtRisk.toLocaleString()} />
          </Section>

          {/* Geography */}
          <Section icon={MapPin} title="Geography">
            <Row k="Population" v={region.population.toLocaleString()} />
            <Row k="Lat / Lng" v={`${region.lat.toFixed(2)}, ${region.lng.toFixed(2)}`} />
            <Row k="Region" v="IV-A · CALABARZON" />
          </Section>

          {/* Risk Drivers */}
          <Section icon={CloudRain} title="Risk Drivers">
            <div className="grid grid-cols-2 gap-2">
              <Driver icon={Briefcase} label="Unemployment" value={`${region.unemploymentRate}%`} />
              <Driver icon={Plane} label="OFW Index" value={`${(region.accessToFood * 100).toFixed(0)}%`} />
              <Driver icon={CloudRain} label="Climate stress" value={`${(region.cropYieldIndex * 10).toFixed(1)}/10`} />
              <Driver icon={Store} label="Market / Prices" value={`${region.fpsi}%`} />
            </div>
          </Section>

          {/* Prices */}
          <Section icon={Store} title="Prices (₱/kg, est.)">
            <Row k="Rice (regular milled)" v={`₱${(48 + region.fpsi * 0.4).toFixed(2)}`} />
            <Row k="Corn (yellow)" v={`₱${(28 + region.fpsi * 0.2).toFixed(2)}`} />
            <Row k="Vegetables (basket)" v={`₱${(72 + region.fpsi * 0.6).toFixed(2)}`} />
          </Section>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Section({ icon: Icon, title, children }: { icon: typeof Info; title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon className="h-3 w-3 text-primary" />
        <h3 className="text-[10px] font-bold uppercase tracking-wider">{title}</h3>
        <Info className="h-2.5 w-2.5 text-muted-foreground/50 ml-auto" />
      </div>
      <div className="rounded-lg border border-border/40 bg-secondary/20 p-2.5 space-y-1">{children}</div>
    </div>
  );
}

function Row({ k, v, accent }: { k: string; v: string; accent?: string }) {
  return (
    <div className="flex items-center justify-between text-[11px]">
      <span className="text-muted-foreground">{k}</span>
      <span className="font-bold tabular-nums" style={accent ? { color: accent } : undefined}>{v}</span>
    </div>
  );
}

function Driver({ icon: Icon, label, value }: { icon: typeof Info; label: string; value: string }) {
  return (
    <div className="rounded-md bg-card border border-border/40 px-2 py-1.5">
      <div className="flex items-center gap-1.5 text-[9px] uppercase tracking-wider text-muted-foreground/80 font-semibold">
        <Icon className="h-3 w-3" />
        {label}
      </div>
      <p className="text-[12px] font-bold tabular-nums mt-0.5">{value}</p>
    </div>
  );
}
