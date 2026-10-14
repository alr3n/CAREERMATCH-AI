import { Link } from "react-router-dom";
import type { JobSummary, MatchSummary, Weights } from "../types/api";
import { ARRANGEMENT_LABEL, EMPLOYMENT_LABEL, formatSalary } from "../utils/format";
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
  const salary = formatSalary(job.salary_min, job.salary_max, job.salary_currency, job.salary_interval);
  return (
    <article className="panel flex flex-col gap-4 p-5 md:flex-row md:gap-6" aria-labelledby={`job-${job.id}`}>
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <SourceBadge provider={job.provider} sourceName={job.source_name} isDemo={job.is_demo} />
          <ListingFreshnessIndicator lastChecked={job.last_checked_at} freshness={job.freshness} />
        </div>
        <h3 id={`job-${job.id}`} className="text-lg font-semibold leading-snug">
          <Link to={detailHref} className="text-ink no-underline hover:text-teal hover:underline">
            {job.title}
          </Link>
        </h3>
        <p className="text-sm text-muted">
          {job.company}
          {job.location ? `, ${job.location}` : ""}
        </p>
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-label="Job details">
          <li>{ARRANGEMENT_LABEL[job.work_arrangement]}</li>
          <li>{EMPLOYMENT_LABEL[job.employment_type]}</li>
          {salary && <li className="num">{salary}</li>}
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
      <div className="flex shrink-0 flex-col justify-between gap-4 md:w-60">
        {match && weights && (
          <MatchScore score={match.score} components={match.components} weights={weights} evidenceCoverage={match.evidence_coverage} />
        )}
        <div className="flex flex-wrap gap-2">
          <Link to={detailHref} className="btn-primary no-underline">
            View details
          </Link>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => onToggleSave(job)}
            disabled={saving}
            aria-pressed={job.is_saved}
          >
            {job.is_saved ? "Saved" : "Save"}
          </button>
          <a href={job.apply_url} target="_blank" rel="noopener noreferrer" className="btn-ghost">
            {job.is_demo ? "Demo link" : "Apply on site"}
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        </div>
      </div>
    </article>
  );
}
