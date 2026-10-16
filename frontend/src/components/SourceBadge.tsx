import type { JobSummary } from "../types/api";

/** Where a listing was published and how it was retrieved. Always visible on cards and detail pages. */
export function SourceBadge({ job }: { job: Pick<JobSummary, "source_platform" | "provider_name" | "source_name" | "provider"> }) {
  const aggregated = job.provider === "jsearch";
  const title = aggregated
    ? `Published on ${job.source_platform}; found through ${job.provider_name}`
    : `Retrieved from ${job.provider_name} (${job.source_name})`;
  return (
    <span
      className="inline-flex max-w-full items-center gap-1 rounded border border-line bg-paper px-2 py-0.5 text-xs text-muted"
      title={title}
    >
      <span className="font-semibold text-ink">Source:</span>
      <span className="truncate">
        {job.source_platform}
        {aggregated ? " via JSearch" : ""}
      </span>
    </span>
  );
}
