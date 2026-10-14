import { Link, useParams } from "react-router-dom";
import { JobDetailPanel } from "../components/JobDetailPanel";
import { ErrorState, InlineStatus, LoadingState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { useSaveToggle } from "../hooks/useSaveToggle";
import { api } from "../services/api";

export function JobDetailPage() {
  const { jobId = "" } = useParams();
  const job = useAsync(() => api.getJob(jobId), [jobId]);
  const skills = useAsync(async () => {
    const list = await api.listResumes();
    const active = list.find((r) => r.is_active);
    if (!active) return null;
    const resume = await api.getResume(active.id);
    return new Set(resume.skills.map((s) => s.skill.toLowerCase()));
  }, []);
  const saver = useSaveToggle((_, saved) => job.setData((prev) => prev && { ...prev, is_saved: saved }));

  if (job.loading) return <LoadingState label="Loading job…" />;
  if (job.error) return <ErrorState error={job.error} onRetry={job.reload} title="Couldn't load this job" />;
  const data = job.data!;
  return (
    <>
      <Link to="/app/jobs" className="mb-6 inline-block text-sm">
        Back to all jobs
      </Link>
      {saver.error && <InlineStatus message={saver.error} tone="error" />}
      <JobDetailPanel job={data} userSkills={skills.data ?? undefined} onToggleSave={() => saver.toggle(data)} saving={saver.pending === data.id} />
    </>
  );
}
