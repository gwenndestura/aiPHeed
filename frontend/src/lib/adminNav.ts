// src/lib/adminNav.ts
// --------------------
// The admin console's sections and their URLs, shared by the admin header and
// by the public header when an admin is signed in, so both navigate the same
// way. The URL is the source of truth for which section is showing.

export type AdminSection = "map" | "review" | "feedback";

export const ADMIN_SECTIONS: readonly { section: AdminSection; label: string; path: string }[] = [
  { section: "map", label: "Mapping", path: "/admin" },
  { section: "review", label: "Review", path: "/admin/review" },
  { section: "feedback", label: "Feedback", path: "/admin/feedback" },
];

/**
 * A signed-in admin's header links, in order -- the same in the admin header
 * and the public header, so moving between them never changes the menu.
 * Data and Visualization are the public pages; the rest are admin sections.
 */
export const ADMIN_NAV: readonly { label: string; path: string }[] = [
  { label: "Mapping", path: "/admin" },
  { label: "Data", path: "/data" },
  { label: "Visualization", path: "/visualization" },
  { label: "Review", path: "/admin/review" },
  { label: "Feedback", path: "/admin/feedback" },
];

/** A link is active when it points at the page being shown. */
export function isActivePath(pathname: string, path: string): boolean {
  return (pathname.replace(/\/+$/, "") || "/") === path;
}

export function adminPath(section: AdminSection): string {
  return ADMIN_SECTIONS.find((s) => s.section === section)!.path;
}

/** The section a pathname shows; the map for /admin and anything unrecognised. */
export function sectionFromPath(pathname: string): AdminSection {
  return ADMIN_SECTIONS.find((s) => isActivePath(pathname, s.path))?.section ?? "map";
}
