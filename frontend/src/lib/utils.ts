import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// The type scale in tailwind.config.ts (text-label/body/emphasis/key) is
// registered as font sizes, so cn() does not mistake them for text colours
// and drop them next to a colour class such as text-ink-secondary.
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [{ text: ["label", "body", "emphasis", "key"] }],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
