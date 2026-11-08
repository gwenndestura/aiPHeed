import { cn } from "@/lib/utils";

interface Props {
  children: React.ReactNode;
  /** Lead-in word; "Note" by default. Pass null for none. */
  label?: string | null;
  /** A 2px neutral rule on the left, square-cornered. */
  bordered?: boolean;
  className?: string;
}

/** A note or disclaimer in plain secondary text: no icon, no bold mid-sentence. */
export function Note({ children, label = "Note", bordered = true, className }: Props) {
  return (
    <p
      className={cn(
        "text-label text-ink-secondary",
        bordered && "border-l-2 border-line-strong pl-2.5",
        className,
      )}
    >
      {label && `${label}: `}
      {children}
    </p>
  );
}
