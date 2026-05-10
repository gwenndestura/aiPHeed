// Persistent rejection log shared between Admin and public dashboard.
// Uses localStorage + a custom event so any open tab updates immediately.

export interface RejectionEntry {
  province: string;       // display name, e.g. "Quezon"
  provinceId: string;     // lowercased id, e.g. "quezon"
  quarter: string;        // e.g. "2026-Q4"
  reason: string;
  notes?: string;
  timestamp: string;      // ISO
}

const KEY = "aipheed_rejections";
const EVT = "aipheed:rejections-changed";

export function loadRejections(): RejectionEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as RejectionEntry[]) : [];
  } catch {
    return [];
  }
}

function save(entries: RejectionEntry[]) {
  localStorage.setItem(KEY, JSON.stringify(entries));
  window.dispatchEvent(new CustomEvent(EVT));
}

export function addRejection(entry: RejectionEntry) {
  const all = loadRejections().filter(
    (e) => !(e.provinceId === entry.provinceId && e.quarter === entry.quarter)
  );
  all.unshift(entry);
  save(all);
}

export function removeRejection(provinceId: string, quarter: string) {
  const all = loadRejections().filter(
    (e) => !(e.provinceId === provinceId && e.quarter === quarter)
  );
  save(all);
}

export function isRejected(provinceId: string, quarter: string): boolean {
  return loadRejections().some(
    (e) => e.provinceId === provinceId && e.quarter === quarter
  );
}

export function getRejectedProvinceIdsForQuarter(quarter: string): Set<string> {
  return new Set(loadRejections().filter((e) => e.quarter === quarter).map((e) => e.provinceId));
}

export function onRejectionsChanged(cb: () => void): () => void {
  const handler = () => cb();
  window.addEventListener(EVT, handler);
  window.addEventListener("storage", handler);
  return () => {
    window.removeEventListener(EVT, handler);
    window.removeEventListener("storage", handler);
  };
}
