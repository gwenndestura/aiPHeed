import { Menu } from "lucide-react";
import { SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";

/**
 * The menu sheet: floating 12px in from the screen's edges, with large
 * rounded corners and the dialog shadow. Its items scroll inside it when the
 * screen is short (a phone held sideways); a footer can stay at the bottom.
 */
export const MENU_SHEET_CLASS =
  "w-[280px] [--surface-base:var(--card)] inset-y-3 right-3 h-auto rounded-sheet border-0 z-[1100] flex flex-col gap-0 p-0";

/** The menu sheet's header: an icon tile in the amber tint, the title and what the menu holds. */
export function MenuSheetHeader({ title }: { title: string }) {
  return (
    <SheetHeader className="shrink-0 px-5 pt-5 pr-12 flex-row items-center gap-3 space-y-0 text-left sm:text-left">
      <span aria-hidden className="tint-primary h-10 w-10 rounded-xl flex items-center justify-center shrink-0">
        <Menu className="h-4 w-4" />
      </span>
      <span className="min-w-0">
        <SheetTitle className="text-[14px] leading-5">{title}</SheetTitle>
        <SheetDescription className="text-[11px] leading-4 text-foreground/70">Pages, display and help</SheetDescription>
      </span>
    </SheetHeader>
  );
}

/** A group of menu items: a flat rounded card with a small title. */
export function MenuSection({ heading, className = "", title, children }: { heading: string; className?: string; title?: string; children: React.ReactNode }) {
  return (
    <section className={`inner-card p-1.5 ${className}`} title={title}>
      <p className="px-2 pt-1 pb-0.5 text-[11px] font-semibold text-foreground/70">{heading}</p>
      {children}
    </section>
  );
}
