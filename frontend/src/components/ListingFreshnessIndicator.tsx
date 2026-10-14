import type { Freshness } from "../types/api";
import { formatDate, timeAgo } from "../utils/format";

const DOT: Record<Freshness, string> = { fresh: "bg-teal", recent: "bg-teal-soft", stale: "bg-amber" };

export function ListingFreshnessIndicator({ lastChecked, freshness }: { lastChecked: string; freshness: Freshness }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted" title={`Last checked ${formatDate(lastChecked)}`}>
      <span className={`h-2 w-2 rounded-full ${DOT[freshness]}`} aria-hidden="true" />
      Checked {timeAgo(lastChecked)}
      {freshness === "stale" && <span className="font-semibold text-amber"> (may have closed)</span>}
    </span>
  );
}
