import { Link } from "react-router-dom";
import type { JobSummary, MatchSummary, Weights } from "../types/api";
import { ARRANGEMENT_LABEL, EMPLOYMENT_LABEL, NOT_SPECIFIED, formatDate, salaryOf } from "../utils/format";
import { ListingFreshnessIndicator } from "./ListingFreshnessIndicator";
import { MatchScore } from "./MatchScore";
import { SkillChip } from "./SkillChip";
import { SourceBadge } from "./SourceBadge";

interface Props {
  job: JobSummary;
  match?: MatchSummary;
  weights?: Weights | null;
  detailHref: string;
  onToggleSave: (job: JobSummary) => void;
  saving?: boolean;
}

export function JobCard({ job, match, weights, detailHref, onToggleSave, saving }: Props) {
  const salary = salaryOf(job);
  const separateApply = job.apply_url !== job.posting_url;
  return (
    // The card lays itself out by its own width (container query), not the screen's:
    // the same card sits in columns of very different sizes across pages.
    <article className="panel @container min-w-0" aria-labelledby={`job-${job.id}`}>
      <div className="flex flex-col gap-4 p-4 sm:p-5 @2xl:flex-row @2xl:gap-6">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <SourceBadge job={job} />
            <ListingFreshnessIndicator lastChecked={job.last_checked_at} freshness={job.freshness} />
          </div>
          <h3 id={`job-${job.id}`} className="break-words text-lg font-semibold leading-snug">
            <Link to={detailHref} className="text-ink no-underline hover:text-teal hover:underline">
              {job.title}
            </Link>
          </h3>
          <p className="break-words text-sm text-muted">
            <span className="font-semibold text-ink">{job.company}</span>
            <span aria-hidden="true"> · </span>
            {job.location ?? <span className="italic">Location {NOT_SPECIFIED.toLowerCase()}</span>}
          </p>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-label="Job details">
            <li>{ARRANGEMENT_LABEL[job.work_arrangement]}</li>
            <li>{EMPLOYMENT_LABEL[job.employment_type]}</li>
            <li className={salary ? "num" : "text-muted"}>{salary ? <span className="break-words">{salary}</span> : `Salary ${NOT_SPECIFIED.toLowerCase()}`}</li>
            <li className="text-muted">{job.posted_at ? `Posted ${formatDate(job.posted_at)}` : `Posting date ${NOT_SPECIFIED.toLowerCase()}`}</li>
          </ul>
          {match ? (
            <div className="space-y-2 pt-1">
              {match.matched_skills.length > 0 && (
                <div>
                  <p className="mb-1 text-xs text-muted">Found in your resume</p>
                  <div className="flex flex-wrap gap-1.5">
                    {match.matched_skills.slice(0, 8).map((s) => (
                      <SkillChip key={s} skill={s} variant="matched" />
                    ))}
                  </div>
                </div>
              )}
              {match.missing_required.length > 0 && (
                <div>
                  <p className="mb-1 text-xs text-muted">Required, not found in your resume</p>
                  <div className="flex flex-wrap gap-1.5">
                    {match.missing_required.slice(0, 6).map((s) => (
                      <SkillChip key={s} skill={s} variant="missing" />
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            job.required_skills.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1" aria-label="Required skills">
                {job.required_skills.slice(0, 8).map((s) => (
                  <SkillChip key={s} skill={s} />
                ))}
              </div>
            )
          )}
        </div>
        <div className="flex shrink-0 flex-col justify-between gap-4 @2xl:w-60">
          {match && weights && (
            <MatchScore score={match.score} components={match.components} weights={weights} evidenceCoverage={match.evidence_coverage} />
          )}
          <div className="grid grid-cols-2 gap-2 @md:flex @md:flex-wrap @2xl:grid @2xl:grid-cols-2">
            <Link to={detailHref} className="btn-primary no-underline">
              View details
            </Link>
            <button type="button" className="btn-secondary" onClick={() => onToggleSave(job)} disabled={saving} aria-pressed={job.is_saved}>
              {job.is_saved ? "Saved" : "Save"}
            </button>
            <a href={job.posting_url} target="_blank" rel="noopener noreferrer" className="btn-ghost col-span-2 border border-line @md:border-0">
              {separateApply ? "View original posting" : `Apply on ${job.source_platform}`}
              <span className="sr-only"> (opens {job.source_platform} in a new tab)</span>
            </a>
            {separateApply && (
              <a href={job.apply_url} target="_blank" rel="noopener noreferrer" className="btn-ghost col-span-2 border border-line @md:border-0">
                Apply
                <span className="sr-only"> (opens the application page in a new tab)</span>
              </a>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
