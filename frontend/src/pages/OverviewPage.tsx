import { Link } from "react-router-dom";
import { PageHeader } from "../components/AppShell";
import { ErrorState, LoadingState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";
import { STAGE_LABEL, formatDate, timeAgo } from "../utils/format";

const RELEVANT_THRESHOLD = 50;

export function OverviewPage() {
  const { profile } = useAuth();
  const state = useAsync(async () => {
    const [facets, matches, saved, history, resumes] = await Promise.all([
      api.facets(),
      api.listMatches({ page_size: 100 }),
      api.listSaved(1, 1),
      api.history(1, 1),
      api.listResumes(),
    ]);
    const active = resumes.find((r) => r.is_active);
    const resume = active ? await api.getResume(active.id) : null;
    return { facets, matches, saved, history, resume };
  }, []);

  if (state.loading || !profile) return <LoadingState label="Loading your overview…" />;
  if (state.error) return <ErrorState error={state.error} onRetry={state.reload} />;
  const { facets, matches, saved, history, resume } = state.data!;
  const relevant = matches.items.filter((m) => m.score >= RELEVANT_THRESHOLD).length;
  const p = profile.profile;

  const stats = [
    {
      label: "Open listings",
      value: facets.total_active,
      note: facets.platforms.length ? `from ${facets.platforms.map((p) => p.value).slice(0, 3).join(", ")}${facets.platforms.length > 3 ? " and more" : ""}` : "no live listings yet",
    },
    { label: "Relevant to you", value: matches.run_id ? relevant : "–", note: matches.run_id ? `scored ${RELEVANT_THRESHOLD}+ in your latest run` : "run matching to see this" },
    { label: "Saved jobs", value: saved.total, note: "kept for later" },
    { label: "Last search", value: history.items[0] ? timeAgo(history.items[0].created_at) : "–", note: history.items[0] ? formatDate(history.items[0].created_at) : "no searches yet" },
  ];

  return (
    <>
      <PageHeader title="Overview" description="Where you are and what to do next." />

      {!resume && (
        <div className="panel mb-8 flex flex-col gap-3 p-6 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Start by uploading your resume</h2>
            <p className="text-muted">Recommendations and skill-gap analysis are based on it.</p>
          </div>
          <Link to="/app/resume" className="btn-primary no-underline">
            Upload resume
          </Link>
        </div>
      )}

      <dl className="mb-10 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line md:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="bg-surface p-5">
            <dt className="text-sm text-muted">{s.label}</dt>
            <dd className="num mt-1 text-2xl font-bold">{s.value}</dd>
            <dd className="mt-1 text-xs text-muted">{s.note}</dd>
          </div>
        ))}
      </dl>

      <div className="grid gap-8 lg:grid-cols-[1.4fr_1fr]">
        <section aria-labelledby="recent-heading">
          <div className="flex items-baseline justify-between">
            <h2 id="recent-heading" className="text-lg font-semibold">
              Recent recommendations
            </h2>
            <Link to="/app/matches" className="text-sm">
              See all
            </Link>
          </div>
          {matches.items.length === 0 ? (
            <p className="mt-3 text-muted">
              No recommendations yet.{" "}
              {resume ? <Link to="/app/matches">Generate matches</Link> : "Upload a resume first."}
            </p>
          ) : (
            <ol className="mt-3 divide-y divide-line border-y border-line">
              {matches.items.slice(0, 5).map((m) => (
                <li key={m.id} className="flex items-center gap-4 py-3">
                  <span className="num w-10 text-right text-xl font-bold text-teal">{Math.round(m.score)}</span>
                  <div className="min-w-0">
                    <Link to={`/app/matches/${m.id}`} className="block truncate font-semibold text-ink no-underline hover:text-teal">
                      {m.job.title}
                    </Link>
                    <p className="truncate text-sm text-muted">
                      {m.job.company}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section aria-labelledby="profile-heading" className="space-y-6">
          <div className="panel p-5">
            <h2 id="profile-heading" className="text-lg font-semibold">
              Your profile
            </h2>
            {resume ? (
              <ul className="mt-2 space-y-1 text-sm">
                <li>{resume.skills.length} skills, {resume.experience.length} experience entries, {resume.projects.length} projects</li>
                {resume.education[0] && <li>{[resume.education[0].degree, resume.education[0].institution].filter(Boolean).join(", ")}</li>}
                <li>Career stage: {p.career_stage ? STAGE_LABEL[p.career_stage] : "not set"}</li>
                {p.preferred_titles.length > 0 && <li>Targeting: {p.preferred_titles.join(", ")}</li>}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-muted">No resume uploaded.</p>
            )}
          </div>
          <div className="panel p-5">
            <div className="flex items-baseline justify-between">
              <h2 className="text-lg font-semibold">Profile completeness</h2>
              <span className="num text-xl font-bold">{profile.completeness}%</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-sm bg-paper" role="progressbar" aria-valuenow={profile.completeness} aria-valuemin={0} aria-valuemax={100} aria-label="Profile completeness">
              <div className="h-full bg-teal" style={{ width: `${profile.completeness}%` }} />
            </div>
            <ul className="mt-4 space-y-1.5 text-sm">
              {profile.completeness_items.map((item) => (
                <li key={item.key} className={item.done ? "text-muted line-through decoration-line" : ""}>
                  <span aria-hidden="true">{item.done ? "✓ " : "○ "}</span>
                  {item.label}
                  <span className="sr-only">{item.done ? " (done)" : " (to do)"}</span>
                </li>
              ))}
            </ul>
            <Link to="/app/preferences" className="mt-4 inline-block text-sm">
              Update preferences
            </Link>
          </div>
        </section>
      </div>
    </>
  );
}
