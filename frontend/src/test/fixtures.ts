import type { JobSummary, MatchSummary, Profile, Resume, Weights } from "../types/api";

export const weights: Weights = {
  semantic_similarity: 0.35,
  required_skill_coverage: 0.3,
  preferred_skill_coverage: 0.1,
  experience_compatibility: 0.1,
  preference_compatibility: 0.1,
  profile_relevance: 0.05,
};

export function job(overrides: Partial<JobSummary> = {}): JobSummary {
  return {
    id: "job-1",
    title: "Data Analyst Intern",
    company: "Test Company (Demo – fictional)",
    location: "Makati, Metro Manila",
    work_arrangement: "hybrid",
    employment_type: "internship",
    experience_level: "internship",
    category: "Data & Analytics",
    salary_min: "12000",
    salary_max: "15000",
    salary_currency: "PHP",
    salary_interval: "per-month-salary",
    salary_text: null,
    posted_at: null,
    deadline: null,
    apply_url: "https://example.com/demo-jobs/1",
    last_checked_at: new Date().toISOString(),
    freshness: "fresh",
    status: "active",
    provider: "demo",
    source_name: "DEMO DATA",
    is_demo: true,
    is_saved: false,
    required_skills: ["SQL", "Python"],
    ...overrides,
  };
}

export function match(overrides: Partial<MatchSummary> = {}): MatchSummary {
  return {
    id: "match-1",
    run_id: "run-1",
    rank: 1,
    score: 72.4,
    evidence_coverage: 0.95,
    components: {
      semantic_similarity: 0.6,
      required_skill_coverage: 0.75,
      preferred_skill_coverage: 0.5,
      experience_compatibility: 1,
      preference_compatibility: 1,
      profile_relevance: null,
    },
    matched_skills: ["SQL", "Python"],
    related_skills: [],
    missing_required: ["Power BI"],
    missing_preferred: [],
    top_reason: "3 of 4 required skills found in your resume",
    job: job(),
    ...overrides,
  };
}

export const profile: Profile = {
  display_name: null,
  career_stage: null,
  goal: null,
  preferred_titles: [],
  preferred_industries: [],
  preferred_locations: [],
  work_arrangements: [],
  employment_types: [],
  min_salary: null,
  salary_currency: null,
  skills_to_develop: [],
  consent_llm_processing: false,
  consent_store_resume_text: false,
  consent_updated_at: null,
  onboarding_completed: false,
  updated_at: "2026-10-01T00:00:00Z",
};

export const resume: Resume = {
  id: "resume-1",
  original_filename: "resume.pdf",
  content_type: "pdf",
  file_size: 1000,
  page_count: 1,
  char_count: 900,
  status: "processed",
  extraction_method: "pymupdf-text+rules-v1",
  extraction_warnings: [],
  summary: "Aspiring data analyst",
  total_experience_months: 3,
  certifications: [],
  achievements: [],
  detected_preferences: {},
  is_active: true,
  raw_text_stored: false,
  file_retained: false,
  skills: [
    { skill: "Python", category: "Programming Languages", source: "extracted", evidence: "Python, SQL", confidence: 0.9 },
    { skill: "Exel", category: null, source: "extracted", evidence: "Exel", confidence: 0.7 },
  ],
  education: [],
  experience: [],
  projects: [],
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};
