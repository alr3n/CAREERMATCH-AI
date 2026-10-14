import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/AppShell";
import { ConfirmationDialog } from "../components/ConfirmationDialog";
import { ResumeUploader } from "../components/ResumeUploader";
import { ErrorState, LoadingState } from "../components/States";
import { ResumeEditor } from "../features/ResumeEditor";
import { useAsync } from "../hooks/useAsync";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";
import type { Resume } from "../types/api";
import { formatDate } from "../utils/format";

export function ResumePage() {
  const { refreshProfile, profile } = useAuth();
  const [replacing, setReplacing] = useState(false);
  const [prefsApplied, setPrefsApplied] = useState(false);
  const state = useAsync<Resume | null>(async () => {
    const list = await api.listResumes();
    const active = list.find((r) => r.is_active) ?? list[0];
    return active ? api.getResume(active.id) : null;
  }, []);

  async function uploaded(resume: Resume) {
    state.setData(resume);
    setReplacing(false);
    setPrefsApplied(false);
    await refreshProfile();
  }

  async function applyDetected(resume: Resume) {
    const d = resume.detected_preferences;
    const current = profile?.profile;
    await api.updateProfile({
      employment_types: (d.employment_types as never) ?? current?.employment_types,
      work_arrangements: (d.work_arrangements as never) ?? current?.work_arrangements,
      preferred_locations: d.locations ?? current?.preferred_locations,
      preferred_titles: d.titles ?? current?.preferred_titles,
    });
    await refreshProfile();
    setPrefsApplied(true);
  }

  if (state.loading) return <LoadingState label="Loading your resume…" />;
  if (state.error) return <ErrorState error={state.error} onRetry={state.reload} />;
  const resume = state.data;

  if (!resume || replacing) {
    return (
      <>
        <PageHeader
          title={resume ? "Upload a new version" : "Upload your resume"}
          description="We'll extract your skills, education, experience and projects. You can review and correct everything before matching."
        />
        <div className="max-w-2xl space-y-4">
          <ResumeUploader onUploaded={uploaded} />
          <p className="text-sm text-muted">
            The original file is discarded after reading (unless this server is configured to keep it), and contact details are not extracted.
            See <Link to="/app/settings">Settings &amp; privacy</Link>.
          </p>
          {resume && (
            <button type="button" className="btn-ghost" onClick={() => setReplacing(false)}>
              Cancel
            </button>
          )}
        </div>
      </>
    );
  }

  const detected = resume.detected_preferences;
  const hasDetected = Object.keys(detected).length > 0;
  return (
    <>
      <PageHeader
        title="My resume"
        description="This is what CareerMatch AI understood from your resume. Correct anything that's wrong — matching uses this profile, not the file."
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={() => setReplacing(true)}>
              Upload new version
            </button>
            <ConfirmationDialog
              trigger={
                <button type="button" className="btn-ghost text-danger">
                  Delete resume
                </button>
              }
              title="Delete this resume?"
              description="The extracted profile, any stored text or file, and all match results based on it will be permanently deleted."
              confirmLabel="Delete resume"
              onConfirm={async () => {
                await api.deleteResume(resume.id);
                await refreshProfile();
                await state.reload();
              }}
            />
          </>
        }
      />
      <div className="mb-8 grid gap-4 md:grid-cols-3">
        <div className="panel p-4 text-sm">
          <p className="text-muted">File</p>
          <p className="mt-1 truncate font-semibold">{resume.original_filename}</p>
          <p className="text-muted">
            {resume.content_type.toUpperCase()}, uploaded {formatDate(resume.created_at)}
          </p>
        </div>
        <div className="panel p-4 text-sm">
          <p className="text-muted">Status</p>
          <p className="mt-1 font-semibold">{resume.status === "reviewed" ? "Reviewed by you" : "Not reviewed yet"}</p>
          <p className="text-muted">
            {resume.total_experience_months !== null ? `${resume.total_experience_months} months of dated experience` : "Experience duration not calculated"}
          </p>
        </div>
        <div className="panel p-4 text-sm">
          <p className="text-muted">Storage</p>
          <p className="mt-1">{resume.raw_text_stored ? "Full text stored (you allowed this)" : "Full text not stored"}</p>
          <p className="text-muted">{resume.file_retained ? "Original file kept on the server" : "Original file discarded"}</p>
        </div>
      </div>

      {resume.extraction_warnings.length > 0 && (
        <div className="mb-8 rounded-lg border border-amber/30 bg-amber-tint p-4 text-sm">
          <p className="font-semibold text-amber">Please check</p>
          <ul className="mt-1 list-disc pl-5">
            {resume.extraction_warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {hasDetected && (
        <div className="panel mb-8 p-4 text-sm">
          <p className="font-semibold">Preferences mentioned in your summary</p>
          <ul className="mt-1 text-muted">
            {detected.titles && <li>Roles: {detected.titles.join(", ")}</li>}
            {detected.employment_types && <li>Employment: {detected.employment_types.join(", ").replace(/_/g, "-")}</li>}
            {detected.work_arrangements && <li>Arrangement: {detected.work_arrangements.join(", ")}</li>}
            {detected.locations && <li>Locations: {detected.locations.join(", ")}</li>}
          </ul>
          {prefsApplied ? (
            <p className="mt-3 text-teal">
              Added to your preferences. <Link to="/app/preferences">Review preferences</Link>
            </p>
          ) : (
            <button type="button" className="btn-secondary mt-3" onClick={() => void applyDetected(resume)}>
              Use these as my preferences
            </button>
          )}
        </div>
      )}

      <ResumeEditor
        key={resume.id}
        resume={resume}
        onSave={async (update) => {
          const saved = await api.correctResume(resume.id, update);
          state.setData(saved);
          await refreshProfile();
        }}
      />
    </>
  );
}
