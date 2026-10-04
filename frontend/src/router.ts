/**
 * Strand A: hash routes for the one-page app. #/ landing, #/cases, #/case/<name>, #/design, #/bench, #/validation,
 * #/schedule, plus the hidden dev route #/gallery. The older query links (?replay=, ?view=, ?demo=gallery) are
 * rewritten to their hash route once at startup, keeping other params such as ?t= and ?select=.
 */
export type Route =
  | { page: "landing" } | { page: "cases" } | { page: "case"; name: string } | { page: "design"; whatif?: string }
  | { page: "bench" } | { page: "validation" } | { page: "schedule" } | { page: "gallery" };

export function parseRoute(hash = location.hash): Route {
  const [a, b] = hash.replace(/^#\/?/, "").split("/");
  switch (a) {
    case "case": return b ? { page: "case", name: decodeURIComponent(b) } : { page: "cases" };
    case "cases": return { page: "cases" };
    case "design": return { page: "design", whatif: b ? decodeURIComponent(b) : undefined };
    case "bench": case "validation": case "schedule": case "gallery": return { page: a };
    default: return { page: "landing" };
  }
}

/** Rewrite legacy query links to hash routes (replaceState, so Back still works). */
export function migrateLegacyLinks() {
  const q = new URLSearchParams(location.search);
  let hash: string | undefined;
  const replay = q.get("replay"), view = q.get("view");
  if (replay) hash = `#/case/${encodeURIComponent(replay)}`;
  else if (view === "plan") hash = "#/schedule";
  else if (view === "bench" || view === "validation") hash = `#/${view}`;
  else if (view?.startsWith("whatif:")) hash = `#/design/${encodeURIComponent(view.slice(7))}`;
  else if (q.get("demo") === "gallery") hash = "#/gallery";
  if (!hash) return;
  for (const k of ["replay", "view", "demo"]) q.delete(k);
  const rest = q.toString();
  history.replaceState(null, "", `${location.pathname}${rest ? `?${rest}` : ""}${hash}`);
}

export const routeKey = (r: Route) => (r.page === "case" ? `case/${r.name}` : r.page);
