// Layout breakpoints shared by components and CSS (src/index.css).

/**
 * The phone layout: upright phones, phones turned sideways and narrow
 * laptop windows. The map's side panels become one bottom sheet here.
 * Keep in step with the matching @media rule in src/index.css.
 */
export const COMPACT_QUERY = "(max-width: 767px), (max-height: 500px)";

/** Tablets and small laptops: room for one map side panel at a time. */
export const MEDIUM_QUERY = "(min-width: 768px) and (max-width: 1279px) and (min-height: 501px)";
