import type { Config } from "tailwindcss";
import plugin from "tailwindcss/plugin";

export default {
  darkMode: ["class"],
  content: ["./pages/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        surface: "hsl(var(--surface))",
        "surface-hover": "hsl(var(--surface-hover))",
        risk: {
          low: {
            DEFAULT: "hsl(var(--risk-low))",
            bg: "hsl(var(--risk-low-bg))",
            text: "hsl(var(--risk-low-text))",
            border: "hsl(var(--risk-low-border))",
          },
          moderate: {
            DEFAULT: "hsl(var(--risk-moderate))",
            bg: "hsl(var(--risk-moderate-bg))",
            text: "hsl(var(--risk-moderate-text))",
            border: "hsl(var(--risk-moderate-border))",
          },
          high: {
            DEFAULT: "hsl(var(--risk-high))",
            bg: "hsl(var(--risk-high-bg))",
            text: "hsl(var(--risk-high-text))",
            border: "hsl(var(--risk-high-border))",
          },
          severe: "hsl(var(--risk-severe))",
        },
        // Status components (index.css): neutral text and borders, review
        // statuses, and values whose colour carries meaning.
        ink: {
          DEFAULT: "hsl(var(--text-primary))",
          secondary: "hsl(var(--text-secondary))",
          muted: "hsl(var(--text-muted))",
        },
        line: {
          DEFAULT: "hsl(var(--border-subtle))",
          strong: "hsl(var(--border-strong))",
        },
        status: {
          "positive-bg": "hsl(var(--status-positive-bg))",
          "positive-text": "hsl(var(--status-positive-text))",
          "positive-border": "hsl(var(--status-positive-border))",
          "neutral-bg": "hsl(var(--status-neutral-bg))",
          "neutral-text": "hsl(var(--status-neutral-text))",
          "neutral-border": "hsl(var(--status-neutral-border))",
        },
        value: {
          danger: "hsl(var(--value-danger))",
          success: "hsl(var(--value-success))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
      },
      // Corner and shadow scales from the tokens in index.css.
      borderRadius: {
        none: "0",
        sm: "var(--radius-sm)",
        DEFAULT: "var(--radius-sm)",
        md: "var(--radius-control)",
        lg: "var(--radius-panel)",
        xl: "var(--radius-panel)",
        "2xl": "var(--radius-sheet)",
        "3xl": "var(--radius-sheet)",
        full: "9999px",
        control: "var(--radius-control)",
        panel: "var(--radius-panel)",
        sheet: "var(--radius-sheet)",
        pill: "var(--radius-pill)",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        DEFAULT: "var(--shadow-control)",
        md: "var(--shadow-control)",
        lg: "var(--shadow-float)",
        xl: "var(--shadow-float)",
        "2xl": "var(--shadow-dialog)",
        control: "var(--shadow-control)",
        float: "var(--shadow-float)",
        dialog: "var(--shadow-dialog)",
      },
      fontFamily: {
        sans: ['Sora', 'system-ui', 'sans-serif'],
        mono: ['"DM Mono"', 'ui-monospace', 'monospace'],
      },
      // Type scale for the status components: labels, body, emphasis, key figures.
      fontSize: {
        label: ["12px", "16px"],
        body: ["14px", "20px"],
        emphasis: ["16px", "24px"],
        key: ["22px", "28px"],
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
    // The phone layout (lib/breakpoints.ts COMPACT_QUERY), e.g. `compact:min-h-11`.
    // A variant, not a `screens` entry: a raw media query among the screens
    // turns off Tailwind's max-* variants (max-lg:) everywhere.
    plugin(({ addVariant }) => addVariant("compact", "@media (max-width: 767px), (max-height: 500px)")),
  ],
} satisfies Config;
