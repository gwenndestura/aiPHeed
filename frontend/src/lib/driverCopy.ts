// src/lib/driverCopy.ts
// -----------------------
// Plain-language copy for the five real driver categories the backend
// computes. The technical thesis terms (Market/Prices, Climate Stress,
// Fish Kill, Employment, OFW Remittance) stay exactly as-is in
// DRIVER_GROUP_LABELS on the backend and in the glossary -- this is a
// friendlier presentation of the same key + direction for the general
// public dashboard, not a different value or a different computation.

import type { Trigger } from "./apiTypes";

interface Copy {
  title: string;
  description: string;
}

const DRIVER_COPY: Record<string, { risk: Copy; protective: Copy }> = {
  market: {
    risk: {
      title: "Food and rice prices are too high",
      description: "Rice, vegetables, and meat cost more than usual this quarter.",
    },
    protective: {
      title: "Food and rice prices are stable",
      description: "Rice, vegetables, and meat are priced close to normal this quarter.",
    },
  },
  climate: {
    risk: {
      title: "Weather is hurting food supply",
      description: "Typhoons or heavy rain damaged farms and disrupted food supply.",
    },
    protective: {
      title: "Weather has been calm",
      description: "No major storms or flooding disrupted farms this quarter.",
    },
  },
  fish_kill: {
    risk: {
      title: "Fish kills are being reported",
      description: "News reports point to fish die-offs affecting local fisheries.",
    },
    protective: {
      title: "No major fish kill reports",
      description: "Local news has few or no reports of fish die-offs this quarter.",
    },
  },
  employment: {
    risk: {
      title: "Fewer people have jobs",
      description: "Job rates dropped this quarter, making it harder for families to afford food.",
    },
    protective: {
      title: "More people are employed",
      description: "Job rates are stable this quarter, helping families afford food.",
    },
  },
  ofw_remittance: {
    risk: {
      title: "OFW money sent home is dropping",
      description: "Families are receiving less money from relatives working abroad.",
    },
    protective: {
      title: "OFW money sent home is steady",
      description: "Money from relatives working abroad is holding steady or rising.",
    },
  },
};

export function driverCopy(t: Pick<Trigger, "key" | "direction">): Copy {
  const entry = DRIVER_COPY[t.key];
  if (!entry) return { title: t.key, description: "" };
  return t.direction === "protective" ? entry.protective : entry.risk;
}

// Plain labels for the news-topic breakdown (NewsArticlesCardBody). Same real
// topic keys/counts/percentages from the backend's TOPIC_MAP -- just shorter,
// non-technical display text.
export const TOPIC_FRIENDLY_LABELS: Record<string, string> = {
  food_prices: "Food prices",
  crop_damage: "Crop damage",
  food_assistance: "Food assistance",
  hunger_nutrition: "Hunger & nutrition",
  ofw: "OFW & remittances",
  fishkill: "Fish kill",
  displacement: "Typhoon & disaster",
  unrest: "Unrest & strikes",
  logistics: "Transport issues",
  poverty: "Workers & poverty",
  unclassified: "Other",
};
