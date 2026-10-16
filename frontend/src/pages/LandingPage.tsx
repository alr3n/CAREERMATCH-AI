import { Link, Navigate } from "react-router-dom";
import { Logo } from "../components/Logo";
import { MatchScore } from "../components/MatchScore";
import { SkillChip } from "../components/SkillChip";
import { useAuth } from "../hooks/useAuth";
import type { Components, Weights } from "../types/api";
import { COMPONENT_ORDER, COMPONENT_SHORT, pct } from "../utils/format";

// Default weights of the transparent-v1 model (backend/app/ml/scoring.py).
const DEFAULT_WEIGHTS: Weights = {
  semantic_similarity: 0.35,
  required_skill_coverage: 0.3,
  preferred_skill_coverage: 0.1,
  experience_compatibility: 0.1,
  preference_compatibility: 0.1,
  profile_relevance: 0.05,
};

// Illustrative values for the preview only — not a real result.
const EXAMPLE: Components = {
  semantic_similarity: 0.71,
  required_skill_coverage: 0.75,
  preferred_skill_coverage: 0.5,
  experience_compatibility: 1,
  preference_compatibility: 1,
  profile_relevance: null,
};
const EXAMPLE_SCORE = (() => {
  const keys = COMPONENT_ORDER.filter((k) => EXAMPLE[k] !== null);
  const w = keys.reduce((a, k) => a + DEFAULT_WEIGHTS[k], 0);
  return { score: (100 * keys.reduce((a, k) => a + DEFAULT_WEIGHTS[k] * (EXAMPLE[k] as number), 0)) / w, coverage: w };
})();

const STEPS = [
  {
    title: "Upload your resume",
    body: "PDF or DOCX. We read the text and pull out skills, education, experience, internships and projects.",
  },
  {
    title: "Check what we found",
    body: "Fix anything that's wrong and add what we missed. Something we didn't detect is never treated as something you can't do.",
  },
  {
    title: "See ranked matches",
    body: "Each listing is scored on six signals, and every score comes with the evidence behind it: matched skills, skills not found, and your preferences.",
  },
  {
    title: "Close the gaps",
    body: "See which skills your best matches ask for most, with free official learning resources and project ideas you can show in a portfolio.",
  },
];

const COMPONENT_HELP: Record<string, string> = {
  semantic_similarity: "How closely your profile's language matches the job description.",
  required_skill_coverage: "Share of the posting's required skills found in your resume. Related skills earn half credit.",
  preferred_skill_coverage: "The same, for nice-to-have skills.",
  experience_compatibility: "Your career stage and dated experience compared with the job's level.",
  preference_compatibility: "Work arrangement, location, employment type and salary, if you set them.",
  profile_relevance: "How the job title and category line up with the roles you're targeting.",
};

export function LandingPage() {
  const { token } = useAuth();
  if (token) return <Navigate to="/app" replace />;

  return (
    <div className="bg-paper">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 md:px-8">
        <Logo />
        <nav aria-label="Site" className="flex items-center gap-2 text-sm">
          <a href="#how" className="hidden px-3 py-2 text-ink no-underline hover:text-teal sm:inline">
            How it works
          </a>
          <a href="#privacy" className="hidden px-3 py-2 text-ink no-underline hover:text-teal sm:inline">
            Privacy
          </a>
          <Link to="/login" className="btn-ghost no-underline">
            Sign in
          </Link>
          <Link to="/register" className="btn-primary no-underline">
            Create account
          </Link>
        </nav>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl gap-12 px-4 pb-20 pt-10 md:grid-cols-[1.1fr_1fr] md:items-center md:px-8 md:pt-16">
          <div>
            <h1 className="text-3xl font-bold leading-tight md:text-4xl">Your skills. Your next opportunity.</h1>
            <p className="mt-5 max-w-prose text-lg text-muted">
              Upload your resume once. CareerMatch AI compares it with internships and jobs from employers' own job boards, ranks them, and
              shows you exactly why each one fits and what isn't in your resume yet.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/register" className="btn-primary px-5 py-3 text-base no-underline">
                Upload your resume
              </Link>
              <Link to="/login" className="btn-secondary px-5 py-3 text-base no-underline">
                I already have an account
              </Link>
            </div>
            <p className="mt-6 max-w-prose text-sm text-muted">
              Built for students, fresh graduates and early-career job seekers in the Philippines, including remote roles. A match score helps
              you prioritise. It doesn't predict whether you'll be hired.
            </p>
          </div>

          <figure className="panel p-6 shadow-[0_1px_0_#DCE1DE,0_12px_32px_-16px_rgba(23,33,43,0.25)]">
            <figcaption className="mb-4 text-sm text-muted">Illustrative example of a recommendation</figcaption>
            <p className="text-lg font-semibold">Data Analyst Intern</p>
            <p className="text-sm text-muted">Example company, Makati (hybrid)</p>
            <div className="mt-5">
              <MatchScore score={EXAMPLE_SCORE.score} components={EXAMPLE} weights={DEFAULT_WEIGHTS} evidenceCoverage={EXAMPLE_SCORE.coverage} />
            </div>
            <div className="mt-5 space-y-3">
              <div>
                <p className="mb-1 text-xs text-muted">Found in your resume</p>
                <div className="flex flex-wrap gap-1.5">
                  {["SQL", "Python", "Pandas"].map((s) => (
                    <SkillChip key={s} skill={s} variant="matched" />
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-1 text-xs text-muted">Required, not found in your resume</p>
                <SkillChip skill="Power BI" variant="missing" />
              </div>
            </div>
            <ul className="mt-5 space-y-1 border-t border-line pt-4 text-sm">
              <li>3 of 4 required skills found in your resume</li>
              <li>Internship posting matches your stage: student</li>
              <li>Hybrid in Metro Manila matches your preferences</li>
            </ul>
          </figure>
        </section>

        <section id="how" className="border-t border-line bg-surface">
          <div className="mx-auto max-w-6xl px-4 py-16 md:px-8">
            <h2 className="text-2xl font-bold">How it works</h2>
            <ol className="mt-8 grid gap-8 md:grid-cols-4">
              {STEPS.map((step, i) => (
                <li key={step.title}>
                  <span className="num flex h-8 w-8 items-center justify-center rounded-full border border-teal text-sm font-semibold text-teal" aria-hidden="true">
                    {i + 1}
                  </span>
                  <h3 className="mt-3 text-base font-semibold">{step.title}</h3>
                  <p className="mt-1 text-sm text-muted">{step.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16 md:px-8">
          <div className="grid gap-10 md:grid-cols-[1fr_1.4fr]">
            <div>
              <h2 className="text-2xl font-bold">What the score means</h2>
              <p className="mt-3 max-w-prose text-muted">
                The compatibility score is a weighted average of six signals. If a signal can't be measured, for example because a posting lists
                no skills, it's left out, and the note under the bar shows how much of the scoring weight could actually be evaluated.
              </p>
              <p className="mt-3 max-w-prose text-muted">
                A score of 80 means strong alignment between your resume and the posting. It is not an 80% chance of getting the job. The weights
                below are starting values and are still being evaluated.
              </p>
            </div>
            <dl className="divide-y divide-line border-y border-line">
              {COMPONENT_ORDER.map((k) => (
                <div key={k} className="grid grid-cols-[3.5rem_1fr] gap-4 py-3">
                  <dt className="num text-lg font-semibold text-teal">{pct(DEFAULT_WEIGHTS[k])}</dt>
                  <dd>
                    <span className="font-semibold">{COMPONENT_SHORT[k]}.</span> <span className="text-muted">{COMPONENT_HELP[k]}</span>
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section className="border-t border-line bg-surface">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 md:grid-cols-2 md:px-8">
            <div>
              <h2 className="text-2xl font-bold">Where the jobs come from</h2>
              <p className="mt-3 max-w-prose text-muted">
                Listings are real postings retrieved from employers' public job boards (Greenhouse, Lever, SmartRecruiters), the Remotive remote-jobs
                feed and, where configured, the JSearch job-search API, which includes postings published on LinkedIn, Indeed, Glassdoor and
                JobStreet. Each listing names its source, links to the original posting and shows when it was last checked. We never scrape job
                sites or show sample jobs.
              </p>
            </div>
            <div id="privacy">
              <h2 className="text-2xl font-bold">Your data</h2>
              <ul className="mt-3 max-w-prose list-disc space-y-2 pl-5 text-muted">
                <li>Your original file is discarded after it's read, unless the operator turns on file retention.</li>
                <li>Contact details aren't extracted, and the full resume text is stored only if you allow it.</li>
                <li>Matching runs on the CareerMatch AI server. The optional AI assistant sends data to an external provider only with your consent.</li>
                <li>You can delete your resume, or your whole account and everything linked to it, at any time.</li>
              </ul>
            </div>
          </div>
        </section>
      </main>

      <footer className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-muted md:flex-row md:justify-between md:px-8">
        <Logo className="text-base" />
        <p>CareerMatch AI suggests opportunities. It never applies to jobs or sends your resume to employers.</p>
      </footer>
    </div>
  );
}
