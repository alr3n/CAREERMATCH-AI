import { useState } from "react";
import { Link } from "react-router-dom";
import { InlineStatus } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { AssistantResponse, AssistantTask } from "../types/api";

const TASKS: { value: AssistantTask; label: string }[] = [
  { value: "explain_requirements", label: "Explain the requirements" },
  { value: "resume_suggestions", label: "Suggest resume improvements" },
  { value: "rewrite_bullet", label: "Improve a resume bullet" },
  { value: "portfolio_projects", label: "Suggest portfolio projects" },
  { value: "interview_questions", label: "Practise interview questions" },
  { value: "cover_letter", label: "Draft a cover letter" },
];

export function AssistantPanel({ jobId }: { jobId: string }) {
  const status = useAsync(() => api.assistantStatus(), []);
  const [task, setTask] = useState<AssistantTask>("explain_requirements");
  const [bullet, setBullet] = useState("");
  const [result, setResult] = useState<AssistantResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  async function run() {
    setBusy(true);
    setError(null);
    setCopied(false);
    try {
      setResult(await api.assistant({ task, job_id: jobId, input_text: task === "rewrite_bullet" ? bullet : undefined }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "The assistant could not respond.");
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.text);
      setCopied(true);
    } catch {
      setError("Copying isn't available in this browser. Select the text and copy it instead.");
    }
  }

  const s = status.data;
  return (
    <section className="panel p-5" aria-labelledby="assistant-heading">
      <h2 id="assistant-heading" className="text-lg font-semibold">
        Career assistant
      </h2>
      <p className="mt-1 text-sm text-muted">
        {s?.llm_configured && s.consent_given
          ? `Uses ${s.provider} with your consent, grounded in your profile and this posting.`
          : "Uses templates built from your profile and this posting. Nothing is sent to an external AI service."}
        {s?.llm_configured && !s.consent_given && (
          <>
            {" "}
            An AI model is available if you allow it in <Link to="/app/settings">Settings &amp; privacy</Link>.
          </>
        )}
      </p>
      <div className="mt-4 space-y-3">
        <label htmlFor="assistant-task" className="field-label">
          What would you like help with?
        </label>
        <select id="assistant-task" className="field-input" value={task} onChange={(e) => setTask(e.target.value as AssistantTask)}>
          {TASKS.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        {task === "rewrite_bullet" && (
          <div>
            <label htmlFor="assistant-bullet" className="field-label">
              Resume bullet
            </label>
            <textarea
              id="assistant-bullet"
              className="field-input min-h-[4rem]"
              maxLength={1500}
              value={bullet}
              onChange={(e) => setBullet(e.target.value)}
              placeholder="e.g. Responsible for cleaning sales data in Excel"
            />
          </div>
        )}
        <button type="button" className="btn-primary" onClick={run} disabled={busy || (task === "rewrite_bullet" && !bullet.trim())}>
          {busy ? "Working…" : "Get help"}
        </button>
        {error && <InlineStatus message={error} tone="error" />}
      </div>
      {result && (
        <div className="mt-6 border-t border-line pt-4" aria-live="polite">
          <p className="rounded border-l-4 border-amber bg-amber-tint px-3 py-2 text-sm">{result.notice}</p>
          {result.fallback_reason && <p className="mt-2 text-xs text-muted">{result.fallback_reason}</p>}
          <h3 className="mt-4 font-semibold">{result.title}</h3>
          {result.sections.length > 0 ? (
            result.sections.map((sec) => (
              <div key={sec.heading} className="mt-3">
                <h4 className="text-sm font-semibold">{sec.heading}</h4>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                  {sec.items.map((item, i) => (
                    <li key={i} className="whitespace-pre-line">
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))
          ) : (
            <div className="mt-3 whitespace-pre-line text-sm">{result.text}</div>
          )}
          <div className="mt-4 flex items-center gap-3">
            <button type="button" className="btn-secondary" onClick={copy}>
              Copy draft
            </button>
            {copied && <span className="text-sm text-teal">Copied. Review it before you use it.</span>}
          </div>
          <p className="mt-2 text-xs text-muted">Generated by {result.mode_used === "llm" ? result.model : "CareerMatch templates"}.</p>
        </div>
      )}
    </section>
  );
}
