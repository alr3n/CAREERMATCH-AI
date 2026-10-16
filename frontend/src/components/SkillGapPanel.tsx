import { Link } from "react-router-dom";
import type { SkillGap } from "../types/api";

export function SkillGapPanel({ gaps, jobsAnalyzed }: { gaps: SkillGap[]; jobsAnalyzed: number }) {
  if (gaps.length === 0) {
    return <p className="text-muted">Every skill detected in your top jobs was found in your resume.</p>;
  }
  return (
    <ol className="divide-y divide-line">
      {gaps.map((gap) => (
        <li key={gap.skill} className="py-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-base font-semibold">
              {gap.skill}
              {gap.in_development_list && <span className="ml-2 text-xs font-normal text-teal">on your learning list</span>}
            </h3>
            <p className="num text-sm text-muted">
              {gap.required_count > 0 && <span className="font-semibold text-amber">Required in {gap.required_count}</span>}
              {gap.required_count > 0 && gap.preferred_count > 0 && ", "}
              {gap.preferred_count > 0 && <span>preferred in {gap.preferred_count}</span>}
              <span> of {jobsAnalyzed} jobs</span>
            </p>
          </div>
          <ul className="mt-2 space-y-1 text-sm">
            {gap.examples.map((ex) => (
              <li key={`${ex.job_id}-${ex.requirement}`} className="text-muted">
                <Link to={`/app/jobs/${ex.job_id}`}>{ex.title}</Link>
                : “{ex.evidence}”
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ol>
  );
}
