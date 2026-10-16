import { useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PageHeader } from "../components/AppShell";
import { SkillChip } from "../components/SkillChip";
import { SkillGapPanel } from "../components/SkillGapPanel";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { ApiError, api } from "../services/api";

const TOP_K = 10;
const INITIAL_GAPS = 10;

export function SkillsPage() {
  const [showAll, setShowAll] = useState(false);
  const state = useAsync(async () => {
    const [report, recs] = await Promise.all([api.skillGaps(TOP_K), api.skillRecommendations()]);
    return { report, recs };
  }, []);

  if (state.loading) return <LoadingState label="Analysing skill gaps…" />;
  if (state.error) {
    const code = state.error instanceof ApiError ? state.error.code : "";
    if (code === "matches_required" || code === "resume_required") {
      return (
        <>
          <PageHeader title="Skill gaps" />
          <EmptyState
            title={code === "resume_required" ? "Upload your resume first" : "Generate recommendations first"}
            action={
              <Link to={code === "resume_required" ? "/app/resume" : "/app/matches"} className="btn-primary no-underline">
                {code === "resume_required" ? "Upload resume" : "Go to recommendations"}
              </Link>
            }
          >
            The gap analysis compares your resume with the jobs you were matched to, so it needs both.
          </EmptyState>
        </>
      );
    }
    return <ErrorState error={state.error} onRetry={state.reload} />;
  }
  const { report, recs } = state.data!;
  const chartData = report.skill_frequency.slice(0, 15).map((f) => ({ ...f, percent: Math.round(f.share * 100) }));

  return (
    <>
      <PageHeader title="Skill gaps" description={`${report.basis}. ${report.note}`} />

      <div className="grid gap-8 lg:grid-cols-[1.3fr_1fr]">
        <section className="panel p-6" aria-labelledby="gaps-heading">
          <h2 id="gaps-heading" className="text-lg font-semibold">
            Skills your top jobs ask for that weren't found in your resume
          </h2>
          <p className="mt-1 text-sm text-muted">Ordered by priority: required counts twice as much as preferred.</p>
          <div className="mt-2">
            <SkillGapPanel gaps={showAll ? report.gaps : report.gaps.slice(0, INITIAL_GAPS)} jobsAnalyzed={report.jobs_analyzed} />
          </div>
          {report.gaps.length > INITIAL_GAPS && (
            <button type="button" className="btn-secondary mt-2" onClick={() => setShowAll((v) => !v)} aria-expanded={showAll}>
              {showAll ? "Show fewer" : `Show all ${report.gaps.length} skills`}
            </button>
          )}
        </section>

        <div className="space-y-8">
          <section className="panel p-6" aria-labelledby="have-heading">
            <h2 id="have-heading" className="text-lg font-semibold">
              Skills identified in your resume
            </h2>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {report.identified_skills.map((s) => (
                <SkillChip
                  key={s.skill}
                  skill={s.jobs_requesting ? `${s.skill} (${s.jobs_requesting})` : s.skill}
                  variant={s.jobs_requesting ? "matched" : "neutral"}
                  title={s.jobs_requesting ? `Requested by ${s.jobs_requesting} of your top jobs` : "Not requested by your top jobs"}
                />
              ))}
            </div>
            <p className="mt-3 text-xs text-muted">Numbers show how many of your top {report.jobs_analyzed} jobs ask for the skill.</p>
          </section>

          <section className="panel p-6" aria-labelledby="freq-heading">
            <h2 id="freq-heading" className="text-lg font-semibold">
              Most requested skills across all {report.total_listings} listings
            </h2>
            <div className="mt-4 h-[26rem]" role="img" aria-label="Bar chart of the most requested skills across all listings">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16, top: 0, bottom: 0 }}>
                  <CartesianGrid horizontal={false} stroke="#DCE1DE" />
                  <XAxis type="number" unit="%" tick={{ fontSize: 12, fill: "#5A6672" }} domain={[0, "dataMax"]} />
                  <YAxis type="category" dataKey="skill" width={120} tick={{ fontSize: 12, fill: "#17212B" }} />
                  <Tooltip formatter={(v: number) => [`${v}% of listings`, "Requested in"]} cursor={{ fill: "#F6F7F5" }} />
                  <Bar dataKey="percent" radius={[0, 3, 3, 0]}>
                    {chartData.map((d) => (
                      <Cell key={d.skill} fill={d.user_has ? "#0F6E66" : "#C9D2CE"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 flex flex-wrap gap-4 text-xs text-muted">
              <span>
                <span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-teal align-middle" aria-hidden="true" />
                In your resume
              </span>
              <span>
                <span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-[#C9D2CE] align-middle" aria-hidden="true" />
                Not found in your resume
              </span>
            </p>
            {/* sr-only on a wrapper: a table ignores the 1px width and would widen the page. */}
            <div className="sr-only">
              <table>
                <caption>Most requested skills</caption>
                <tbody>
                  {chartData.map((d) => (
                    <tr key={d.skill}>
                      <td>{d.skill}</td>
                      <td>{d.percent}%</td>
                      <td>{d.user_has ? "in your resume" : "not found in your resume"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>

      <section className="mt-10" aria-labelledby="recs-heading">
        <h2 id="recs-heading" className="text-xl font-bold">
          How to close the top gaps
        </h2>
        <p className="mt-1 text-sm text-muted">{recs.note}</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {recs.recommendations.map((r) => (
            <article key={r.skill} className="panel p-5">
              <h3 className="text-lg font-semibold">{r.skill}</h3>
              <p className="text-sm text-muted">{r.why}</p>
              <h4 className="mt-3 text-sm font-semibold">Project idea</h4>
              <p className="text-sm">{r.project_idea}</p>
              <h4 className="mt-3 text-sm font-semibold">Show it on your resume</h4>
              <p className="text-sm">{r.how_to_demonstrate}</p>
              <h4 className="mt-3 text-sm font-semibold">Free resources</h4>
              {r.resources.length > 0 ? (
                <ul className="mt-1 space-y-1 text-sm">
                  {r.resources.map((res) => (
                    <li key={res.url}>
                      <a href={res.url} target="_blank" rel="noopener noreferrer">
                        {res.title}
                      </a>{" "}
                      <span className="text-muted">by {res.provider}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted">{r.resources_note}</p>
              )}
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
