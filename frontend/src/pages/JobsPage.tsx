import { useRef, useState } from "react";
import { PageHeader } from "../components/AppShell";
import { JobCard } from "../components/JobCard";
import { JobFilters } from "../components/JobFilters";
import { EmptyState, ErrorState, InlineStatus, LoadingState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { useSaveToggle } from "../hooks/useSaveToggle";
import { api } from "../services/api";
import type { JobFilters as Filters, RefreshItem } from "../types/api";
import { timeAgo } from "../utils/format";
import { SourcesPanel } from "../features/SourcesPanel";

const PAGE_SIZE = 20;

export function JobsPage() {
  const [filters, setFilters] = useState<Filters>({ include_demo: true, sort: "recently_checked", page: 1, page_size: PAGE_SIZE });
  // Only explicit searches (Apply filters) are recorded in search history, not paging or sorting.
  const recordNext = useRef(false);
  const facets = useAsync(() => api.facets(), []);
  const jobs = useAsync(() => {
    const record = recordNext.current;
    recordNext.current = false;
    return record ? api.searchJobs(filters) : api.listJobs(filters);
  }, [filters]);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshResult, setRefreshResult] = useState<{ message: string; tone: "success" | "error" } | null>(null);
  const saver = useSaveToggle((id, saved) =>
    jobs.setData((prev) => prev && { ...prev, items: prev.items.map((j) => (j.id === id ? { ...j, is_saved: saved } : j)) }),
  );

  async function refresh() {
    setRefreshing(true);
    setRefreshResult(null);
    try {
      const res = await api.refreshJobs();
      setRefreshResult({ message: summarise(res.results), tone: res.results.some((r) => r.status === "error") ? "error" : "success" });
      await Promise.all([facets.reload(), jobs.reload()]);
    } catch (e) {
      setRefreshResult({ message: e instanceof Error ? e.message : "Refresh failed.", tone: "error" });
    } finally {
      setRefreshing(false);
    }
  }

  const total = jobs.data?.total ?? 0;
  const page = filters.page ?? 1;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <PageHeader
        title="Find jobs"
        description={
          facets.data?.last_checked_at
            ? `Listings stored from configured job boards. Last checked ${timeAgo(facets.data.last_checked_at)}.`
            : "Listings stored from configured job boards."
        }
        actions={
          <button type="button" className="btn-secondary" onClick={refresh} disabled={refreshing}>
            {refreshing ? "Checking job boards…" : "Check for new listings"}
          </button>
        }
      />
      {refreshResult && <InlineStatus message={refreshResult.message} tone={refreshResult.tone} />}
      <div className="grid gap-8 lg:grid-cols-[18rem_1fr]">
        <div className="space-y-6">
          <JobFilters
            value={filters}
            facets={facets.data}
            onApply={(f) => {
              recordNext.current = true;
              setFilters({ ...f, page_size: PAGE_SIZE });
            }}
          />
          <SourcesPanel />
        </div>
        <section aria-labelledby="results-heading" aria-busy={jobs.loading}>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 id="results-heading" className="num text-lg font-semibold">
              {jobs.loading ? "Searching…" : `${total} listing${total === 1 ? "" : "s"}`}
            </h2>
            <label className="flex items-center gap-2 text-sm">
              Sort by
              <select
                className="field-input w-auto py-1"
                value={filters.sort}
                onChange={(e) => setFilters({ ...filters, sort: e.target.value as Filters["sort"], page: 1 })}
              >
                <option value="recently_checked">Recently checked</option>
                <option value="posted">Recently posted</option>
                <option value="title">Title</option>
              </select>
            </label>
          </div>
          {saver.error && <InlineStatus message={saver.error} tone="error" />}
          {jobs.loading && !jobs.data ? (
            <LoadingState label="Loading listings…" />
          ) : jobs.error ? (
            <ErrorState error={jobs.error} onRetry={jobs.reload} />
          ) : jobs.data && jobs.data.items.length === 0 ? (
            <EmptyState title="No listings match these filters">
              Try removing a filter. If no job boards are configured yet, an administrator can add Greenhouse or Lever company boards — see the
              source list on this page.
            </EmptyState>
          ) : (
            <div className="space-y-4">
              {jobs.data?.items.map((job) => (
                <JobCard key={job.id} job={job} detailHref={`/app/jobs/${job.id}`} onToggleSave={saver.toggle} saving={saver.pending === job.id} />
              ))}
            </div>
          )}
          {pages > 1 && (
            <nav aria-label="Pagination" className="mt-6 flex items-center gap-3">
              <button type="button" className="btn-secondary" disabled={page <= 1} onClick={() => setFilters({ ...filters, page: page - 1 })}>
                Previous
              </button>
              <span className="num text-sm text-muted">
                Page {page} of {pages}
              </span>
              <button type="button" className="btn-secondary" disabled={page >= pages} onClick={() => setFilters({ ...filters, page: page + 1 })}>
                Next
              </button>
            </nav>
          )}
        </section>
      </div>
    </>
  );
}

function summarise(results: RefreshItem[]): string {
  if (results.length === 0) return "No job sources are configured.";
  return results
    .map((r) => {
      const name = r.provider === "demo" ? "Demo listings" : `${r.provider} ${r.identifier}`;
      if (r.status === "ok") return `${name}: ${r.fetched} checked, ${r.created} new, ${r.expired} closed`;
      if (r.status === "skipped_cooldown") return `${name}: checked recently, skipped`;
      return `${name}: ${r.message ?? r.status}`;
    })
    .join(". ");
}
