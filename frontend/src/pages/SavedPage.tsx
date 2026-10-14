import { Link } from "react-router-dom";
import { PageHeader } from "../components/AppShell";
import { JobCard } from "../components/JobCard";
import { EmptyState, ErrorState, InlineStatus, LoadingState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { useSaveToggle } from "../hooks/useSaveToggle";
import { api } from "../services/api";

export function SavedPage() {
  const saved = useAsync(() => api.listSaved(1, 100), []);
  const saver = useSaveToggle((id, isSaved) => {
    if (!isSaved) saved.setData((prev) => prev && { ...prev, total: prev.total - 1, items: prev.items.filter((s) => s.job.id !== id) });
  });

  return (
    <>
      <PageHeader title="Saved jobs" description="Opportunities you saved for later. Removing one doesn't affect your recommendations." />
      {saver.error && <InlineStatus message={saver.error} tone="error" />}
      {saved.loading ? (
        <LoadingState label="Loading saved jobs…" />
      ) : saved.error ? (
        <ErrorState error={saved.error} onRetry={saved.reload} />
      ) : saved.data!.items.length === 0 ? (
        <EmptyState title="No saved jobs yet" action={<Link to="/app/matches" className="btn-primary no-underline">See recommendations</Link>}>
          Select “Save” on any job to keep it here.
        </EmptyState>
      ) : (
        <div className="space-y-4">
          {saved.data!.items.map((s) => (
            <JobCard key={s.id} job={s.job} detailHref={`/app/jobs/${s.job.id}`} onToggleSave={saver.toggle} saving={saver.pending === s.job.id} />
          ))}
        </div>
      )}
    </>
  );
}
