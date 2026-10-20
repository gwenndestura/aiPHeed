import { useEffect, useRef, useCallback, useMemo, useState } from "react";
import L from "leaflet";
import { leafletLayer } from "protomaps-leaflet";
import { RegionData, MunicipalityData, RISK_COLORS, NO_DATA_COLOR } from "@/data/types";
import "leaflet/dist/leaflet.css";

// Self-hosted open basemap — a single Protomaps .pmtiles file built from
// OpenStreetMap data (ODbL). No API key and no third-party runtime call, so
// the map keeps working without a vendor relationship. The file location is
// deploy-configurable; see docs/basemap.md for how to generate it.
const PMTILES_URL =
  (import.meta.env.VITE_BASEMAP_PMTILES_URL as string | undefined) || "/basemap.pmtiles";
const BASEMAP_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://protomaps.com">Protomaps</a>';

interface Props {
  regions: RegionData[];                        // CALABARZON provinces
  selectedRegion: RegionData | null;            // selected province
  selectedMunicipality: MunicipalityData | null;
  // Municipalities for whichever province is currently selected/zoomed. The
  // API serves one province's roster at a time, and only one province is
  // ever zoomed-into at once, so the parent passes just that roster.
  municipalities: MunicipalityData[];
  onHover: (r: RegionData | null) => void;
  onClick: (r: RegionData) => void;
  onMunicipalityClick: (m: MunicipalityData) => void;
  // A click that lands on no CALABARZON province or municipality (sea, the
  // faint non-CALABARZON provinces, Metro Manila).
  onBackgroundClick?: () => void;
  rejectedProvinceIds?: Set<string>;            // provinces with no forecast for current quarter
  // Map area covered by panels (phone layout: the search box, legend, sheet
  // and timeline), kept clear when fitting CALABARZON or a province.
  fitInsets?: { top: number; right: number; bottom: number; left: number };
  // Lowest zoom. Phones need to go further out to fit CALABARZON.
  minZoom?: number;
  // Zoom levels a fit may land on: 1 = whole levels. Phones use quarter
  // levels, so CALABARZON fills the small map instead of rounding down.
  zoomSnap?: number;
}

/** fitBounds / flyToBounds padding: 40px; on phones 12px plus whatever the panels cover. */
function fitPadding(insets?: Props["fitInsets"]): Pick<L.FitBoundsOptions, "padding" | "paddingTopLeft" | "paddingBottomRight"> {
  if (!insets) return { padding: [40, 40] };
  return { paddingTopLeft: [12 + insets.left, 12 + insets.top], paddingBottomRight: [12 + insets.right, 12 + insets.bottom] };
}

const AMBER = "hsl(35, 90%, 55%)";

type Ring = number[][];

const ringContains = (ring: Ring, lng: number, lat: number) => {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
};

// Ray-cast test against the outer rings only. Holes are ignored on purpose:
// a lake inside a province (Laguna's seven San Pablo lakes) reads as part of
// that province, not as somewhere outside it.
function outlineContains(geometry: GeoJSON.Geometry | undefined, lng: number, lat: number): boolean {
  if (!geometry) return false;
  const polygons =
    geometry.type === "Polygon" ? [geometry.coordinates]
    : geometry.type === "MultiPolygon" ? geometry.coordinates
    : [];
  return polygons.some(([outer]) => ringContains(outer, lng, lat));
}

// Basemap flavor + page-background colour per theme. "black" / "white" Protomaps
// flavors are near-monochrome (no cyan water) and match the app's dark/light
// chrome; the bg colour is the flavor's water tone so any tile-boundary is
// invisible against the container.
const BASEMAP_FLAVOR = { dark: "black", light: "white" } as const;
const BASEMAP_PAGE_BG = { dark: "#1a1a1a", light: "#dcdcdc" } as const;

// CALABARZON region overall bounds (overrides flaky polygon bounds for SW Quezon island fragments)
const CALABARZON_BOUNDS: [[number, number], [number, number]] = [[13.40, 120.20], [15.20, 122.95]];

const SVG_NS = "http://www.w3.org/2000/svg";

const hexToRgb = (hex: string) => {
  const clean = hex.replace("#", "");
  return {
    r: parseInt(clean.slice(0, 2), 16),
    g: parseInt(clean.slice(2, 4), 16),
    b: parseInt(clean.slice(4, 6), 16),
  };
};

const rgbToHex = ({ r, g, b }: { r: number; g: number; b: number }) =>
  `#${[r, g, b].map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("")}`;

const mixHex = (from: string, to: string, amount: number) => {
  const a = hexToRgb(from);
  const b = hexToRgb(to);
  return rgbToHex({
    r: a.r + (b.r - a.r) * amount,
    g: a.g + (b.g - a.g) * amount,
    b: a.b + (b.b - a.b) * amount,
  });
};


// Lakes are drawn in their province's colour, this much darker, so they read
// as part of the province but clearly not a municipality with its own score.
const LAKE_SHADE = 0.28;

// The selected city / municipality: a thick outline in the page's text colour
// (drawn as a wide stroke under the shape, whose fill hides the inner half)
// around a thin dark edge, so it reads on both light and dark maps; the
// province's other municipalities fade. No glow, shadow or animation.
const SELECTED_OUTLINE_WEIGHT = 7; // about 3px shows outside the shape
const SELECTED_INNER_EDGE = "#0D0F14";
const FADED_MUNI_OPACITY = 0.35;
// The selected province's own shape lies under its municipalities in the
// same colour: faded too while one of them is selected, or the faded
// municipalities would still look as strong as the chosen one.
const PROVINCE_FILL_WITH_MUNI = 0.1;
const MUNI_OPACITY = 0.9;
const MUNI_STROKE = "rgba(255,255,255,0.35)";

const featureOf = (layer: L.Layer) => (layer as L.Layer & { feature?: GeoJSON.Feature }).feature;

/** The page's text colour (light on the dark theme, dark on the light one). */
function foregroundColor(): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue("--foreground").trim();
  return v ? `hsl(${v.split(/\s+/).join(", ")})` : "#ffffff";
}

// The boundary file names component cities "City of Antipolo" while the API
// says "Antipolo" (and "Cavite City" for "City of Cavite"), so both sides are
// reduced to the bare place name before matching.
const muniKey = (provinceId: string, name: string) =>
  `${provinceId}::${name.toLowerCase().trim().replace(/^city of\s+/, "").replace(/\s+city$/, "")}`;

const ringDistance = (ring: Ring, lng: number, lat: number) => {
  let best = Infinity;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [ax, ay] = ring[j];
    const [bx, by] = ring[i];
    const dx = bx - ax;
    const dy = by - ay;
    const len = dx * dx + dy * dy;
    const t = len ? Math.max(0, Math.min(1, ((lng - ax) * dx + (lat - ay) * dy) / len)) : 0;
    best = Math.min(best, Math.hypot(lng - (ax + t * dx), lat - (ay + t * dy)));
  }
  return best;
};

// Where a municipality's name goes. The bounding-box centre is fine for most
// shapes, but one that wraps around water (San Nicolas around Taal Lake) has
// its centre in the lake, so those fall back to the point of the largest
// polygon that sits furthest from any edge.
function labelPoint(geometry: GeoJSON.Geometry | undefined, fallback: L.LatLng): L.LatLng {
  if (!geometry || (geometry.type !== "Polygon" && geometry.type !== "MultiPolygon")) return fallback;
  const polygons = (geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates) as Ring[][];
  const inPolygon = (rings: Ring[], lng: number, lat: number) =>
    ringContains(rings[0], lng, lat) && !rings.slice(1).some((h) => ringContains(h, lng, lat));
  if (polygons.some((rings) => inPolygon(rings, fallback.lng, fallback.lat))) return fallback;

  const extent = (rings: Ring[]) => {
    const xs = rings[0].map((c) => c[0]);
    const ys = rings[0].map((c) => c[1]);
    return { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) };
  };
  const largest = polygons.reduce((a, b) => {
    const ea = extent(a);
    const eb = extent(b);
    return (eb.maxX - eb.minX) * (eb.maxY - eb.minY) > (ea.maxX - ea.minX) * (ea.maxY - ea.minY) ? b : a;
  });
  const { minX, maxX, minY, maxY } = extent(largest);
  const steps = 24;
  let best: [number, number] | null = null;
  let bestDist = -1;
  for (let i = 1; i < steps; i++) {
    for (let j = 1; j < steps; j++) {
      const lng = minX + ((maxX - minX) * i) / steps;
      const lat = minY + ((maxY - minY) * j) / steps;
      if (!inPolygon(largest, lng, lat)) continue;
      const d = Math.min(...largest.map((r) => ringDistance(r, lng, lat)));
      if (d > bestDist) {
        bestDist = d;
        best = [lat, lng];
      }
    }
  }
  return best ? L.latLng(best[0], best[1]) : fallback;
}

export function PhilippineMap({
  regions,
  selectedRegion,
  selectedMunicipality,
  municipalities,
  onHover,
  onClick,
  onMunicipalityClick,
  onBackgroundClick,
  rejectedProvinceIds,
  fitInsets,
  minZoom = 8,
  zoomSnap = 1,
}: Props) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  // Read when a fit starts, so a fit uses the layout of that moment.
  const fitInsetsRef = useRef(fitInsets);
  fitInsetsRef.current = fitInsets;
  // The municipality the map last zoomed to (to zoom back out when cleared).
  const focusedMuniRef = useRef<string | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const provincesLayerRef = useRef<L.GeoJSON | null>(null);
  const municipalitiesLayerRef = useRef<L.GeoJSON | null>(null);
  const lakesLayerRef = useRef<L.GeoJSON | null>(null);
  const provincePulsesRef = useRef<{ marker: L.Marker; provinceId: string }[]>([]);
  const provinceLabelsRef = useRef<L.Marker[]>([]);
  const municipalityLabelsRef = useRef<L.Marker[]>([]);

  const onHoverRef = useRef(onHover);
  const onClickRef = useRef(onClick);
  const onMuniClickRef = useRef(onMunicipalityClick);
  const onBackgroundClickRef = useRef(onBackgroundClick);
  const selectedRef = useRef(selectedRegion);
  const selectedMuniRef = useRef(selectedMunicipality);
  const [isZoomed, setIsZoomed] = useState(false);
  const isZoomedRef = useRef(false);
  const muniGeoDataRef = useRef<GeoJSON.FeatureCollection | null>(null);
  // Lakes the province outline covers but no municipality does (Laguna de
  // Bay, Taal Lake), cut from the two boundary files so the edges line up.
  const lakeGeoDataRef = useRef<GeoJSON.FeatureCollection | null>(null);

  onHoverRef.current = onHover;
  onClickRef.current = onClick;
  onMuniClickRef.current = onMunicipalityClick;
  onBackgroundClickRef.current = onBackgroundClick;
  selectedRef.current = selectedRegion;
  selectedMuniRef.current = selectedMunicipality;

  const regionMap = useMemo(() => {
    const m = new Map<string, RegionData>();
    regions.forEach((r) => m.set(r.id, r));
    return m;
  }, [regions]);
  const regionMapRef = useRef(regionMap);
  regionMapRef.current = regionMap;

  const rejectedRef = useRef<Set<string>>(rejectedProvinceIds ?? new Set());
  rejectedRef.current = rejectedProvinceIds ?? new Set();

  const muniMap = useMemo(() => {
    // Map by lowercased name + province for matching against geojson "name"
    const m = new Map<string, MunicipalityData>();
    municipalities.forEach((mu) => {
      m.set(muniKey(mu.provinceId, mu.name), mu);
    });
    return m;
  }, [municipalities]);
  // Read from timers and map events, where the closure's copy may be old.
  const muniMapRef = useRef(muniMap);
  muniMapRef.current = muniMap;
  const selectedOutlineRef = useRef<L.GeoJSON | null>(null);
  const selectedLabelRef = useRef<L.Marker | null>(null);
  const selectedMuniLayerRef = useRef<L.Path | null>(null);
  const muniLabelsByKeyRef = useRef(new Map<string, L.Marker>());

  /** A municipality shape's look; `selectedId` is the chosen one in its province, if any. */
  const muniStyle = (provinceId: string, muni: MunicipalityData | undefined, selectedId: string | null): L.PathOptions => {
    const rejected = rejectedRef.current.has(provinceId);
    const fill = rejected ? NO_DATA_COLOR : muni ? (RISK_COLORS[muni.riskLevel] ?? NO_DATA_COLOR) : NO_DATA_COLOR;
    if (!rejected && muni && muni.id === selectedId) {
      return { fillColor: fill, fillOpacity: 1, color: SELECTED_INNER_EDGE, weight: 1.5, opacity: 1, lineJoin: "round", lineCap: "round" };
    }
    return { fillColor: fill, fillOpacity: selectedId && !rejected ? FADED_MUNI_OPACITY : MUNI_OPACITY, color: MUNI_STROKE, weight: 0.8, opacity: 1, lineJoin: "round", lineCap: "round" };
  };

  /** Outline, then the selected shape, above every other municipality. */
  const raiseSelectedMunicipality = () => {
    selectedOutlineRef.current?.bringToFront();
    selectedMuniLayerRef.current?.bringToFront();
  };

  const getProvinceStyle = useCallback((id: string | undefined, isSelected: boolean, isDimmed: boolean): L.PathOptions => {
    const region = id ? regionMapRef.current.get(id) : null;
    const isRejected = id ? rejectedRef.current.has(id) : false;
    if (!region || isRejected) {
      return {
        fillColor: NO_DATA_COLOR,
        fillOpacity: isDimmed ? 0.25 : isSelected ? 0.7 : 0.55,
        color: isSelected ? AMBER : "#1f2937",
        weight: isSelected ? 2.5 : 1,
      };
    }
    const fill = RISK_COLORS[region.riskLevel] ?? NO_DATA_COLOR;
    if (isDimmed) {
      return {
        fillColor: fill,
        fillOpacity: 0.25,
        color: "#1f2937",
        weight: 1,
      };
    }
    return {
      fillColor: fill,
      fillOpacity: isSelected ? 0.95 : 0.85,
      color: isSelected ? AMBER : "#1f2937",
      weight: isSelected ? 2.5 : 1,
    };
  }, []);
  const getProvinceStyleRef = useRef(getProvinceStyle);
  getProvinceStyleRef.current = getProvinceStyle;

  // Zoom to the selected city / municipality, once its shape is on the map
  // (the province's layer is built after the province zoom, so this runs
  // both when the selection changes and right after the layer is built).
  const focusSelectedMunicipality = useCallback(() => {
    const map = mapRef.current;
    const layerGroup = municipalitiesLayerRef.current;
    const sel = selectedMuniRef.current;
    if (!map || !layerGroup || !sel || focusedMuniRef.current === sel.id) return;
    let target: L.Polygon | null = null;
    layerGroup.eachLayer((layer) => {
      const name = ((layer as L.Layer & { feature?: GeoJSON.Feature }).feature?.properties?.name || "").toLowerCase();
      if (muniKey(sel.provinceId, name) === muniKey(sel.provinceId, sel.name.toLowerCase())) target = layer as L.Polygon;
    });
    if (!target) return;
    focusedMuniRef.current = sel.id;
    map.flyToBounds((target as L.Polygon).getBounds(), { ...fitPadding(fitInsetsRef.current), duration: 0.6, maxZoom: 12 });
  }, []);

  // Style every municipality for the current selection; draw the outline and
  // the bold name label of the selected one (its label even where small
  // areas' labels are left out). Cleared selection: the normal look.
  const applyMuniSelection = useCallback(() => {
    const map = mapRef.current;
    const group = municipalitiesLayerRef.current;
    selectedOutlineRef.current?.remove();
    selectedOutlineRef.current = null;
    selectedLabelRef.current?.remove();
    selectedLabelRef.current = null;
    selectedMuniLayerRef.current = null;
    muniLabelsByKeyRef.current.forEach((m) => m.setOpacity(1));
    if (!map || !group) return;

    const sel = selectedMuniRef.current;
    let selLayer: L.Polygon | null = null;
    group.eachLayer((layer) => {
      const f = featureOf(layer);
      const pid = f?.properties?.province_id as string;
      const muni = muniMapRef.current.get(muniKey(pid, (f?.properties?.name || "").toLowerCase()));
      if (sel && muni?.id === sel.id && !rejectedRef.current.has(pid)) selLayer = layer as L.Polygon;
    });
    const selectedId = selLayer ? sel!.id : null;
    group.eachLayer((layer) => {
      const f = featureOf(layer);
      const pid = f?.properties?.province_id as string;
      const muni = muniMapRef.current.get(muniKey(pid, (f?.properties?.name || "").toLowerCase()));
      (layer as L.Path).setStyle(muniStyle(pid, muni, selectedId));
    });
    const provinceId = selectedRef.current?.id;
    if (provinceId) {
      provincesLayerRef.current?.eachLayer((layer) => {
        if (featureOf(layer)?.properties?.id !== provinceId) return;
        const base = getProvinceStyleRef.current(provinceId, true, false);
        (layer as L.Path).setStyle(selectedId ? { ...base, fillOpacity: PROVINCE_FILL_WITH_MUNI } : base);
      });
    }
    if (!selLayer) return;

    const target = selLayer as L.Polygon;
    const feature = featureOf(target)!;
    selectedOutlineRef.current = L.geoJSON(feature as GeoJSON.Feature, {
      interactive: false,
      style: () => ({ color: foregroundColor(), weight: SELECTED_OUTLINE_WEIGHT, opacity: 1, fill: false, lineJoin: "round", lineCap: "round" }),
    }).addTo(map);
    selectedMuniLayerRef.current = target;
    raiseSelectedMunicipality();

    const key = muniKey(feature.properties?.province_id, (feature.properties?.name || "").toLowerCase());
    muniLabelsByKeyRef.current.get(key)?.setOpacity(0);
    const center = labelPoint(feature.geometry, target.getBounds().getCenter());
    selectedLabelRef.current = L.marker([center.lat, center.lng], {
      icon: L.divIcon({
        className: "",
        html: `<div class="map-label" data-selected-label="true" style="
          color: hsl(var(--foreground));
          font-size: 11px;
          font-weight: 700;
          text-shadow: var(--map-label-halo);
          white-space: nowrap;
          pointer-events: none;
          transform: translate(-50%, -50%);
        ">${feature.properties?.name ?? ""}</div>`,
        iconSize: [0, 0],
        iconAnchor: [0, 0],
      }),
      interactive: false,
      keyboard: false,
      zIndexOffset: 1000,
    }).addTo(map);
    // Refs carry the current selection and data.
  }, []);

  const clearMunicipalities = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    selectedOutlineRef.current?.remove();
    selectedOutlineRef.current = null;
    selectedLabelRef.current?.remove();
    selectedLabelRef.current = null;
    selectedMuniLayerRef.current = null;
    muniLabelsByKeyRef.current.clear();
    if (municipalitiesLayerRef.current) {
      map.removeLayer(municipalitiesLayerRef.current);
      municipalitiesLayerRef.current = null;
    }
    if (lakesLayerRef.current) {
      map.removeLayer(lakesLayerRef.current);
      lakesLayerRef.current = null;
    }
    map.closePopup();
    municipalityLabelsRef.current.forEach((l) => map.removeLayer(l));
    municipalityLabelsRef.current = [];
  }, []);

  const showMunicipalities = useCallback((provinceId: string) => {
    const map = mapRef.current;
    if (!map || !muniGeoDataRef.current) return;

    clearMunicipalities();

    const features = muniGeoDataRef.current.features.filter(
      (f) => f.properties?.province_id === provinceId
    );
    if (!features.length) return;

    const isProvRejected = rejectedRef.current.has(provinceId);
    const labels: L.Marker[] = [];

    // Lakes go in first so the municipalities draw over their shorelines.
    const lakes = (lakeGeoDataRef.current?.features ?? []).filter(
      (f) => f.properties?.province_id === provinceId
    );
    if (lakes.length) {
      const lakeFill = mixHex(getProvinceStyle(provinceId, true, false).fillColor as string, "#000000", LAKE_SHADE);
      lakesLayerRef.current = L.geoJSON(
        { type: "FeatureCollection", features: lakes } as GeoJSON.FeatureCollection,
        {
          style: () => ({ fillColor: lakeFill, fillOpacity: 0.95, stroke: false }),
          onEachFeature: (feature, layer) => {
            layer.bindTooltip(
              `<div style="font-size:11px"><strong>${feature.properties?.name}</strong><br/><span style="color:#9ca3af;font-style:italic">Lake · No data</span></div>`,
              { sticky: true }
            );
            layer.on("click", (e) => L.DomEvent.stopPropagation(e));
          },
        }
      ).addTo(map);
      lakes.forEach((f) => {
        const [lat, lng] = f.properties?.label as [number, number];
        labels.push(
          L.marker([lat, lng], {
            icon: L.divIcon({
              className: "",
              html: `<div class="map-label" style="
                color: hsl(var(--foreground) / 0.85);
                font-size: 11px;
                font-style: italic;
                font-weight: 600;
                letter-spacing: 0.06em;
                text-shadow: var(--map-label-halo);
                white-space: nowrap;
                pointer-events: none;
                transform: translate(-50%, -50%);
              ">${f.properties?.name}</div>`,
              iconSize: [0, 0],
              iconAnchor: [0, 0],
            }),
            interactive: false,
            keyboard: false,
          }).addTo(map)
        );
      });
    }

    const muniLayer = L.geoJSON(
      { type: "FeatureCollection", features } as GeoJSON.FeatureCollection,
      {
        // The selection's look is applied once the layer is built (applyMuniSelection).
        style: (feature) => {
          const name = (feature?.properties?.name || "").toLowerCase();
          return muniStyle(provinceId, muniMap.get(muniKey(provinceId, name)), null);
        },
        onEachFeature: (feature, layer) => {
          const name: string = feature.properties?.name || "Unknown";
          const muni = muniMap.get(muniKey(provinceId, name));
          const tipColor = muni ? RISK_COLORS[muni.riskLevel] : "#888";
          layer.bindTooltip(
            `<div style="font-size:11px">
              <strong>${name}</strong>
              ${isProvRejected
                ? `<br/><span style="color:#9ca3af;font-style:italic">No Forecast Available</span>`
                : muni ? `<br/><span style="color:${tipColor}">Risk Level ${muni.riskScore.toFixed(2)} • ${muni.riskLevel}</span>`
                : `<br/><span style="color:#9ca3af;font-style:italic">No data available</span>`}
            </div>`,
            { sticky: true }
          );
          layer.on({
            mouseover: (e) => {
              const l = e.target as L.Path;
              l.setStyle({ fillOpacity: 1, weight: 2, color: AMBER });
              l.bringToFront();
            },
            mouseout: (e) => {
              const l = e.target as L.Path;
              const current = muniMapRef.current.get(muniKey(provinceId, name.toLowerCase()));
              const sel = selectedMuniRef.current;
              const selectedId = sel && selectedMuniLayerRef.current ? sel.id : null;
              l.setStyle(muniStyle(provinceId, current, selectedId));
              raiseSelectedMunicipality();
            },
            click: (e) => {
              L.DomEvent.stopPropagation(e);
              if (muni && !isProvRejected) {
                onMuniClickRef.current(muni);
                return;
              }
              // Nothing to open in the side panel, so say so where they clicked.
              L.popup({ closeButton: false })
                .setLatLng(e.latlng)
                .setContent(
                  `<div style="font-size:12px"><strong>${name}</strong><br/><span style="color:#6b7280;font-style:italic">${
                    isProvRejected ? "No forecast available for this quarter" : "No data available"
                  }</span></div>`
                )
                .openOn(map);
            },
          });
        },
      }
    ).addTo(map);
    municipalitiesLayerRef.current = muniLayer;

    muniLayer.eachLayer((layer) => {
      const feature = (layer as any).feature as GeoJSON.Feature;
      const name = (feature?.properties?.name || "").toLowerCase();
      const muni = muniMap.get(muniKey(provinceId, name));
      const fill = isProvRejected ? NO_DATA_COLOR : muni ? (RISK_COLORS[muni.riskLevel] ?? NO_DATA_COLOR) : NO_DATA_COLOR;
      (layer as L.Path).setStyle({ fillColor: fill });
    });

    // Add muni name labels (only for larger features, capped to avoid clutter)
    let labelCount = 0;
    muniLayer.eachLayer((layer) => {
      if (labelCount >= 60) return;
      const feature = (layer as any).feature as GeoJSON.Feature;
      const name = feature?.properties?.name || "";
      if (!name) return;
      const center = labelPoint(feature.geometry, (layer as L.Polygon).getBounds().getCenter());
      const label = L.marker([center.lat, center.lng], {
          icon: L.divIcon({
            className: "",
            html: `<div class="map-label" style="
              color: hsl(var(--foreground));
              font-size: 9px;
              font-weight: 600;
              text-shadow: var(--map-label-halo);
              white-space: nowrap;
              pointer-events: none;
              transform: translate(-50%, -50%);
            ">${name}</div>`,
            iconSize: [0, 0],
            iconAnchor: [0, 0],
          }),
          interactive: false,
          keyboard: false,
        }).addTo(map);
      labels.push(label);
      muniLabelsByKeyRef.current.set(muniKey(provinceId, name.toLowerCase()), label);
      labelCount++;
    });
    municipalityLabelsRef.current = labels;
    applyMuniSelection();
    focusSelectedMunicipality();
  }, [muniMap, clearMunicipalities, getProvinceStyle, focusSelectedMunicipality, applyMuniSelection]);

  // Pulse markers + permanent name labels, one per province. Rebuildable
  // (not just run-once): province data arrives from the network, so this is
  // called both right after the map's GeoJSON loads and again whenever
  // `regions` changes -- otherwise a slow API response leaves the map
  // permanently unlabeled (built before the data needed to label it existed).
  const provinceLabelOverrides: Record<string, [number, number]> = {
    quezon: [14.05, 121.85], // Quezon's centroid is in the islands; pin to mainland
  };

  const syncProvinceMarkers = useCallback(() => {
    const map = mapRef.current;
    const provLayer = provincesLayerRef.current;
    if (!map || !provLayer) return;

    provincePulsesRef.current.forEach(({ marker }) => map.removeLayer(marker));
    provinceLabelsRef.current.forEach((l) => map.removeLayer(l));

    const pulses: { marker: L.Marker; provinceId: string }[] = [];
    const labels: L.Marker[] = [];
    provLayer.eachLayer((layer) => {
      const feature = (layer as any).feature as GeoJSON.Feature;
      const id = feature?.properties?.id;
      const region = id ? regionMapRef.current.get(id) : null;
      if (!region || !id) return;
      const isRejected = rejectedRef.current.has(id);

      const override = provinceLabelOverrides[id];
      const bounds = (layer as L.Polygon).getBounds();
      const center = override ? { lat: override[0], lng: override[1] } : bounds.getCenter();
      const color = isRejected ? NO_DATA_COLOR : RISK_COLORS[region.riskLevel];

      if (!isRejected) {
        const pulseIcon = L.divIcon({
          className: "",
          html: `<div class="pulse-marker" style="--pulse-color: ${color}">
            <div class="pulse-dot" style="background: ${color}"></div>
            <div class="pulse-ring" style="border-color: ${color}"></div>
          </div>`,
          iconSize: [20, 20],
          iconAnchor: [10, 10],
        });
        const pulse = L.marker([center.lat, center.lng], { icon: pulseIcon, interactive: false, keyboard: false }).addTo(map);
        pulses.push({ marker: pulse, provinceId: id });
      }

      const label = L.marker([center.lat, center.lng], {
        icon: L.divIcon({
          className: "",
          html: `<div class="map-label" style="
            color: hsl(var(--foreground));
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-shadow: var(--map-label-halo);
            white-space: nowrap;
            pointer-events: none;
            transform: translate(-50%, 14px);
            text-transform: uppercase;
          ">${region.name}</div>`,
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        }),
        interactive: false,
        keyboard: false,
      }).addTo(map);
      labels.push(label);
    });
    provincePulsesRef.current = pulses;
    provinceLabelsRef.current = labels;
  }, []);

  // Re-sync markers whenever province data changes (first real load, and
  // every later quarter switch, which can change risk level/colour and
  // therefore pulse colour).
  useEffect(() => {
    syncProvinceMarkers();
  }, [regions, syncProvinceMarkers]);

  // Fill colour + tooltips also need a refresh once regions data arrives,
  // for the same reason -- they're first drawn from whatever regionMap held
  // (possibly empty) at GeoJSON-load time.
  useEffect(() => {
    const provLayer = provincesLayerRef.current;
    if (!provLayer) return;
    provLayer.eachLayer((layer) => {
      const feature = (layer as any).feature as GeoJSON.Feature;
      const id = feature?.properties?.id;
      const region = id ? regionMapRef.current.get(id) : null;
      if (!region || !id) return;
      const sel = selectedRef.current?.id === id;
      const dimmed = isZoomedRef.current && !sel;
      (layer as L.Path).setStyle(getProvinceStyle(id, sel, dimmed));
      const isRej = rejectedRef.current.has(id);
      (layer as any).unbindTooltip?.();
      (layer as any).bindTooltip(
        isRej
          ? `<div style="font-size:12px"><strong>${region.name}</strong><br/><span style="color:#9ca3af;font-style:italic">No Forecast Available</span></div>`
          : `<div style="font-size:12px"><strong>${region.name}</strong><br/>Risk Level: ${region.riskScore.toFixed(2)}<br/><span style="text-transform:capitalize">${region.riskLevel} risk</span></div>`,
        { sticky: true }
      );
    });
    // The province's fade under a selected municipality (applyMuniSelection).
    applyMuniSelection();
  }, [regions, getProvinceStyle, applyMuniSelection]);

  const resetZoom = useCallback(() => {
    const map = mapRef.current;
    const provLayer = provincesLayerRef.current;
    if (!map || !provLayer) return;

    isZoomedRef.current = false;
    setIsZoomed(false);

    clearMunicipalities();

    // Re-show pulses only for non-rejected provinces
    provincePulsesRef.current.forEach(({ marker, provinceId }) => {
      if (!rejectedRef.current.has(provinceId)) marker.addTo(map);
    });

    // Reset all province styles + re-enable interactivity
    provLayer.eachLayer((layer) => {
      const feature = (layer as any).feature as GeoJSON.Feature;
      const id = feature?.properties?.id;
      (layer as L.Path).setStyle(getProvinceStyle(id, false, false));
      const el = (layer as L.Path).getElement() as SVGElement | null;
      if (el) el.style.pointerEvents = "";
    });

    map.flyToBounds(L.latLngBounds(CALABARZON_BOUNDS), { ...fitPadding(fitInsetsRef.current), duration: 0.8 });
  }, [getProvinceStyle, clearMunicipalities]);

  const zoomToProvince = useCallback((provinceId: string) => {
    const map = mapRef.current;
    const provLayer = provincesLayerRef.current;
    if (!map || !provLayer) return;

    isZoomedRef.current = true;
    setIsZoomed(true);

    // Hide all province pulses (we'll show muni layer instead)
    provincePulsesRef.current.forEach(({ marker }) => map.removeLayer(marker));

    let targetBounds: L.LatLngBounds | null = null;
    provLayer.eachLayer((layer) => {
      const feature = (layer as any).feature as GeoJSON.Feature;
      const id = feature?.properties?.id;
      const isTarget = id === provinceId;
      if (isTarget) {
        targetBounds = (layer as L.Polygon).getBounds();
        (layer as L.Path).setStyle(getProvinceStyle(id, true, false));
        (layer as L.Path).bringToFront();
      } else {
        (layer as L.Path).setStyle(getProvinceStyle(id, false, true));
      }
    });

    if (targetBounds) {
      map.flyToBounds(targetBounds, { ...fitPadding(fitInsetsRef.current), duration: 0.8, maxZoom: 11 });
      // Show municipalities after the zoom animation
      setTimeout(() => {
        showMunicipalities(provinceId);
        // Disable interactivity ONLY on the selected province so lake gaps (Taal, Laguna de Bay)
        // don't capture clicks. Other provinces remain clickable so users can switch directly.
        provLayer.eachLayer((layer) => {
          const feature = (layer as any).feature as GeoJSON.Feature;
          const id = feature?.properties?.id;
          const el = (layer as L.Path).getElement() as SVGElement | null;
          if (el) el.style.pointerEvents = id === provinceId ? "none" : "";
        });
      }, 800);
    }
  }, [getProvinceStyle, showMunicipalities]);

  // ─── Init map once ───
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [14.2, 121.4],
      zoom: 8,
      minZoom: 8,
      maxZoom: 12,
      maxBounds: [[12.8, 119.5], [15.8, 123.6]],
      maxBoundsViscosity: 1.0,
      zoomControl: false,
      attributionControl: false,
      boxZoom: false,
    });

    const onZoomIn = () => map.zoomIn();
    const onZoomOut = () => map.zoomOut();
    window.addEventListener("aipheed:zoom-in", onZoomIn);
    window.addEventListener("aipheed:zoom-out", onZoomOut);
    // Redraw at the new size whenever the map's box changes (window resized,
    // phone rotated, header or banner changing height) or the panels over it
    // change ("aipheed:map-resize"), so no grey strip is left uncovered.
    const resize = () => map.invalidateSize({ pan: false });
    const ro = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
    ro?.observe(mapContainerRef.current);
    window.addEventListener("aipheed:map-resize", resize);
    window.addEventListener("orientationchange", resize);
    (map as any).__aipheedZoomCleanup = () => {
      window.removeEventListener("aipheed:zoom-in", onZoomIn);
      window.removeEventListener("aipheed:zoom-out", onZoomOut);
      ro?.disconnect();
      window.removeEventListener("aipheed:map-resize", resize);
      window.removeEventListener("orientationchange", resize);
    };

    const isLight = () => document.documentElement.classList.contains("light");
    const applyBg = () => {
      map.getContainer().style.background = isLight() ? BASEMAP_PAGE_BG.light : BASEMAP_PAGE_BG.dark;
    };
    applyBg();

    const makeBasemap = () =>
      leafletLayer({
        url: PMTILES_URL,
        flavor: isLight() ? BASEMAP_FLAVOR.light : BASEMAP_FLAVOR.dark,
        attribution: BASEMAP_ATTRIBUTION,
      }) as unknown as L.GridLayer;

    let tile = makeBasemap().addTo(map);
    tile.on("tileerror", () => {
      if ((map as any).__basemapWarned) return;
      (map as any).__basemapWarned = true;
      console.warn(
        `[aiPHeed] Basemap tiles could not load from "${PMTILES_URL}". ` +
          "Province and municipality outlines still render on the themed background. " +
          "See docs/basemap.md to provision the .pmtiles file for this deployment.",
      );
    });

    const onTheme = () => {
      map.removeLayer(tile);
      tile = makeBasemap().addTo(map);
      applyBg();
    };
    window.addEventListener("aipheed:theme", onTheme);
    (map as any).__aipheedThemeCleanup = () => window.removeEventListener("aipheed:theme", onTheme);

    mapRef.current = map;

    // Province and municipality clicks stop propagation, so a click reaching
    // the map itself landed outside every CALABARZON shape. The one exception
    // is the selected province: its path is click-through while zoomed (see
    // zoomToProvince), so a click on its lakes or other gaps between
    // municipalities also lands here and is filtered out by outline.
    map.on("click", (e: L.LeafletMouseEvent) => {
      const selectedId = selectedRef.current?.id;
      if (!selectedId) return;
      let insideSelected = false;
      provincesLayerRef.current?.eachLayer((layer) => {
        const feature = (layer as L.Polygon).feature;
        if (feature?.properties?.id === selectedId) {
          insideSelected = outlineContains(feature.geometry, e.latlng.lng, e.latlng.lat);
        }
      });
      if (!insideSelected) onBackgroundClickRef.current?.();
    });

    // Set on unmount: the GeoJSON can arrive after the map is gone, and adding
    // layers to a removed map throws.
    let disposed = false;

    // Load provinces (filter to CALABARZON only) + municipalities
    Promise.all([
      fetch("/ph-provinces.json").then((r) => r.json()),
      fetch("/calabarzon-municities.json").then((r) => r.json()),
      fetch("/calabarzon-lakes.json").then((r) => r.json()),
    ])
      .then(([provincesGeo, muniGeo, lakeGeo]: GeoJSON.FeatureCollection[]) => {
        if (disposed) return;
        muniGeoDataRef.current = muniGeo;
        lakeGeoDataRef.current = lakeGeo;

        // Filter & re-tag provinces: use province name → our id
        const NAME_TO_ID: Record<string, string> = {
          Batangas: "batangas",
          Cavite: "cavite",
          Laguna: "laguna",
          Quezon: "quezon",
          Rizal: "rizal",
        };
        const calabarzonFeatures = provincesGeo.features
          .filter((f) => f.properties?.region_id === "r4a")
          .map((f) => ({
            ...f,
            properties: {
              ...f.properties,
              id: NAME_TO_ID[f.properties?.name] || f.properties?.name,
              name: f.properties?.name,
            },
          }));

        const provLayer = L.geoJSON(
          { type: "FeatureCollection", features: calabarzonFeatures } as GeoJSON.FeatureCollection,
          {
            style: (feature) => {
              const id = feature?.properties?.id;
              const isSel = selectedRef.current?.id === id;
              return getProvinceStyle(id, isSel, false);
            },
            onEachFeature: (feature, layer) => {
              const id = feature.properties?.id;
              // Looked up fresh on every interaction, not captured once here:
              // this layer is built as soon as the (fast, local) GeoJSON file
              // loads, which usually finishes before the (slower, network)
              // province data does. Closing over `region` at construction
              // time would freeze it at "not loaded yet" forever.
              const regionNow = () => (id ? regionMapRef.current.get(id) : undefined);

              layer.on({
                mouseover: (e) => {
                  const l = e.target as L.Path;
                  if (!isZoomedRef.current || selectedRef.current?.id === id) {
                    l.setStyle({ fillOpacity: 0.85, weight: 2.5, color: AMBER });
                    l.bringToFront();
                    if (municipalitiesLayerRef.current) municipalitiesLayerRef.current.bringToFront();
                  }
                  const region = regionNow();
                  if (region) onHoverRef.current(region);
                },
                mouseout: (e) => {
                  const l = e.target as L.Path;
                  const sel = selectedRef.current?.id === id;
                  const dimmed = isZoomedRef.current && !sel;
                  l.setStyle(getProvinceStyle(id, sel, dimmed));
                  onHoverRef.current(null);
                },
                click: (e) => {
                  L.DomEvent.stopPropagation(e);
                  const region = regionNow();
                  if (!region) return;
                  if (isZoomedRef.current && selectedRef.current?.id === id) return;
                  onClickRef.current(region);
                },
              });

              const region = regionNow();
              if (region) {
                const isRej = rejectedRef.current.has(id);
                layer.bindTooltip(
                  isRej
                    ? `<div style="font-size:12px"><strong>${region.name}</strong><br/><span style="color:#9ca3af;font-style:italic">No Forecast Available</span></div>`
                    : `<div style="font-size:12px"><strong>${region.name}</strong><br/>Risk Level: ${region.riskScore.toFixed(2)}<br/><span style="text-transform:capitalize">${region.riskLevel} risk</span></div>`,
                  { sticky: true }
                );
              }
            },
          }
        ).addTo(map);
        provincesLayerRef.current = provLayer;

        provLayer.eachLayer((layer) => {
          const feature = (layer as any).feature as GeoJSON.Feature;
          const id = feature?.properties?.id;
          const region = id ? regionMapRef.current.get(id) : null;
          if (!region) return;
          // (no texture)
          (layer as L.Path).setStyle(getProvinceStyle(id, selectedRef.current?.id === id, false));
        });

        // ── Rest of the Philippines: visible faint outlines, NOT clickable ──
        const restFeatures = provincesGeo.features.filter(
          (f) => f.properties?.region_id !== "r4a"
        );
        L.geoJSON(
          { type: "FeatureCollection", features: restFeatures } as GeoJSON.FeatureCollection,
          {
            interactive: false,
            style: () => ({
              fillColor: "#1a2230",
              fillOpacity: 0.55,
              color: "rgba(255,255,255,0.18)",
              weight: 0.6,
            }),
          }
        ).addTo(map);
        provLayer.bringToFront();

        // First attempt -- will be empty-labelled if province data hasn't
        // arrived yet; the `[regions]`-keyed effect above re-syncs once it does.
        syncProvinceMarkers();

        // Fit to CALABARZON bounds
        map.fitBounds(L.latLngBounds(CALABARZON_BOUNDS), fitPadding(fitInsetsRef.current));
      })
      .catch(console.error);

    return () => {
      disposed = true;
      (map as any).__aipheedZoomCleanup?.();
      // Without this the theme listener outlives the map: the next page's
      // header announces its theme on mount, and the stale handler adds a
      // basemap layer to the removed map ("reading 'appendChild'").
      (map as any).__aipheedThemeCleanup?.();
      // A zoom animation (e.g. the fit-to-CALABARZON once the outlines load)
      // finishes on a 250 ms timer that map.remove() does not cancel; leaving
      // the page inside that window threw "reading '_leaflet_pos'". Leaflet's
      // handler does nothing once the animation is marked finished.
      map.stop();
      (map as unknown as { _animatingZoom?: boolean })._animatingZoom = false;
      map.remove();
      mapRef.current = null;
      provincesLayerRef.current = null;
      municipalitiesLayerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.options.zoomSnap = zoomSnap;
    map.setMinZoom(minZoom);
  }, [minZoom, zoomSnap]);

  // Selection changes
  useEffect(() => {
    if (selectedRegion) {
      zoomToProvince(selectedRegion.id);
    } else {
      resetZoom();
    }
  }, [selectedRegion, zoomToProvince, resetZoom]);

  // A city / municipality picked (search or map): zoom to it. Cleared while
  // its province stays selected: back out to the province.
  useEffect(() => {
    if (selectedMunicipality) {
      focusSelectedMunicipality();
      return;
    }
    if (focusedMuniRef.current && selectedRegion) {
      focusedMuniRef.current = null;
      const map = mapRef.current;
      let bounds: L.LatLngBounds | null = null;
      provincesLayerRef.current?.eachLayer((layer) => {
        if ((layer as L.Layer & { feature?: GeoJSON.Feature }).feature?.properties?.id === selectedRegion.id) bounds = (layer as L.Polygon).getBounds();
      });
      if (map && bounds) map.flyToBounds(bounds, { ...fitPadding(fitInsetsRef.current), duration: 0.6, maxZoom: 11 });
    } else {
      focusedMuniRef.current = null;
    }
    // Only when the selection itself changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMunicipality?.id]);

  // Re-style municipalities when the selection or their data changes.
  useEffect(() => {
    if (!municipalitiesLayerRef.current) return;
    applyMuniSelection();
  }, [selectedMunicipality, selectedRegion, muniMap, rejectedProvinceIds, applyMuniSelection]);

  // The outline is in the page's text colour: redraw it when the theme changes.
  useEffect(() => {
    const onTheme = () => window.setTimeout(applyMuniSelection, 0);
    window.addEventListener("aipheed:theme", onTheme);
    return () => window.removeEventListener("aipheed:theme", onTheme);
  }, [applyMuniSelection]);

  // Apply rejection updates: re-style provinces, re-bind tooltips, hide pulses for rejected.
  useEffect(() => {
    const provLayer = provincesLayerRef.current;
    if (!provLayer) return;
    provLayer.eachLayer((layer) => {
      const feature = (layer as any).feature as GeoJSON.Feature;
      const id = feature?.properties?.id;
      if (!id) return;
      const region = regionMapRef.current.get(id);
      if (!region) return;
      const sel = selectedRef.current?.id === id;
      const dimmed = isZoomedRef.current && !sel;
      (layer as L.Path).setStyle(getProvinceStyle(id, sel, dimmed));
      const isRej = rejectedRef.current.has(id);
      (layer as any).unbindTooltip?.();
      (layer as any).bindTooltip(
        isRej
          ? `<div style="font-size:12px"><strong>${region.name}</strong><br/><span style="color:#9ca3af;font-style:italic">No Forecast Available</span></div>`
          : `<div style="font-size:12px"><strong>${region.name}</strong><br/>Risk Level: ${region.riskScore.toFixed(2)}<br/><span style="text-transform:capitalize">${region.riskLevel} risk</span></div>`,
        { sticky: true }
      );
    });
    // Toggle pulse visibility for rejected provinces
    const map = mapRef.current;
    if (map) {
      provincePulsesRef.current.forEach(({ marker, provinceId }) => {
        const el = (marker as any).getElement?.() as HTMLElement | undefined;
        if (el) el.style.display = rejectedRef.current.has(provinceId) ? "none" : "";
      });
    }
    // The province's fade under a selected municipality (applyMuniSelection).
    applyMuniSelection();
  }, [rejectedProvinceIds, getProvinceStyle, applyMuniSelection]);

  return (
    <div className="absolute inset-0 w-full h-full">
      {isZoomed && (
        <button
          onClick={() => onClick(selectedRegion!)}
          className="absolute top-14 left-1/2 -translate-x-1/2 z-[1000] surface-float border rounded-full px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary transition-colors"
        >
          ← Back to CALABARZON
        </button>
      )}
      <div ref={mapContainerRef} className="w-full h-full [&:focus]:outline-none" />
    </div>
  );
}
