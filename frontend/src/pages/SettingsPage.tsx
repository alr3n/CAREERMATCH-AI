import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/AppShell";
import { ConfirmationDialog } from "../components/ConfirmationDialog";
import { InlineStatus, LoadingState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";
import { formatDate } from "../utils/format";

export function SettingsPage() {
  const { profile, setProfile, logout } = useAuth();
  const assistant = useAsync(() => api.assistantStatus(), []);
  const [status, setStatus] = useState<{ message: string | null; tone: "success" | "error" | "info" }>({ message: null, tone: "info" });
  if (!profile) return <LoadingState />;
  const p = profile.profile;

  async function toggle(key: "consent_llm_processing" | "consent_store_resume_text", value: boolean) {
    try {
      setProfile(await api.updateProfile({ [key]: value }));
      setStatus({ message: value ? "Consent given." : "Consent withdrawn.", tone: "success" });
      void assistant.reload();
    } catch (e) {
      setStatus({ message: e instanceof Error ? e.message : "Couldn't update consent.", tone: "error" });
    }
  }

  return (
    <>
      <PageHeader title="Settings & privacy" description={`Signed in as ${profile.user.email}.`} />
      <div className="max-w-3xl space-y-8">
        <section className="panel p-6" aria-labelledby="consent-heading">
          <h2 id="consent-heading" className="text-lg font-semibold">
            Consent
          </h2>
          <p className="mt-1 text-sm text-muted">Both are off by default. You can change them any time. Last changed: {formatDate(p.consent_updated_at)}.</p>
          <div className="mt-4 space-y-5">
            <label className="flex gap-3">
              <input type="checkbox" className="mt-1 h-4 w-4 accent-teal" checked={p.consent_store_resume_text} onChange={(e) => void toggle("consent_store_resume_text", e.target.checked)} />
              <span>
                <span className="font-semibold">Keep the full text of my resume</span>
                <span className="block text-sm text-muted">
                  Contact details are redacted before storage. Without this, only the extracted profile is kept. Turning it off deletes text already stored.
                </span>
              </span>
            </label>
            <label className="flex gap-3">
              <input type="checkbox" className="mt-1 h-4 w-4 accent-teal" checked={p.consent_llm_processing} onChange={(e) => void toggle("consent_llm_processing", e.target.checked)} />
              <span>
                <span className="font-semibold">Allow the career assistant to use an external AI model</span>
                <span className="block text-sm text-muted">
                  {assistant.data?.llm_configured
                    ? `This server is configured to use ${assistant.data.provider}.`
                    : "No external AI model is configured on this server, so nothing would be sent even with consent."}
                </span>
              </span>
            </label>
          </div>
          <InlineStatus message={status.message} tone={status.tone} />
        </section>

        <section className="panel p-6" aria-labelledby="processing-heading">
          <h2 id="processing-heading" className="text-lg font-semibold">
            How your data is processed
          </h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm">
            <li>When you upload a resume, its text is extracted on the CareerMatch AI server. The original file is discarded unless the operator has enabled file retention.</li>
            <li>Skills, education, experience, projects and certifications are extracted with rules on the server. Names, emails, phone numbers and addresses are not extracted.</li>
            <li>Matching, skill-gap analysis and the template assistant run entirely on the server. No paid AI service is used for them.</li>
            <li>Job listings come from public employer job boards (Greenhouse, Lever). Your data is never sent to job boards or employers, and CareerMatch AI never applies on your behalf.</li>
            <li>Search history stores filters and keywords only. Sensitive characteristics are not used for ranking.</li>
          </ul>
          {assistant.data && (
            <>
              <h3 className="mt-5 text-sm font-semibold">Shared with an external AI provider only if configured and you consent</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
                {assistant.data.data_shared_with_llm.map((d) => (
                  <li key={d}>{d}</li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section className="panel p-6" aria-labelledby="delete-heading">
          <h2 id="delete-heading" className="text-lg font-semibold">
            Delete your data
          </h2>
          <p className="mt-1 text-sm text-muted">
            To delete just your resume and the matches based on it, use <Link to="/app/resume">My resume</Link>. Deleting your account removes everything:
            resumes, extracted profile, preferences, matches, saved jobs and history.
          </p>
          <div className="mt-4">
            <ConfirmationDialog
              trigger={
                <button type="button" className="btn-danger">
                  Delete my account
                </button>
              }
              title="Delete your account permanently?"
              description="All of your data will be deleted immediately. This can't be undone."
              confirmLabel="Delete account"
              onConfirm={async () => {
                await api.deleteAccount();
                logout();
                // Full reload so no in-memory state from the deleted account survives.
                window.location.replace("/");
              }}
            />
          </div>
        </section>
      </div>
    </>
  );
}
