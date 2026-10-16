import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { SourcesResponse } from "../types/api";
import { timeAgo } from "../utils/format";

const STATUS_LABEL: Record<string, string> = {
  ok: "Working",
  error: "Unavailable",
  rate_limited: "Rate-limited",
  never: "Not checked yet",
};

/** Honest list of where listings come from, including sources that are unavailable or not configured. */
export function SourcesPanel({ reloadKey = 0 }: { reloadKey?: number }) {
  const { data, error } = useAsync(() => api.sources(), [reloadKey]);
  if (error || !data) return null;
  return <SourcesList data={data} />;
}

export function SourcesList({ data }: { data: SourcesResponse }) {
  const failing = data.sources.filter((s) => s.last_status === "error" || s.last_status === "rate_limited");
  const configured = data.providers.filter((p) => p.configured);
  const unconfigured = data.providers.filter((p) => !p.configured);
  return (
    <section className="panel p-4 text-sm sm:p-5" aria-labelledby="sources-heading">
      <h2 id="sources-heading" className="font-semibold">
        Job sources
      </h2>
      <p className="mt-1 text-muted">
        Last successful update: <span className="text-ink">{timeAgo(data.last_successful_refresh_at)}</span>
      </p>
      {failing.length > 0 && (
        <div role="alert" className="mt-3 rounded border border-danger/30 bg-danger-tint px-3 py-2">
          <p className="font-semibold text-danger">
            {failing.length === 1 ? "1 source is temporarily unavailable" : `${failing.length} sources are temporarily unavailable`}
          </p>
          <p className="mt-0.5 text-xs text-ink">Listings already stored from these sources stay visible with their last-checked time.</p>
          <ul className="mt-1 space-y-0.5 text-xs text-ink">
            {failing.map((s) => (
              <li key={s.id} className="break-words">
                <span className="font-semibold">{s.display_name}</span>: {s.last_error}
              </li>
            ))}
          </ul>
        </div>
      )}
      <details className="group mt-3" open={configured.length === 0 ? true : undefined}>
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-2 font-semibold text-teal">
          <span>
            {data.sources.length} connected source{data.sources.length === 1 ? "" : "s"}
          </span>
          <span aria-hidden="true" className="transition-transform group-open:rotate-180">
            ▾
          </span>
        </summary>
        <ul className="mt-2 space-y-2">
          {data.sources.map((s) => (
            <li key={s.id} className="flex flex-wrap items-baseline justify-between gap-x-2">
              <span className="min-w-0 break-words">
                {s.display_name} <span className="text-xs text-muted">({s.provider})</span>
              </span>
              <span className={`num text-xs ${s.last_status === "ok" ? "text-muted" : "text-danger"}`}>
                {STATUS_LABEL[s.last_status] ?? s.last_status} · {s.active_listings} open
              </span>
            </li>
          ))}
          {data.sources.length === 0 && <li className="text-muted">No job source is configured on this server.</li>}
        </ul>
        {unconfigured.length > 0 && (
          <div className="mt-3 border-t border-line pt-3">
            <p className="text-xs font-semibold text-muted">Available but not configured</p>
            <ul className="mt-1 space-y-1 text-xs text-muted">
              {unconfigured.map((p) => (
                <li key={p.provider}>
                  <a href={p.docs} target="_blank" rel="noopener noreferrer">
                    {p.name}
                  </a>{" "}
                  — {p.access}. Set <code className="break-all">{p.config_variable}</code>.
                </li>
              ))}
            </ul>
          </div>
        )}
        <p className="mt-3 text-xs text-muted">{data.unsupported_note}</p>
      </details>
    </section>
  );
}
