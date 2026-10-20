// Exports for the Visualization page (Trend and SHAP tabs).
//
// PNG: captureLightFigure() rasterises the on-screen chart in the light theme
// on white, regardless of what the user is viewing.
//
// PDF: renderReportPdf() lays out the report the backend composes at
// GET /api/v1/report/data. Every finding, number and sentence comes from that
// payload; this file adds none. Charts are drawn as vectors from the payload's
// data, so the printed figure carries exactly the numbers in the tables.
//
// jsPDF's built-in Helvetica has no glyphs for typographic dashes, curly quotes
// or most accented letters, so every string goes through toAscii() first.

import html2canvas from "html2canvas";
import jsPDF from "jspdf";

const FOLD: Record<string, string> = {
  "\u2012": "-", "\u2013": "-", "\u2014": "-", "\u2212": "-",
  "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
  "\u00b7": "-", "\u2026": "...", "\u00a0": " ",
};

/** Fold typographic characters to ASCII and drop anything else non-printable. */
export function toAscii(text: string): string {
  return text
    .replace(/[\u2012-\u2014\u2212\u2018\u2019\u201c\u201d\u00b7\u2026\u00a0]/g, (c) => FOLD[c] ?? "")
    .normalize("NFKD")
    .replace(/[^ -~]/g, "");
}

export const quarterLabel = (id: string) => id.replace("-", " ");

// ---------------------------------------------------------------------------
// Figure capture
// ---------------------------------------------------------------------------

const CSS_VAR = /var\(--([\w-]+)\)/g;
const SVG_COLOR_ATTRS = ["fill", "stroke", "stop-color", "color"];

/**
 * Rasterise a chart node in the light theme on a white background.
 *
 * The theme switch happens on html2canvas's cloned document, never on the
 * live page, so the user's theme does not change or flicker. Recharts writes
 * colours such as `hsl(var(--muted-foreground))` into SVG attributes; html2canvas
 * draws SVG as a detached image where those variables are undefined, so they
 * are resolved against the cloned (light) root first. HTML parts of the chart
 * (the legend) carry literal series colours and need no resolving.
 */
export async function captureLightFigure(node: HTMLElement): Promise<HTMLCanvasElement> {
  return html2canvas(node, {
    backgroundColor: "#ffffff",
    scale: 3,
    useCORS: true,
    onclone: (doc, clone) => {
      const root = doc.documentElement;
      root.classList.remove("dark");
      root.classList.add("light");
      clone.style.background = "#ffffff";

      clone.querySelectorAll<HTMLElement>(".recharts-tooltip-wrapper").forEach((el) => {
        el.style.display = "none";
      });

      const vars = doc.defaultView?.getComputedStyle(root);
      if (!vars) return;
      const resolve = (value: string) =>
        value.replace(CSS_VAR, (_, name: string) => vars.getPropertyValue(`--${name}`).trim() || "0 0% 0%");

      // html2canvas also copies each element's computed style from the live
      // (possibly dark) page into the clone's inline style, which outranks
      // the attribute -- so the resolved colour is written to both.
      clone.querySelectorAll<SVGElement>("svg, svg *").forEach((el) => {
        for (const attr of SVG_COLOR_ATTRS) {
          const v = el.getAttribute(attr);
          if (!v?.includes("var(")) continue;
          const color = resolve(v);
          el.setAttribute(attr, color);
          el.style.setProperty(attr, color);
        }
      });
      // A <tspan> carries no colour attribute of its own, only that copied
      // dark-theme inline fill; make it take its <text>'s resolved colour.
      clone.querySelectorAll<SVGElement>("svg tspan").forEach((el) => {
        el.style.setProperty("fill", "inherit");
        el.style.setProperty("stroke", "inherit");
      });
      // Room below the legend, which otherwise sits flush on the edge.
      clone.style.paddingBottom = "12px";
    },
  });
}

// ---------------------------------------------------------------------------
// Report payload (GET /api/v1/report/data)
// ---------------------------------------------------------------------------
//
// The backend composes every finding, number and sentence; this file only lays
// the blocks out. Tables and figures follow APA 7: a bold label line ("Table 1"),
// an italic title line, the table or figure, then an optional "Note." below.

export interface LineChart {
  type: "line";
  quarters: string[];
  series: { name: string; values: (number | null)[] }[];
  yMin: number;
  yMax: number;
  yStep: number;
  lines: { value: number; label: string }[];
}

export interface BarChart {
  type: "bars";
  bars: { label: string; pct: number; direction: "increases_risk" | "protective"; unmeasured?: boolean }[];
}

export type ReportBlock =
  | { kind: "heading"; level: number; text: string }
  | { kind: "paragraph"; style?: string; text: string }
  | { kind: "bullets"; items: string[] }
  | {
      kind: "table";
      label: string;
      title: string;
      columns: { label: string; align: "left" | "right" | "center"; width: number }[];
      rows: string[][];
      note: string | null;
    }
  | { kind: "figure"; label: string; title: string; chart: LineChart | BarChart; note: string | null };

export interface ReportPayload {
  type: "trend" | "shap";
  title: string;
  subtitle: string;
  generatedDate: string;
  metadata: [string, string][];
  blocks: ReportBlock[];
}

// ---------------------------------------------------------------------------
// Layout constants (A4 portrait, points)
// ---------------------------------------------------------------------------

const MARGIN_X = 56;
const MARGIN_TOP = 56;
const MARGIN_BOTTOM = 64;
const INK = 20;
const MUTED = 90;
const RULE = 190;
const BODY = 10;
const LH = 1.42;

// Series colours match the on-screen chart; each series also gets its own
// marker and dash pattern so the figure still reads in grayscale.
const SERIES_COLORS: Record<string, string> = {
  Cavite: "#4F46E5",
  Laguna: "#15803D",
  Batangas: "#B45309",
  Rizal: "#0E7490",
  Quezon: "#B91C1C",
};
const FALLBACK_COLORS = ["#374151", "#6B7280", "#7C3AED", "#BE185D"];
const DASHES: number[][] = [[], [6, 3], [1.5, 2], [7, 2.5, 1.5, 2.5], [10, 4]];
const MARKERS = ["circle", "square", "triangle", "diamond", "cross"] as const;
const BAR_RAISE = "#C0392B";
const BAR_LOWER = "#2E7D5B";
const ALERT_COLOR = "#B42318";
const HIGH_COLOR = "#B54708";

const hex = (c: string): [number, number, number] => [
  parseInt(c.slice(1, 3), 16),
  parseInt(c.slice(3, 5), 16),
  parseInt(c.slice(5, 7), 16),
];

// ---------------------------------------------------------------------------
// Renderer
// ---------------------------------------------------------------------------

export function renderReportPdf(report: ReportPayload): jsPDF {
  const pdf = new jsPDF({ orientation: "portrait", unit: "pt", format: "a4", compress: true });
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  const contentW = pageW - MARGIN_X * 2;
  const bottom = pageH - MARGIN_BOTTOM;
  let y = MARGIN_TOP;

  const newPage = () => {
    pdf.addPage();
    y = MARGIN_TOP;
  };
  const ensure = (h: number) => {
    if (y + h > bottom) newPage();
  };
  const font = (size: number, style: "normal" | "bold" | "italic" = "normal", color = INK) => {
    pdf.setFont("helvetica", style);
    pdf.setFontSize(size);
    pdf.setTextColor(color);
  };
  const wrap = (text: string, width: number): string[] => pdf.splitTextToSize(toAscii(text), width) as string[];
  const hline = (weight: number, gray = INK) => {
    pdf.setDrawColor(gray);
    pdf.setLineWidth(weight);
    pdf.line(MARGIN_X, y, pageW - MARGIN_X, y);
  };

  /** One wrapped line stretched to `width` by widening the spaces between words (justified text). */
  const justifyLine = (ln: string, x: number, baseline: number, width: number) => {
    const words = ln.trim().split(/\s+/);
    const used = words.reduce((s, w) => s + pdf.getTextWidth(w), 0);
    const gap = words.length > 1 ? (width - used) / (words.length - 1) : 0;
    // a line far shorter than the width (e.g. before a long unbreakable word) stays left-aligned
    if (words.length < 2 || gap > pdf.getTextWidth(" ") * 4) {
      pdf.text(ln, x, baseline);
      return;
    }
    let cx = x;
    for (const w of words) {
      pdf.text(w, cx, baseline);
      cx += pdf.getTextWidth(w) + gap;
    }
  };

  /** Wrapped lines, breaking pages between lines; `justify` spreads every line but the last to the full width. */
  const lines = (text: string, size: number, style: "normal" | "bold" | "italic" = "normal",
                 color = INK, indent = 0, after = 6, justify = false) => {
    font(size, style, color);
    const lh = size * LH;
    const ls = wrap(text, contentW - indent);
    ls.forEach((ln, k) => {
      ensure(lh);
      if (justify && k < ls.length - 1) justifyLine(ln, MARGIN_X + indent, y + size, contentW - indent);
      else pdf.text(ln, MARGIN_X + indent, y + size);
      y += lh;
    });
    y += after;
  };

  /** APA note: "Note." in italics, the rest in normal text, wrapped together. */
  const note = (text: string) => {
    const size = 9;
    const lh = size * LH;
    font(size, "italic", MUTED);
    const lead = "Note. ";
    const leadW = pdf.getTextWidth(lead);
    font(size, "normal", MUTED);
    const firstWidth = contentW - leadW;
    const words = toAscii(text).split(" ");
    const out: string[] = [];
    let cur = "";
    let width = firstWidth;
    for (const w of words) {
      const next = cur ? `${cur} ${w}` : w;
      if (pdf.getTextWidth(next) > width && cur) {
        out.push(cur);
        cur = w;
        width = contentW;
      } else {
        cur = next;
      }
    }
    if (cur) out.push(cur);
    out.forEach((ln, i) => {
      ensure(lh);
      if (i === 0) {
        font(size, "italic", MUTED);
        pdf.text(lead.trim(), MARGIN_X, y + size);
        font(size, "normal", MUTED);
        pdf.text(ln, MARGIN_X + leadW, y + size);
      } else {
        pdf.text(ln, MARGIN_X, y + size);
      }
      y += lh;
    });
    y += 4;
  };

  /** Height of an APA label + title. */
  const labelTitleHeight = (title: string) => {
    font(10, "italic");
    return 10 * LH + wrap(title, contentW).length * 10 * LH + 4;
  };
  const labelTitle = (label: string, title: string) => {
    lines(label, 10, "bold", INK, 0, 0);
    lines(title, 10, "italic", INK, 0, 4);
  };

  // Space the start of a block needs, so a heading is never stranded.
  const leadHeight = (idx: number): number => {
    const b = report.blocks[idx];
    if (!b) return 0;
    switch (b.kind) {
      case "paragraph": {
        font(BODY);
        const n = wrap(b.text, contentW).length;
        const next = report.blocks[idx + 1];
        // A heading over a short lead-in must also clear the table or figure after it.
        if (next && (next.kind === "table" || next.kind === "figure") && n <= 2) {
          return n * BODY * LH + 7 + leadHeight(idx + 1);
        }
        return Math.min(n, 3) * BODY * LH;
      }
      case "bullets":
        font(BODY);
        return Math.min(wrap(b.items[0] ?? "", contentW - 14).length, 3) * BODY * LH;
      case "table":
        return labelTitleHeight(b.title) + 60;
      case "figure":
        return labelTitleHeight(b.title) + figureHeight(b.chart);
      default:
        return 30;
    }
  };

  // ---- Title and details
  lines(report.title, 17, "bold", INK, 0, 0);
  lines(report.subtitle, 12, "normal", MUTED, 0, 8);
  hline(0.6, RULE);
  y += 12;
  const labelW = 92;
  for (const [label, value] of report.metadata) {
    font(9.5);
    const vals = wrap(value, contentW - labelW);
    font(9.5, "bold", MUTED);
    pdf.text(toAscii(label), MARGIN_X, y + 9.5);
    font(9.5, "normal", INK);
    vals.forEach((ln, i) => pdf.text(ln, MARGIN_X + labelW, y + 9.5 + i * 13.5));
    y += vals.length * 13.5 + 2;
  }
  y += 6;
  hline(0.6, RULE);
  y += 12;

  // ---- Blocks
  report.blocks.forEach((b, i) => {
    switch (b.kind) {
      case "heading":
        ensure(14 + 13 * LH + leadHeight(i + 1));
        if (y > MARGIN_TOP) y += 10;
        lines(b.text, 13, "bold", INK, 0, 3);
        break;
      case "paragraph": {
        // A short lead-in stays on the same page as the table or figure it introduces.
        const next = report.blocks[i + 1];
        font(BODY);
        const paraLines = wrap(b.text, contentW).length;
        if (next && (next.kind === "table" || next.kind === "figure") && paraLines <= 2) {
          ensure(paraLines * BODY * LH + 7 + leadHeight(i + 1));
        }
        lines(b.text, BODY, "normal", INK, 0, 7, true);
        break;
      }
      case "bullets":
        for (const item of b.items) {
          font(BODY);
          const ls = wrap(item, contentW - 14);
          const lh = BODY * LH;
          ensure(Math.min(ls.length, 2) * lh);
          ls.forEach((ln, k) => {
            ensure(lh);
            font(BODY);
            if (k === 0) pdf.text("-", MARGIN_X + 3, y + BODY);
            if (k < ls.length - 1) justifyLine(ln, MARGIN_X + 14, y + BODY, contentW - 14);
            else pdf.text(ln, MARGIN_X + 14, y + BODY);
            y += lh;
          });
          y += 3;
        }
        y += 4;
        break;
      case "table":
        drawTable(b);
        break;
      case "figure":
        drawFigure(b);
        break;
    }
  });

  // ---- Footer on every page
  const footer = toAscii(`aiPHeed | Generated ${report.generatedDate}`);
  const total = pdf.getNumberOfPages();
  for (let p = 1; p <= total; p++) {
    pdf.setPage(p);
    const fy = pageH - 36;
    pdf.setDrawColor(RULE);
    pdf.setLineWidth(0.5);
    pdf.line(MARGIN_X, fy - 12, pageW - MARGIN_X, fy - 12);
    font(8.5, "normal", MUTED);
    pdf.text(footer, MARGIN_X, fy);
    pdf.text(`Page ${p} of ${total}`, pageW - MARGIN_X, fy, { align: "right" });
  }
  return pdf;

  // ---------------------------------------------------------------------
  // APA tables: three horizontal rules only, bold centred headers, header
  // repeated with "Table X (continued)" after a page break, no row split.
  // ---------------------------------------------------------------------
  function drawTable(t: Extract<ReportBlock, { kind: "table" }>) {
    const size = 9;
    const lh = size * 1.32;
    const pad = 4;
    const widths = t.columns.map((c) => c.width * contentW);
    const wrapCells = (cells: string[], bold: boolean) => {
      font(size, bold ? "bold" : "normal");
      return cells.map((c, k) => wrap(c, widths[k] - pad * 2));
    };
    const height = (w: string[][]) => Math.max(...w.map((c) => c.length)) * lh + pad * 2;
    const header = wrapCells(t.columns.map((c) => c.label), true);
    const headerH = height(header);
    const rows = t.rows.map((r) => wrapCells(r, false));

    const drawCells = (wrapped: string[][], bold: boolean) => {
      font(size, bold ? "bold" : "normal", INK);
      let x = MARGIN_X;
      wrapped.forEach((cell, k) => {
        const align = bold ? "center" : t.columns[k].align;
        const tx = align === "right" ? x + widths[k] - pad : align === "center" ? x + widths[k] / 2 : x + pad;
        cell.forEach((ln, j) => pdf.text(ln, tx, y + pad + size + j * lh - 1.5, { align }));
        x += widths[k];
      });
      y += height(wrapped);
    };
    const drawHeader = () => {
      hline(0.9);
      drawCells(header, true);
      hline(0.6);
      y += 1;
    };

    ensure(labelTitleHeight(t.title) + headerH + (rows[0] ? height(rows[0]) : 0) + 4);
    labelTitle(t.label, t.title);
    drawHeader();
    for (const r of rows) {
      if (y + height(r) + 2 > bottom) {
        hline(0.9);
        newPage();
        lines(`${t.label} (continued)`, 10, "bold", INK, 0, 4);
        drawHeader();
      }
      drawCells(r, false);
    }
    hline(0.9);
    y += 5;
    if (t.note) note(t.note);
    y += 8;
  }

  // ---------------------------------------------------------------------
  // APA figures: label and title above, note below, all kept together.
  // ---------------------------------------------------------------------
  function figureHeight(chart: LineChart | BarChart): number {
    return chart.type === "line" ? 222 : 22 + chart.bars.length * 26;
  }

  function drawFigure(f: Extract<ReportBlock, { kind: "figure" }>) {
    const h = figureHeight(f.chart);
    font(9);
    const noteH = f.note ? wrap(`Note. ${f.note}`, contentW).length * 9 * LH + 4 : 0;
    ensure(labelTitleHeight(f.title) + h + noteH + 10);
    labelTitle(f.label, f.title);
    if (f.chart.type === "line") drawLine(f.chart, MARGIN_X, y, contentW, h);
    else drawBars(f.chart, MARGIN_X, y, contentW, h);
    y += h + 6;
    if (f.note) note(f.note);
    y += 8;
  }

  function marker(kind: (typeof MARKERS)[number], cx: number, cy: number, r: number) {
    switch (kind) {
      case "circle":
        pdf.circle(cx, cy, r, "FD");
        break;
      case "square":
        pdf.rect(cx - r, cy - r, r * 2, r * 2, "FD");
        break;
      case "triangle":
        pdf.triangle(cx, cy - r * 1.2, cx - r * 1.1, cy + r * 0.8, cx + r * 1.1, cy + r * 0.8, "FD");
        break;
      case "diamond":
        pdf.lines([[r * 1.2, r * 1.2], [-r * 1.2, r * 1.2], [-r * 1.2, -r * 1.2], [r * 1.2, -r * 1.2]],
                  cx, cy - r * 1.2, [1, 1], "FD", true);
        break;
      case "cross":
        pdf.setLineWidth(1.2);
        pdf.line(cx - r, cy - r, cx + r, cy + r);
        pdf.line(cx - r, cy + r, cx + r, cy - r);
        break;
    }
  }

  function drawLine(c: LineChart, x0: number, y0: number, w: number, h: number) {
    const left = x0 + 46;
    const right = x0 + w - 16;
    const top = y0 + 10;
    const legendH = 30;
    const base = y0 + h - legendH - 22;
    const span = c.yMax - c.yMin || 1;
    const yOf = (v: number) => base - ((v - c.yMin) / span) * (base - top);
    const step = (right - left) / Math.max(c.quarters.length, 1);
    const xOf = (i: number) => left + step * (i + 0.5);

    font(7.5, "normal", 70);
    for (let v = c.yMin; v <= c.yMax + 1e-9; v += c.yStep) {
      const yy = yOf(v);
      pdf.setDrawColor(228);
      pdf.setLineWidth(0.4);
      pdf.line(left, yy, right, yy);
      pdf.text(v.toFixed(2), left - 5, yy + 2.5, { align: "right" });
    }
    pdf.setDrawColor(110);
    pdf.setLineWidth(0.7);
    pdf.line(left, top, left, base);
    pdf.line(left, base, right, base);
    c.quarters.forEach((q, i) => pdf.text(q, xOf(i), base + 11, { align: "center" }));
    pdf.text("Risk score", x0 + 12, (top + base) / 2 + 18, { angle: 90 });

    for (const ln of c.lines) {
      const col = ln.label.toLowerCase().startsWith("alert") ? ALERT_COLOR : HIGH_COLOR;
      pdf.setDrawColor(...hex(col));
      pdf.setLineWidth(0.8);
      pdf.setLineDashPattern([4, 3], 0);
      pdf.line(left, yOf(ln.value), right, yOf(ln.value));
      pdf.setLineDashPattern([], 0);
      font(7, "normal", 0);
      pdf.setTextColor(...hex(col));
      pdf.text(toAscii(ln.label), right - 2, yOf(ln.value) - 3, { align: "right" });
    }

    c.series.forEach((s, k) => {
      const col = hex(SERIES_COLORS[s.name] ?? FALLBACK_COLORS[k % FALLBACK_COLORS.length]);
      pdf.setDrawColor(...col);
      pdf.setLineWidth(1.4);
      pdf.setLineDashPattern(DASHES[k % DASHES.length], 0);
      for (let i = 1; i < s.values.length; i++) {
        const a = s.values[i - 1];
        const b = s.values[i];
        if (a == null || b == null) continue;
        pdf.line(xOf(i - 1), yOf(a), xOf(i), yOf(b));
      }
      pdf.setLineDashPattern([], 0);
      s.values.forEach((v, i) => {
        if (v == null) return;
        pdf.setDrawColor(...col);
        pdf.setFillColor(255, 255, 255);
        pdf.setLineWidth(1.1);
        marker(MARKERS[k % MARKERS.length], xOf(i), yOf(v), 2.6);
      });
    });

    font(8, "normal", INK);
    const itemW = Math.min(150, (w - 24) / Math.max(c.series.length, 1));
    const rowY = y0 + h - legendH / 2 - 4;
    let lx = x0 + (w - itemW * c.series.length) / 2;
    c.series.forEach((s, k) => {
      const col = hex(SERIES_COLORS[s.name] ?? FALLBACK_COLORS[k % FALLBACK_COLORS.length]);
      pdf.setDrawColor(...col);
      pdf.setLineWidth(1.4);
      pdf.setLineDashPattern(DASHES[k % DASHES.length], 0);
      pdf.line(lx, rowY, lx + 22, rowY);
      pdf.setLineDashPattern([], 0);
      pdf.setFillColor(255, 255, 255);
      pdf.setLineWidth(1.1);
      marker(MARKERS[k % MARKERS.length], lx + 11, rowY, 2.6);
      font(8, "normal", INK);
      wrap(s.name, itemW - 30).forEach((ln, j) => pdf.text(ln, lx + 27, rowY + 3 + j * 9));
      lx += itemW;
    });
  }

  function drawBars(c: BarChart, x0: number, y0: number, w: number, h: number) {
    const labelW = 130;
    const left = x0 + labelW;
    const right = x0 + w - 96;
    const top = y0 + 4;
    const base = y0 + h - 18;
    const xOf = (p: number) => left + (p / 100) * (right - left);
    const band = (base - top) / Math.max(c.bars.length, 1);

    font(7.5, "normal", 70);
    for (let p = 0; p <= 100; p += 20) {
      pdf.setDrawColor(232);
      pdf.setLineWidth(0.4);
      pdf.line(xOf(p), top, xOf(p), base);
      pdf.text(`${p}%`, xOf(p), base + 10, { align: "center" });
    }
    pdf.setDrawColor(110);
    pdf.setLineWidth(0.7);
    pdf.line(left, top, left, base);
    pdf.line(left, base, right, base);

    c.bars.forEach((b, i) => {
      const cy = top + band * (i + 0.5);
      const bh = Math.min(15, band * 0.6);
      if (b.pct > 0) {
        pdf.setFillColor(...hex(b.direction === "increases_risk" ? BAR_RAISE : BAR_LOWER));
        pdf.rect(left, cy - bh / 2, xOf(b.pct) - left, bh, "F");
      }
      font(8.5, "normal", INK);
      pdf.text(toAscii(b.label), left - 6, cy + 3, { align: "right" });
      font(8, "normal", 60);
      const text = b.unmeasured ? "not yet measured"
        : b.pct === 0 ? "0%, no noticeable effect"
        : `${b.pct}%, ${b.direction === "increases_risk" ? "raises" : "lowers"} risk`;
      pdf.text(text, xOf(b.pct) + 4, cy + 3);
    });
  }
}
