// src/lib/driverCopy.ts
// -----------------------
// Plain-language copy for the five real driver categories the backend
// computes. The technical thesis terms (Market/Prices, Climate Stress,
// Fisheries production, Employment, OFW Remittance, plus poverty, news and the
// regional hunger indicator) stay exactly as-is in
// DRIVER_GROUP_LABELS on the backend and in the glossary -- this is a
// friendlier presentation of the same key + direction for the general
// public dashboard, not a different value or a different computation.

import type { Trigger, TriggerStatus } from "./apiTypes";

interface Copy {
  title: string;
  description: string;
}

/**
 * One plain sentence per group and direction: what the group's data did, in
 * everyday words. The same for the region and a province.
 */
const PLAIN_SENTENCE: Record<string, { raises: string; lowers: string }> = {
  employment: {
    raises: "Unemployment rose more than usual compared with a year earlier.",
    lowers: "Unemployment changed less than usual compared with a year earlier.",
  },
  climate: {
    raises: "Weather and farm-supply conditions were worse than usual.",
    lowers: "Weather and farm-supply conditions were better than usual.",
  },
  market: {
    raises: "Food prices were higher than usual.",
    lowers: "Food prices were lower than usual.",
  },
  fish_kill: {
    raises: "Fisheries production fell more than usual.",
    lowers: "Fisheries production held up better than usual.",
  },
  ofw_remittance: {
    raises: "Money sent home by OFWs grew less than usual.",
    lowers: "Money sent home by OFWs grew more than usual.",
  },
  poverty: {
    raises: "The province's poverty and density profile pushed the estimate up.",
    lowers: "The province's poverty and density profile pulled the estimate down.",
  },
  news: {
    raises: "Food-stress news signals pushed the estimate up.",
    lowers: "Food-stress news signals pulled the estimate down.",
  },
  hunger_indicator: {
    raises: "The regional hunger outlook pushed the food-price estimate up.",
    lowers: "The regional hunger outlook pulled the food-price estimate down.",
  },
};

// E42: a direction is only stated for a group that actually moved the forecast. A group with no model input, no
// official data, or no measurable effect gets neutral copy that says exactly that (previously a 0% climate group read
// "Weather is hurting food supply").
const FRIENDLY_NAME: Record<string, string> = {
  market: "Food prices",
  climate: "Weather and farm supply",
  fish_kill: "Fisheries production",
  employment: "Jobs and livelihoods",
  ofw_remittance: "OFW remittances",
  poverty: "Poverty and vulnerability",
  news: "News signals",
  hunger_indicator: "Regional hunger (indicator)",
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
    description: "No official data series is available for this factor; this is not a sign of low risk.",
  }),
  insufficient_data: (name) => ({
    title: `${name}: insufficient data`,
    description: "No published data were available when this forecast was issued; this is not a sign of low risk.",
  }),
  not_recorded: (name) => ({
    title: `${name}: not recorded for this quarter`,
    description: "Factor contributions are recorded only for the issued forecast, not for past quarters.",
  }),
};

/** True when the group moved the forecast, so a direction may be stated. */
export function isContributing(t: Pick<Trigger, "status" | "pct">): boolean {
  return t.status ? t.status === "contributes" : t.pct > 0;
}

/**
 * A factor card's copy: the group's plain name and one plain sentence. The
 * section heading (pushing up / pulling down) already gives the direction, so
 * the title does not repeat it. The backend's evidence note is not shown.
 */
export function driverCopy(t: Pick<Trigger, "key" | "direction" | "status" | "pct" | "plainEvidence">): Copy {
  const name = FRIENDLY_NAME[t.key] ?? t.key;
  if (!isContributing(t)) {
    const status: Exclude<TriggerStatus, "contributes"> =
      t.status && t.status !== "contributes" ? t.status : "no_effect";
    return NEUTRAL_COPY[status](name);
  }
  // E87: when the backend sends the measured values behind the group, say them; otherwise the generic sentence
  if (t.plainEvidence) return { title: name, description: t.plainEvidence };
  const sentence = PLAIN_SENTENCE[t.key];
  return {
    title: name,
    description: sentence ? (t.direction === "protective" ? sentence.lowers : sentence.raises) : "",
  };
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
