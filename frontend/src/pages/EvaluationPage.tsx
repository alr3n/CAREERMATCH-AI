import { PageHeader } from "../components/AppShell";
import { ErrorState, LoadingState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { formatDate } from "../utils/format";

interface Run {
  model: string;
  kind?: string;
  split?: string;
  metrics: Record<string, number | null>;
  notes?: string;
  by_stage?: Record<string, Record<string, number | null>>;
}

interface Report {
  evaluated_at?: string;
  model_version?: string;
  semantic_backend?: string;
  seed?: number;
  dataset?: { name: string; version: string; description?: string; split?: string; split_note?: string; candidates?: number; jobs?: number; pairs?: number; labels?: string };
  runs?: Run[];
  extraction?: Record<string, Record<string, unknown>>;
  comparison?: { candidate: string; baseline: string; metric: string; mean_difference?: number; "95ci"?: [number, number] };
  max_achievable?: { "precision@5": number; note: string };
  limitations?: string[];
}

const fmt = (v: unknown) => (typeof v === "number" ? v.toFixed(3) : v === null || v === undefined ? "–" : String(v));

export function EvaluationPage() {
  const state = useAsync(() => api.evaluation(), []);
  if (state.loading) return <LoadingState />;
  if (state.error) return <ErrorState error={state.error} onRetry={state.reload} />;
  const summary = state.data!;

  if (summary.status === "not_evaluated" || !summary.report) {
    return (
      <>
        <PageHeader title="Model evaluation" description="Developer-facing report on how well extraction and ranking perform." />
        <div className="panel p-6">
          <p className="text-2xl font-bold">Not yet evaluated.</p>
          <p className="mt-2 max-w-prose text-muted">
            Run <code className="rounded bg-paper px-1">python scripts/evaluate_matching.py</code> to produce a report. No metrics are shown until an
            evaluation has actually been run.
          </p>
        </div>
      </>
    );
  }

  const report = summary.report as Report;
  const runs = report.runs ?? [];
  const metricKeys = Array.from(new Set(runs.flatMap((r) => Object.keys(r.metrics ?? {}))));
  return (
    <>
      <PageHeader title="Model evaluation" description={`${summary.message} Source: ${summary.source}.`} />
      <div className="space-y-8">
        <section className="panel grid gap-6 p-6 md:grid-cols-3" aria-label="Evaluation metadata">
          <div>
            <p className="text-sm text-muted">Evaluated</p>
            <p className="font-semibold">{formatDate(report.evaluated_at)}</p>
          </div>
          <div>
            <p className="text-sm text-muted">Model version</p>
            <p className="font-semibold">{report.model_version ?? "–"}</p>
          </div>
          <div>
            <p className="text-sm text-muted">Semantic backend used</p>
            <p className="font-semibold">{report.semantic_backend ?? "–"}</p>
          </div>
        </section>

        {report.dataset && (
          <section className="panel p-6" aria-labelledby="dataset-heading">
            <h2 id="dataset-heading" className="text-lg font-semibold">
              Dataset
            </h2>
            <p className="mt-1 font-semibold">
              {report.dataset.name} ({report.dataset.version})
            </p>
            {report.dataset.description && <p className="mt-2 max-w-prose text-sm text-muted">{report.dataset.description}</p>}
            <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-muted">Candidate profiles</dt>
                <dd className="num font-semibold">{report.dataset.candidates ?? "–"}</dd>
              </div>
              <div>
                <dt className="text-muted">Job postings</dt>
                <dd className="num font-semibold">{report.dataset.jobs ?? "–"}</dd>
              </div>
              <div>
                <dt className="text-muted">Labelled pairs</dt>
                <dd className="num font-semibold">{report.dataset.pairs ?? "–"}</dd>
              </div>
              <div>
                <dt className="text-muted">Split</dt>
                <dd className="font-semibold">{report.dataset.split ?? "–"}</dd>
              </div>
            </dl>
            {report.dataset.split_note && <p className="mt-3 max-w-prose text-sm text-muted">{report.dataset.split_note}</p>}
            {report.dataset.labels && <p className="mt-2 max-w-prose text-sm text-muted">Labels: {report.dataset.labels}</p>}
          </section>
        )}

        {runs.length > 0 && (
          <section className="panel overflow-x-auto p-6" aria-labelledby="ranking-heading">
            <h2 id="ranking-heading" className="text-lg font-semibold">
              Ranking quality: baselines vs. candidate
            </h2>
            <table className="mt-4 w-full min-w-[32rem] text-sm">
              <thead>
                <tr className="border-b border-line text-left text-muted">
                  <th className="py-2 font-normal">Model</th>
                  <th className="py-2 font-normal">Role</th>
                  {metricKeys.map((k) => (
                    <th key={k} className="py-2 text-right font-normal">
                      {k}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.model} className="border-b border-line/60">
                    <td className="py-2 font-semibold">{r.model}</td>
                    <td className="py-2 text-muted">{r.kind ?? "–"}</td>
                    {metricKeys.map((k) => (
                      <td key={k} className="num py-2 text-right">
                        {fmt(r.metrics?.[k])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {report.max_achievable && (
              <p className="mt-3 text-sm text-muted">
                Highest possible Precision@5 on this benchmark: {fmt(report.max_achievable["precision@5"])}. {report.max_achievable.note}
              </p>
            )}
            {report.comparison?.["95ci"] && (
              <p className="mt-2 text-sm">
                {report.comparison.candidate} vs. {report.comparison.baseline} ({report.comparison.metric}): mean difference{" "}
                <span className="num font-semibold">{fmt(report.comparison.mean_difference)}</span>, 95% CI{" "}
                <span className="num">
                  [{fmt(report.comparison["95ci"][0])}, {fmt(report.comparison["95ci"][1])}]
                </span>
                .{" "}
                {report.comparison["95ci"][0] <= 0
                  ? "The interval includes zero, so this benchmark does not show a reliable improvement."
                  : "The interval excludes zero on this benchmark."}
              </p>
            )}
            {runs.some((r) => r.notes) && (
              <ul className="mt-4 space-y-1 text-sm text-muted">
                {runs.filter((r) => r.notes).map((r) => (
                  <li key={r.model}>
                    <span className="font-semibold text-ink">{r.model}:</span> {r.notes}
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        {report.extraction && (
          <section className="panel overflow-x-auto p-6" aria-labelledby="extraction-heading">
            <h2 id="extraction-heading" className="text-lg font-semibold">
              Extraction quality
            </h2>
            <table className="mt-4 w-full min-w-[28rem] text-sm">
              <thead>
                <tr className="border-b border-line text-left text-muted">
                  <th className="py-2 font-normal">Task</th>
                  <th className="py-2 text-right font-normal">Precision</th>
                  <th className="py-2 text-right font-normal">Recall</th>
                  <th className="py-2 text-right font-normal">F1</th>
                  <th className="py-2 text-right font-normal">Examples</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(report.extraction)
                  .filter(([, m]) => m && typeof m === "object" && ("recall" in m || "precision" in m))
                  .map(([task, m]) => (
                  <tr key={task} className="border-b border-line/60">
                    <td className="py-2">{task.replace(/_/g, " ")}</td>
                    <td className="num py-2 text-right">{fmt(m.precision)}</td>
                    <td className="num py-2 text-right">{fmt(m.recall)}</td>
                    <td className="num py-2 text-right">{fmt(m.f1)}</td>
                    <td className="num py-2 text-right">{fmt(m.examples)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {report.limitations && (
          <section className="panel p-6" aria-labelledby="limits-heading">
            <h2 id="limits-heading" className="text-lg font-semibold">
              Known limitations
            </h2>
            <ul className="mt-3 max-w-prose list-disc space-y-1.5 pl-5 text-sm">
              {report.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </>
  );
}
