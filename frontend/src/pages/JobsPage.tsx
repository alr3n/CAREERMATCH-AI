import { useRef, useState, type FormEvent } from "react";
import { PageHeader } from "../components/AppShell";
import { JobCard } from "../components/JobCard";
import { JobFilters } from "../components/JobFilters";
import { EmptyState, ErrorState, InlineStatus, LoadingState } from "../components/States";
import { SourcesPanel } from "../features/SourcesPanel";
import { useAsync } from "../hooks/useAsync";
import { useSaveToggle } from "../hooks/useSaveToggle";
import { api } from "../services/api";
import type { JobFilters as Filters, RefreshItem } from "../types/api";
import { formatDate, timeAgo } from "../utils/format";

const PAGE_SIZE = 20;
export const NO_LIVE_LISTINGS = "No live job listings are currently available. Please try again later.";

/** Number of filters set beyond keyword search and sort order. */
function activeFilterCount(f: Filters): number {
  return (
    (f.company ? 1 : 0) +
    (f.location ? 1 : 0) +
    (f.employment_types?.length ?? 0) +
    (f.work_arrangements?.length ?? 0) +
    (f.experience_levels?.length ?? 0) +
    (f.categories?.length ?? 0) +
    (f.skills?.length ?? 0) +
    (f.platforms?.length ?? 0) +
    (f.salary_min ? 1 : 0) +
    (f.has_salary ? 1 : 0) +
    (f.checked_within_days ? 1 : 0) +
    (f.saved_only ? 1 : 0)
  );
}

export function JobsPage() {
  const [filters, setFilters] = useState<Filters>({ sort: "recently_checked", page: 1, page_size: PAGE_SIZE });
  const [query, setQuery] = useState({ q: "", location: "" });
  const [showFilters, setShowFilters] = useState(false);
  const [sourcesKey, setSourcesKey] = useState(0);
  // Only explicit searches are recorded in search history, not paging or sorting.
  const recordNext = useRef(false);
  const facets = useAsync(() => api.facets(), [sourcesKey]);
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

  function apply(next: Filters) {
    recordNext.current = true;
    setFilters({ ...next, page: 1, page_size: PAGE_SIZE });
  }

  function submitSearch(e: FormEvent) {
    e.preventDefault();
    apply({ ...filters, q: query.q.trim() || undefined, location: query.location.trim() || undefined });
  }

  async function refresh() {
    setRefreshing(true);
    setRefreshResult(null);
    try {
      const res = await api.refreshJobs();
      const failed = res.results.some((r) => r.status === "error" || r.status === "rate_limited");
      setRefreshResult({ message: summarise(res.results), tone: failed ? "error" : "success" });
      setSourcesKey((k) => k + 1);
      await jobs.reload();
    } catch (e) {
      setRefreshResult({ message: e instanceof Error ? e.message : "Refresh failed.", tone: "error" });
    } finally {
      setRefreshing(false);
    }
  }

  const total = jobs.data?.total ?? 0;
  const page = filters.page ?? 1;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filterCount = activeFilterCount(filters);
  const noLiveListings = facets.data?.total_active === 0;
  const lastUpdated = facets.data?.last_checked_at;

  return (
    <>
      <PageHeader
        title="Find jobs"
        description="Live listings from employers' job boards and authorised job-search APIs. Every listing links to its original posting."
        actions={
          <button type="button" className="btn-secondary w-full sm:w-auto" onClick={refresh} disabled={refreshing}>
            {refreshing ? "Checking job sources…" : "Check for new listings"}
          </button>
        }
      />
      <p className="-mt-5 mb-5 text-sm text-muted" aria-live="polite">
        {lastUpdated ? (
          <>
            Last updated <time dateTime={lastUpdated} title={formatDate(lastUpdated)}>{timeAgo(lastUpdated)}</time>
          </>
        ) : facets.loading ? (
          "Checking when listings were last updated…"
        ) : (
          "Listings have not been retrieved yet."
        )}
      </p>
      {refreshResult && <InlineStatus message={refreshResult.message} tone={refreshResult.tone} />}

      <form onSubmit={submitSearch} role="search" aria-label="Search jobs" className="panel mb-6 grid gap-3 p-4 sm:grid-cols-[1fr_14rem_auto] sm:items-end">
        <div className="min-w-0">
          <label htmlFor="search-q" className="field-label">
            Job title, keyword or company
          </label>
          <input
            id="search-q"
            type="search"
            className="field-input"
            value={query.q}
            onChange={(e) => setQuery((v) => ({ ...v, q: e.target.value }))}
            placeholder="e.g. data analyst, Grab, React"
            enterKeyHint="search"
          />
        </div>
        <div className="min-w-0">
          <label htmlFor="search-location" className="field-label">
            Location
          </label>
          <input
            id="search-location"
            className="field-input"
            list="search-locations"
            value={query.location}
            onChange={(e) => setQuery((v) => ({ ...v, location: e.target.value }))}
            placeholder="e.g. Taguig, Cebu"
          />
          <datalist id="search-locations">
            {facets.data?.locations.map((l) => <option key={l.value} value={l.value} />)}
          </datalist>
        </div>
        <button type="submit" className="btn-primary">
          Search
        </button>
      </form>

      {/* One DOM order for every screen size: filters, results, sources. On large
          screens the grid places filters and sources in the sidebar. */}
      <div className="grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)] lg:grid-rows-[auto_1fr] lg:gap-x-8">
        <div className="min-w-0 space-y-4 lg:col-start-1 lg:row-start-1">
          <button
            type="button"
            className="btn-secondary w-full lg:hidden"
            aria-expanded={showFilters}
            aria-controls="job-filters"
            onClick={() => setShowFilters((v) => !v)}
          >
            {showFilters ? "Hide filters" : "Show filters"}
            {filterCount > 0 && <span className="num rounded-full bg-teal px-2 text-xs text-white">{filterCount}</span>}
          </button>
          <div id="job-filters" className={`${showFilters ? "block" : "hidden"} lg:block`}>
            <JobFilters
              key={JSON.stringify({ q: filters.q, location: filters.location })}
              value={filters}
              facets={facets.data}
              showSearch={false}
              onApply={(f) => {
                apply({ ...f, q: filters.q, location: f.location ?? filters.location });
                setQuery((v) => ({ ...v, location: f.location ?? "" }));
                setShowFilters(false);
              }}
            />
          </div>
        </div>
        <section aria-labelledby="results-heading" aria-busy={jobs.loading} className="min-w-0 lg:col-start-2 lg:row-span-2 lg:row-start-1">
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
            <LoadingState label="Loading live listings…" />
          ) : jobs.error ? (
            <ErrorState title="Listings could not be loaded" error={jobs.error} onRetry={jobs.reload} />
          ) : jobs.data && jobs.data.items.length === 0 ? (
            noLiveListings ? (
              <EmptyState
                title={NO_LIVE_LISTINGS}
                action={
                  <button type="button" className="btn-secondary" onClick={refresh} disabled={refreshing}>
                    Check job sources again
                  </button>
                }
              >
                CareerMatch only shows real postings retrieved from the job sources below — it never fills the page with sample jobs.
              </EmptyState>
            ) : (
              <EmptyState
                title="No listings match your search"
                action={
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      setQuery({ q: "", location: "" });
                      apply({ sort: filters.sort });
                    }}
                  >
                    Clear search and filters
                  </button>
                }
              >
                Try fewer keywords or remove a filter.
              </EmptyState>
            )
          ) : (
            <div className="space-y-4">
              {jobs.data?.items.map((job) => (
                <JobCard key={job.id} job={job} detailHref={`/app/jobs/${job.id}`} onToggleSave={saver.toggle} saving={saver.pending === job.id} />
              ))}
            </div>
          )}
          {pages > 1 && (
            <nav aria-label="Pagination" className="mt-6 flex flex-wrap items-center justify-between gap-3 sm:justify-start">
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
        <div className="min-w-0 lg:col-start-1 lg:row-start-2 lg:self-start">
          <SourcesPanel reloadKey={sourcesKey} />
        </div>
      </div>
    </>
  );
}

function summarise(results: RefreshItem[]): string {
  if (results.length === 0) return "No job sources are configured.";
  const ok = results.filter((r) => r.status === "ok");
  const created = ok.reduce((n, r) => n + r.created, 0);
  const closed = ok.reduce((n, r) => n + r.expired, 0);
  const skipped = results.filter((r) => r.status === "skipped_cooldown").length;
  const failed = results.filter((r) => r.status === "error" || r.status === "rate_limited");
  const parts = [`${ok.length} source${ok.length === 1 ? "" : "s"} checked: ${created} new, ${closed} closed`];
  if (skipped) parts.push(`${skipped} checked recently and skipped`);
  if (failed.length) parts.push(`unavailable: ${failed.map((r) => `${r.identifier} (${r.message ?? r.status})`).join(", ")}`);
  return parts.join(". ") + ".";
}
