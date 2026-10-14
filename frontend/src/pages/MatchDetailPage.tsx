import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { JobDetailPanel } from "../components/JobDetailPanel";
import { MatchScore } from "../components/MatchScore";
import { SkillChip } from "../components/SkillChip";
import { ErrorState, InlineStatus, LoadingState } from "../components/States";
import { AssistantPanel } from "../features/AssistantPanel";
import { useAsync } from "../hooks/useAsync";
import { useSaveToggle } from "../hooks/useSaveToggle";
import { api } from "../services/api";
import type { MatchEvidence } from "../types/api";

function group(evidence: MatchEvidence[]) {
  const by = (k: MatchEvidence["kind"]) => evidence.filter((e) => e.kind === k);
  return {
    reasons: by("reason"),
    matched: by("matched_skill"),
    related: by("related_skill"),
    missingRequired: by("missing_required"),
    missingPreferred: by("missing_preferred"),
    experience: by("relevant_experience"),
    level: by("experience_level"),
    preferences: by("preference"),
    caveats: by("caveat"),
  };
}

export function MatchDetailPage() {
  const { matchId = "" } = useParams();
  const match = useAsync(() => api.getMatch(matchId), [matchId]);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);
  const saver = useSaveToggle((_, saved) => match.setData((prev) => prev && { ...prev, job: { ...prev.job, is_saved: saved } }));

  if (match.loading) return <LoadingState label="Loading recommendation…" />;
  if (match.error) return <ErrorState error={match.error} onRetry={match.reload} title="Couldn't load this recommendation" />;
  const m = match.data!;
  const g = group(m.evidence);
  const userSkills = new Set(g.matched.map((e) => e.label.toLowerCase()));

  async function feedback(rating: "relevant" | "not_relevant") {
    try {
      await api.sendFeedback(m.id, rating);
      match.setData((prev) => prev && { ...prev, feedback: rating });
      setFeedbackMsg("Thanks. Your feedback is saved.");
    } catch (e) {
      setFeedbackMsg(e instanceof Error ? e.message : "Couldn't save feedback.");
    }
  }

  return (
    <>
      <Link to="/app/matches" className="mb-6 inline-block text-sm">
        Back to recommendations
      </Link>
      <div className="grid gap-8 xl:grid-cols-[1fr_24rem]">
        <div className="min-w-0 space-y-8">
          <section className="panel p-6" aria-labelledby="why-heading">
            <h2 id="why-heading" className="text-lg font-semibold">
              Why this job was recommended
            </h2>
            <p className="mt-1 text-sm text-muted">CareerMatch AI analysis, ranked #{m.rank} in this run. {m.disclaimer}</p>
            <div className="mt-5 grid gap-8 lg:grid-cols-2">
              <MatchScore
                score={m.score}
                components={m.components}
                weights={m.weights}
                evidenceCoverage={m.evidence_coverage}
                variant="full"
              />
              <div className="space-y-4 text-sm">
                <ul className="space-y-2">
                  {g.reasons.map((r) => (
                    <li key={r.label}>
                      <span className="font-semibold">{r.label}:</span> {r.detail}
                    </li>
                  ))}
                </ul>
                {(g.level.length > 0 || g.preferences.length > 0) && (
                  <ul className="space-y-1 border-t border-line pt-3">
                    {(g.reasons.some((r) => r.label === m.component_labels.experience_compatibility) ? [] : g.level).map((e) => (
                      <li key={e.label}>{e.detail}</li>
                    ))}
                    {g.preferences.map((e) => (
                      <li key={e.label}>
                        <span className={e.label.startsWith("✓") ? "text-teal" : "text-amber"}>{e.label}</span>: {e.detail}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </section>

          <section className="panel p-6" aria-labelledby="evidence-heading">
            <h2 id="evidence-heading" className="text-lg font-semibold">
              Skills evidence
            </h2>
            {g.matched.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-semibold">Found in your resume</h3>
                <ul className="mt-2 space-y-1.5 text-sm">
                  {g.matched.map((e) => (
                    <li key={`${e.label}-${e.requirement}`} className="flex flex-wrap items-start gap-2">
                      <SkillChip skill={e.label} variant="matched" />
                      <span className="text-muted">
                        {e.requirement}: “{e.detail}”
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {g.related.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-semibold">Related skills (partial credit)</h3>
                <ul className="mt-2 space-y-1.5 text-sm">
                  {g.related.map((e) => (
                    <li key={e.label} className="flex flex-wrap items-start gap-2">
                      <SkillChip skill={e.label} variant="related" />
                      <span className="text-muted">{e.detail}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {(g.missingRequired.length > 0 || g.missingPreferred.length > 0) && (
              <div className="mt-4">
                <h3 className="text-sm font-semibold">Not found in your resume</h3>
                <p className="text-sm text-muted">This doesn't mean you lack these skills. If you have one, add it to your resume profile with evidence.</p>
                <ul className="mt-2 space-y-1.5 text-sm">
                  {[...g.missingRequired, ...g.missingPreferred].map((e) => (
                    <li key={`${e.kind}-${e.label}`} className="flex flex-wrap items-start gap-2">
                      <SkillChip skill={e.label} variant="missing" />
                      <span className="text-muted">
                        {e.requirement}
                        {e.detail ? `: “${e.detail}”` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {g.experience.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-semibold">Relevant experience and projects from your resume</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                  {g.experience.map((e) => (
                    <li key={e.label}>
                      {e.label} <span className="text-muted">({e.detail})</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {g.caveats.length > 0 && (
              <ul className="mt-5 space-y-2 border-t border-line pt-4 text-sm">
                {g.caveats.map((c) => (
                  <li key={c.label}>
                    <span className="font-semibold">{c.label}.</span> <span className="text-muted">{c.detail}</span>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-line pt-4 text-sm">
              <span>Was this recommendation relevant?</span>
              <button type="button" className="btn-secondary" aria-pressed={m.feedback === "relevant"} onClick={() => feedback("relevant")}>
                Relevant
              </button>
              <button type="button" className="btn-secondary" aria-pressed={m.feedback === "not_relevant"} onClick={() => feedback("not_relevant")}>
                Not relevant
              </button>
              <InlineStatus message={feedbackMsg} tone="success" />
            </div>
          </section>

          {saver.error && <InlineStatus message={saver.error} tone="error" />}
          <JobDetailPanel job={m.job} userSkills={userSkills} onToggleSave={() => saver.toggle(m.job)} saving={saver.pending === m.job.id} />
        </div>
        <aside className="xl:sticky xl:top-6 xl:self-start">
          <AssistantPanel jobId={m.job.id} />
        </aside>
      </div>
    </>
  );
}
