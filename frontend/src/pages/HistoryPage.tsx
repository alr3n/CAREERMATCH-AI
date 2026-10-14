import { Link } from "react-router-dom";
import { PageHeader } from "../components/AppShell";
import { ConfirmationDialog } from "../components/ConfirmationDialog";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { HistoryEntry } from "../types/api";
import { formatDate } from "../utils/format";

function describe(entry: HistoryEntry): string {
  const q = entry.query as Record<string, unknown>;
  if (entry.kind === "match") {
    const preset = String(q.preset ?? "balanced").replace(/_/g, " ");
    const filters = q.filters as Record<string, string[]> | undefined;
    const parts = [`Matching (${preset})`];
    if (filters?.employment_types?.length) parts.push(filters.employment_types.join(", ").replace(/_/g, "-"));
    if (filters?.work_arrangements?.length) parts.push(filters.work_arrangements.join(", "));
    return parts.join(", ");
  }
  const parts: string[] = [];
  if (q.q) parts.push(`“${q.q}”`);
  for (const key of ["employment_types", "work_arrangements", "experience_levels", "categories", "skills"]) {
    const v = q[key] as string[] | undefined;
    if (v?.length) parts.push(v.join(", ").replace(/_/g, "-"));
  }
  if (q.location) parts.push(`in ${q.location}`);
  if (q.salary_min) parts.push(`salary ≥ ${q.salary_min}`);
  return parts.length ? `Search: ${parts.join(", ")}` : "Search: all listings";
}

export function HistoryPage() {
  const history = useAsync(() => api.history(1, 100), []);
  return (
    <>
      <PageHeader
        title="Search history"
        description="Your searches and matching runs. Only filters and keywords are kept — never resume content."
        actions={
          history.data && history.data.total > 0 ? (
            <ConfirmationDialog
              trigger={
                <button type="button" className="btn-secondary">
                  Clear history
                </button>
              }
              title="Clear your search history?"
              description="This removes the list of past searches. Your recommendations and saved jobs stay."
              confirmLabel="Clear history"
              onConfirm={async () => {
                await api.clearHistory();
                await history.reload();
              }}
            />
          ) : undefined
        }
      />
      {history.loading ? (
        <LoadingState />
      ) : history.error ? (
        <ErrorState error={history.error} onRetry={history.reload} />
      ) : history.data!.items.length === 0 ? (
        <EmptyState title="No searches yet">Searches from Find jobs and matching runs from Recommended jobs appear here.</EmptyState>
      ) : (
        <table className="panel w-full overflow-hidden text-sm">
          <thead className="bg-paper text-left text-muted">
            <tr>
              <th className="px-4 py-2 font-normal">When</th>
              <th className="px-4 py-2 font-normal">What</th>
              <th className="px-4 py-2 text-right font-normal">Results</th>
            </tr>
          </thead>
          <tbody>
            {history.data!.items.map((h) => (
              <tr key={h.id} className="border-t border-line">
                <td className="whitespace-nowrap px-4 py-2 text-muted">{formatDate(h.created_at)}</td>
                <td className="px-4 py-2">
                  {describe(h)}
                  {h.kind === "match" && h.run_id && (
                    <>
                      {" "}
                      <Link to="/app/matches" className="text-xs">
                        view latest
                      </Link>
                    </>
                  )}
                </td>
                <td className="num px-4 py-2 text-right">{h.result_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
