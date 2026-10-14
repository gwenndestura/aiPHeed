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

export function adminPath(section: AdminSection): string {
  return ADMIN_SECTIONS.find((s) => s.section === section)!.path;
}

/** The section a pathname shows; the map for /admin and anything unrecognised. */
export function sectionFromPath(pathname: string): AdminSection {
  const path = pathname.replace(/\/+$/, "") || "/";
  return ADMIN_SECTIONS.find((s) => s.path === path)?.section ?? "map";
}
