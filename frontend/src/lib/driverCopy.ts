// src/lib/driverCopy.ts
// -----------------------
// Plain-language copy for the five real driver categories the backend
// computes. The technical thesis terms (Market/Prices, Climate Stress,
// Fish Kill, Employment, OFW Remittance) stay exactly as-is in
// DRIVER_GROUP_LABELS on the backend and in the glossary -- this is a
// friendlier presentation of the same key + direction for the general
// public dashboard, not a different value or a different computation.

import type { Trigger, TriggerStatus } from "./apiTypes";

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

// E42: a direction is only stated for a group that actually moved the forecast. A group with no model input, no
// official data, or no measurable effect gets neutral copy that says exactly that (previously a 0% climate group read
// "Weather is hurting food supply").
const FRIENDLY_NAME: Record<string, string> = {
  market: "Food prices",
  climate: "Weather and farm supply",
  fish_kill: "Fish kills and fisheries",
  employment: "Jobs and livelihoods",
  ofw_remittance: "OFW remittances",
};

const NEUTRAL_COPY: Record<Exclude<TriggerStatus, "contributes">, (name: string) => Copy> = {
  no_effect: (name) => ({
    title: `${name}: no measurable effect`,
    description: "This factor is in the model but did not move this quarter's score.",
  }),
  data_not_in_model: (name) => ({
    title: `${name}: data shown, not in the model`,
    description: "Official data exist and are shown as evidence, but the model does not use them for this score.",
  }),
  stale: (name) => ({
    title: `${name}: data out of date`,
    description: "The latest official figure is more than two quarters old, so it says little about this quarter.",
  }),
  no_model_input: (name) => ({
    title: `${name}: not used in this forecast`,
    description: "The current model has no input for this factor, so it neither raised nor lowered the score.",
  }),
  no_data: (name) => ({
    title: `${name}: no official data`,
    description: "No official data series is available for this factor. Missing data is not a sign of low risk.",
  }),
};

/** True when the group moved the forecast, so a direction may be stated. */
export function isContributing(t: Pick<Trigger, "status" | "pct">): boolean {
  return t.status ? t.status === "contributes" : t.pct > 0;
}

export function driverCopy(t: Pick<Trigger, "key" | "direction" | "status" | "pct">): Copy {
  const entry = DRIVER_COPY[t.key];
  if (!isContributing(t)) {
    const status: Exclude<TriggerStatus, "contributes"> =
      t.status && t.status !== "contributes" ? t.status : "no_effect";
    return NEUTRAL_COPY[status](FRIENDLY_NAME[t.key] ?? t.key);
  }
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
