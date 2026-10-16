import type { JobDetail } from "../types/api";
import { ARRANGEMENT_LABEL, EMPLOYMENT_LABEL, LEVEL_LABEL, NOT_SPECIFIED, formatDate, salaryOf } from "../utils/format";
import { ListingFreshnessIndicator } from "./ListingFreshnessIndicator";
import { SkillChip } from "./SkillChip";
import { SourceBadge } from "./SourceBadge";

interface Props {
  job: JobDetail;
  userSkills?: Set<string>;
  onToggleSave: () => void;
  saving?: boolean;
}

/** Source-provided facts about a listing. AI analysis is rendered elsewhere and labelled as such. */
export function JobDetailPanel({ job, userSkills, onToggleSave, saving }: Props) {
  const salary = salaryOf(job);
  const separateApply = job.apply_url !== job.posting_url;
  const variant = (skill: string) => (userSkills ? (userSkills.has(skill.toLowerCase()) ? "matched" : "missing") : "neutral");
  const required = job.skills.filter((s) => s.requirement === "required");
  const preferred = job.skills.filter((s) => s.requirement === "preferred");

  return (
    <section aria-labelledby="job-title" className="space-y-6">
      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <SourceBadge job={job} />
          <ListingFreshnessIndicator lastChecked={job.last_checked_at} freshness={job.freshness} />
          {job.status !== "active" && <span className="rounded bg-danger-tint px-2 py-0.5 text-xs font-semibold text-danger">No longer listed</span>}
        </div>
        <h1 id="job-title" className="break-words text-2xl font-bold md:text-3xl">
          {job.title}
        </h1>
        <p className="break-words text-muted">
          <span className="font-semibold text-ink">{job.company}</span>
          <span aria-hidden="true"> · </span>
          {job.location ?? `Location ${NOT_SPECIFIED.toLowerCase()}`}
        </p>
        <div className="grid grid-cols-1 gap-2 sm:flex sm:flex-wrap">
          <a href={job.apply_url} target="_blank" rel="noopener noreferrer" className="btn-primary no-underline">
            Apply on {job.source_platform}
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
          {separateApply && (
            <a href={job.posting_url} target="_blank" rel="noopener noreferrer" className="btn-secondary no-underline">
              View original posting
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          )}
          <button type="button" className="btn-secondary" onClick={onToggleSave} disabled={saving} aria-pressed={job.is_saved}>
            {job.is_saved ? "Saved" : "Save job"}
          </button>
        </div>
      </header>

      <div className="panel p-5">
        <h2 className="text-lg font-semibold">From the original posting</h2>
        <p className="mt-1 text-sm text-muted">{job.source_attribution}</p>
        <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted">Work arrangement</dt>
            <dd>{ARRANGEMENT_LABEL[job.work_arrangement]}</dd>
          </div>
          <div>
            <dt className="text-muted">Employment type</dt>
            <dd>{EMPLOYMENT_LABEL[job.employment_type]}</dd>
          </div>
          <div>
            <dt className="text-muted">Experience level</dt>
            <dd>
              {LEVEL_LABEL[job.experience_level]}
              {job.min_years_experience !== null && `, ${job.min_years_experience}+ years mentioned`}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Salary</dt>
            <dd className="num break-words">{salary ?? NOT_SPECIFIED}</dd>
          </div>
          <div>
            <dt className="text-muted">Posted</dt>
            <dd>{formatDate(job.posted_at)}</dd>
          </div>
          <div>
            <dt className="text-muted">Application deadline</dt>
            <dd>{formatDate(job.deadline)}</dd>
          </div>
          <div>
            <dt className="text-muted">Source platform</dt>
            <dd>{job.source_platform}</dd>
          </div>
          <div className="min-w-0">
            <dt className="text-muted">Original posting</dt>
            <dd className="truncate">
              <a href={job.posting_url} target="_blank" rel="noopener noreferrer" title={job.posting_url}>
                {hostOf(job.posting_url)}
              </a>
            </dd>
          </div>
        </dl>
      </div>

      {(job.required_qualifications.length > 0 || job.preferred_qualifications.length > 0) && (
        <div className="grid gap-4 md:grid-cols-2">
          {job.required_qualifications.length > 0 && (
            <div className="panel p-5">
              <h2 className="text-lg font-semibold">Required qualifications</h2>
              <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm">
                {job.required_qualifications.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </div>
          )}
          {job.preferred_qualifications.length > 0 && (
            <div className="panel p-5">
              <h2 className="text-lg font-semibold">Preferred qualifications</h2>
              <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm">
                {job.preferred_qualifications.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {(required.length > 0 || preferred.length > 0) && (
        <div className="panel p-5">
          <h2 className="text-lg font-semibold">Skills detected in the posting</h2>
          <p className="mt-1 text-sm text-muted">
            Detected automatically by CareerMatch AI.{userSkills ? " Filled chips were found in your resume; outlined ones were not found." : ""}
          </p>
          {required.length > 0 && (
            <div className="mt-3">
              <h3 className="text-sm font-semibold">Required</h3>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {required.map((s) => (
                  <SkillChip key={s.skill} skill={s.skill} variant={variant(s.skill)} title={s.evidence ?? undefined} />
                ))}
              </div>
            </div>
          )}
          {preferred.length > 0 && (
            <div className="mt-3">
              <h3 className="text-sm font-semibold">Preferred</h3>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {preferred.map((s) => (
                  <SkillChip key={s.skill} skill={s.skill} variant={variant(s.skill)} title={s.evidence ?? undefined} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="panel p-5">
        <h2 className="text-lg font-semibold">Full description</h2>
        <div className="mt-3 max-w-prose space-y-2 whitespace-pre-line break-words text-sm leading-relaxed">
          {job.description || "The provider did not include a description. Open the original posting for full details."}
        </div>
      </div>
    </section>
  );
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
