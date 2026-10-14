import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { timeAgo } from "../utils/format";

/** Honest list of where listings come from, including unconfigured providers. */
export function SourcesPanel() {
  const { data, error } = useAsync(() => api.sources(), []);
  if (error || !data) return null;
  return (
    <section className="panel p-5 text-sm" aria-labelledby="sources-heading">
      <h2 id="sources-heading" className="font-semibold">
        Job sources
      </h2>
      <ul className="mt-2 space-y-2">
        {data.providers.map((p) => (
          <li key={p.provider}>
            <span className="font-semibold">{p.name}:</span>{" "}
            {p.configured ? `${p.sources.join(", ")}` : <span className="text-muted">not configured ({p.config_variable})</span>}
          </li>
        ))}
        {data.demo_enabled && <li className="text-muted">Demo listings are enabled for demonstration.</li>}
      </ul>
      {data.sources.some((s) => s.last_status === "error" || s.last_status === "rate_limited") && (
        <ul className="mt-2 space-y-1 text-danger">
          {data.sources
            .filter((s) => s.last_status === "error" || s.last_status === "rate_limited")
            .map((s) => (
              <li key={s.id}>
                {s.display_name}: {s.last_error}
              </li>
            ))}
        </ul>
      )}
      {data.sources.length > 0 && (
        <p className="mt-2 text-muted">
          Last fetch: {timeAgo(data.sources.map((s) => s.last_fetched_at).filter(Boolean).sort().at(-1) ?? null)}
        </p>
      )}
      <p className="mt-3 text-xs text-muted">{data.unsupported_note}</p>
    </section>
  );
}
