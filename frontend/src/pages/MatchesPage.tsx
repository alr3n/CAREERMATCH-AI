import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/AppShell";
import { CheckboxGroup } from "../components/CheckboxGroup";
import { JobCard } from "../components/JobCard";
import { EmptyState, ErrorState, InlineStatus, LoadingState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { useAuth } from "../hooks/useAuth";
import { useSaveToggle } from "../hooks/useSaveToggle";
import { api } from "../services/api";
import type { ComponentKey, MatchPage, MatchRequest, Weights } from "../types/api";
import { COMPONENT_ORDER, COMPONENT_SHORT, formatDate } from "../utils/format";

type Preset = "balanced" | "skills_first" | "preferences_first" | "custom";
type SortKey = "score" | "checked" | "title";

const PRESETS: { value: Preset; label: string; help: string }[] = [
  { value: "balanced", label: "Balanced", help: "The default weights." },
  { value: "skills_first", label: "Skills first", help: "Puts the most weight on required and preferred skills." },
  { value: "preferences_first", label: "Preferences first", help: "Puts more weight on arrangement, location, type and target roles." },
  { value: "custom", label: "Custom", help: "Set your own priorities." },
];

const DEFAULT_CUSTOM: Record<ComponentKey, number> = {
  semantic_similarity: 3,
  required_skill_coverage: 3,
  preferred_skill_coverage: 1,
  experience_compatibility: 1,
  preference_compatibility: 1,
  profile_relevance: 1,
};

export function MatchesPage() {
  const { profile } = useAuth();
  const matches = useAsync<MatchPage>(() => api.listMatches({ page_size: 100 }), []);
  const [preset, setPreset] = useState<Preset>("balanced");
  const [custom, setCustom] = useState(DEFAULT_CUSTOM);
  const [types, setTypes] = useState<string[]>([]);
  const [arrangements, setArrangements] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("score");
  const [minScore, setMinScore] = useState(0);
  const saver = useSaveToggle((id, saved) =>
    matches.setData(
      (prev) => prev && { ...prev, items: prev.items.map((m) => (m.job.id === id ? { ...m, job: { ...m.job, is_saved: saved } } : m)) },
    ),
  );

  async function run() {
    setRunning(true);
    setRunError(null);
    const body: MatchRequest = {
      preset: preset === "custom" ? "balanced" : preset,
      weights: preset === "custom" ? custom : null,
      filters: { employment_types: types, work_arrangements: arrangements, include_demo: true },
      limit: 50,
    };
    try {
      await api.runMatches(body);
      await matches.reload();
    } catch (e) {
      setRunError(e instanceof Error ? e.message : "Matching failed.");
    } finally {
      setRunning(false);
    }
  }

  const items = useMemo(() => {
    const list = (matches.data?.items ?? []).filter((m) => m.score >= minScore);
    if (sort === "checked") return [...list].sort((a, b) => b.job.last_checked_at.localeCompare(a.job.last_checked_at));
    if (sort === "title") return [...list].sort((a, b) => a.job.title.localeCompare(b.job.title));
    return list;
  }, [matches.data, sort, minScore]);

  const data = matches.data;
  return (
    <>
      <PageHeader
        title="Recommended jobs"
        description="Listings ranked against your resume and preferences, with the evidence behind every score."
      />

      {!profile?.has_resume ? (
        <EmptyState title="Upload your resume to get recommendations" action={<Link to="/app/resume" className="btn-primary no-underline">Upload resume</Link>}>
          Matching compares your extracted skills, experience and preferences with each listing.
        </EmptyState>
      ) : (
        <section className="panel mb-8 space-y-5 p-5" aria-labelledby="run-heading">
          <h2 id="run-heading" className="text-lg font-semibold">
            Generate recommendations
          </h2>
          <fieldset>
            <legend className="field-label">What matters most to you?</legend>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {PRESETS.map((p) => (
                <label key={p.value} className={`cursor-pointer rounded border p-3 text-sm ${preset === p.value ? "border-teal bg-teal-tint" : "border-line"}`}>
                  <input type="radio" name="preset" value={p.value} checked={preset === p.value} onChange={() => setPreset(p.value)} className="mr-2 accent-teal" />
                  <span className="font-semibold">{p.label}</span>
                  <span className="mt-1 block text-muted">{p.help}</span>
                </label>
              ))}
            </div>
          </fieldset>
          {preset === "custom" && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {COMPONENT_ORDER.map((k) => (
                <div key={k}>
                  <label htmlFor={`w-${k}`} className="flex justify-between text-sm">
                    <span>{COMPONENT_SHORT[k]}</span>
                    <span className="num text-muted">{custom[k]}</span>
                  </label>
                  <input
                    id={`w-${k}`}
                    type="range"
                    min={0}
                    max={5}
                    step={1}
                    value={custom[k]}
                    onChange={(e) => setCustom({ ...custom, [k]: Number(e.target.value) })}
                    className="w-full accent-teal"
                  />
                </div>
              ))}
              {Object.values(custom).every((v) => v === 0) && <p className="text-sm text-danger">Give at least one priority a value above 0.</p>}
            </div>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            <CheckboxGroup
              legend="Only include employment types"
              hint="Leave empty to include all."
              options={[
                { value: "internship", label: "Internship" },
                { value: "full_time", label: "Full-time" },
                { value: "part_time", label: "Part-time" },
              ]}
              values={types}
              onChange={setTypes}
            />
            <CheckboxGroup
              legend="Only include arrangements"
              hint="Leave empty to include all."
              options={[
                { value: "remote", label: "Remote" },
                { value: "hybrid", label: "Hybrid" },
                { value: "onsite", label: "On-site" },
              ]}
              values={arrangements}
              onChange={setArrangements}
            />
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <button
              type="button"
              className="btn-primary"
              onClick={run}
              disabled={running || (preset === "custom" && Object.values(custom).every((v) => v === 0))}
            >
              {running ? "Ranking listings…" : data?.run_id ? "Run matching again" : "Find my matches"}
            </button>
            {runError && <InlineStatus message={runError} tone="error" />}
          </div>
        </section>
      )}

      {matches.loading && !data ? (
        <LoadingState label="Loading recommendations…" />
      ) : matches.error ? (
        <ErrorState error={matches.error} onRetry={matches.reload} />
      ) : data && data.run_id ? (
        <section aria-labelledby="results-heading" aria-busy={running}>
          <div className="mb-4 space-y-2">
            <h2 id="results-heading" className="num text-lg font-semibold">
              {items.length} of {data.total} recommendation{data.total === 1 ? "" : "s"}
            </h2>
            <p className="text-sm text-muted">
              Generated {formatDate(data.created_at)} with {data.model_version} and semantic backend {data.semantic_backend}.
            </p>
            <p className="max-w-prose rounded border-l-4 border-teal bg-teal-tint px-3 py-2 text-sm">{data.disclaimer}</p>
          </div>
          <div className="mb-4 flex flex-wrap items-center gap-4 text-sm">
            <label className="flex items-center gap-2">
              Sort by
              <select className="field-input w-auto py-1" value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
                <option value="score">Compatibility score</option>
                <option value="checked">Recently checked</option>
                <option value="title">Title</option>
              </select>
            </label>
            <label className="flex items-center gap-2">
              Minimum score
              <select className="field-input w-auto py-1" value={minScore} onChange={(e) => setMinScore(Number(e.target.value))}>
                <option value={0}>Any</option>
                <option value={30}>30+</option>
                <option value={50}>50+</option>
                <option value={70}>70+</option>
              </select>
            </label>
          </div>
          {saver.error && <InlineStatus message={saver.error} tone="error" />}
          {items.length === 0 ? (
            <EmptyState title="No recommendations at this minimum score">Lower the minimum score to see more.</EmptyState>
          ) : (
            <div className="space-y-4">
              {items.map((m) => (
                <JobCard
                  key={m.id}
                  job={m.job}
                  match={m}
                  weights={data.weights as Weights}
                  detailHref={`/app/matches/${m.id}`}
                  onToggleSave={saver.toggle}
                  saving={saver.pending === m.job.id}
                />
              ))}
            </div>
          )}
        </section>
      ) : (
        profile?.has_resume && (
          <EmptyState title="No recommendations yet">Choose your priorities above and select “Find my matches”.</EmptyState>
        )
      )}
    </>
  );
}
