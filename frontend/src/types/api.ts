// Types mirroring the FastAPI response schemas (see /api/v1/openapi.json).

export type CareerStage = "student" | "fresh_graduate" | "entry_level" | "experienced" | "career_transition";
export type Goal = "internship" | "entry_level" | "experienced" | "career_transition";
export type WorkArrangement = "remote" | "hybrid" | "onsite";
export type EmploymentType = "full_time" | "part_time" | "contract" | "internship" | "temporary";
export type ExperienceLevel = "internship" | "entry" | "mid" | "senior" | "unknown";
export type Freshness = "fresh" | "recent" | "stale";
export type Requirement = "required" | "preferred" | "mentioned";

export interface ApiErrorBody {
  error: { code: string; message: string; details: unknown };
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Profile {
  display_name: string | null;
  career_stage: CareerStage | null;
  goal: Goal | null;
  preferred_titles: string[];
  preferred_industries: string[];
  preferred_locations: string[];
  work_arrangements: WorkArrangement[];
  employment_types: EmploymentType[];
  min_salary: string | null;
  salary_currency: string | null;
  skills_to_develop: string[];
  consent_llm_processing: boolean;
  consent_store_resume_text: boolean;
  consent_updated_at: string | null;
  onboarding_completed: boolean;
  updated_at: string;
}

export type ProfileUpdate = Partial<Omit<Profile, "consent_updated_at" | "updated_at" | "min_salary">> & {
  min_salary?: number | null;
};

export interface CompletenessItem {
  key: string;
  label: string;
  done: boolean;
  weight: number;
}

export interface ProfileResponse {
  user: User;
  profile: Profile;
  completeness: number;
  completeness_items: CompletenessItem[];
  has_resume: boolean;
  llm_available: boolean;
}

export interface ResumeSkill {
  skill: string;
  category: string | null;
  source: "extracted" | "user";
  evidence: string | null;
  confidence: number;
}

export interface Education {
  institution: string | null;
  degree: string | null;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
  source?: string;
}

export interface Experience {
  title: string | null;
  organization: string | null;
  start_date: string | null;
  end_date: string | null;
  duration_months: number | null;
  is_internship: boolean;
  description: string | null;
  source?: string;
}

export interface ResumeProject {
  name: string;
  description: string | null;
  skills: string[];
  source?: string;
}

export interface ResumeSummary {
  id: string;
  original_filename: string;
  content_type: string;
  status: string;
  is_active: boolean;
  created_at: string;
}

export interface Resume {
  id: string;
  original_filename: string;
  content_type: "pdf" | "docx";
  file_size: number;
  page_count: number | null;
  char_count: number;
  status: "processed" | "reviewed";
  extraction_method: string;
  extraction_warnings: string[];
  summary: string | null;
  total_experience_months: number | null;
  certifications: string[];
  achievements: string[];
  detected_preferences: {
    employment_types?: string[];
    work_arrangements?: string[];
    locations?: string[];
    titles?: string[];
  };
  is_active: boolean;
  raw_text_stored: boolean;
  file_retained: boolean;
  skills: ResumeSkill[];
  education: Education[];
  experience: Experience[];
  projects: ResumeProject[];
  created_at: string;
  updated_at: string;
}

export interface ResumeProfileUpdate {
  skills?: { skill: string }[];
  education?: Omit<Education, "source">[];
  experience?: Omit<Experience, "source">[];
  projects?: Omit<ResumeProject, "source">[];
  certifications?: string[];
  achievements?: string[];
  summary?: string | null;
  total_experience_months?: number | null;
}

export interface JobSkill {
  skill: string;
  category: string | null;
  requirement: Requirement;
  evidence: string | null;
}

export interface JobSummary {
  id: string;
  title: string;
  company: string;
  location: string | null;
  work_arrangement: WorkArrangement | "unknown";
  employment_type: EmploymentType | "unknown";
  experience_level: ExperienceLevel;
  category: string | null;
  salary_min: string | null;
  salary_max: string | null;
  salary_currency: string | null;
  salary_interval: string | null;
  salary_text: string | null;
  posted_at: string | null;
  deadline: string | null;
  apply_url: string;
  last_checked_at: string;
  freshness: Freshness;
  status: string;
  provider: string;
  source_name: string;
  is_demo: boolean;
  is_saved: boolean;
  required_skills: string[];
}

export interface JobDetail extends JobSummary {
  description: string;
  required_qualifications: string[];
  preferred_qualifications: string[];
  skills: JobSkill[];
  min_years_experience: number | null;
  department: string | null;
  country: string | null;
  source_attribution: string;
}

export interface JobFilters {
  q?: string;
  employment_types?: string[];
  work_arrangements?: string[];
  experience_levels?: string[];
  categories?: string[];
  location?: string;
  skills?: string[];
  salary_min?: number | null;
  salary_currency?: string | null;
  checked_within_days?: number | null;
  include_demo?: boolean;
  saved_only?: boolean;
  sort?: "recently_checked" | "posted" | "title";
  page?: number;
  page_size?: number;
}

export interface FacetCount {
  value: string;
  count: number;
}

export interface Facets {
  total_active: number;
  live_active: number;
  demo_active: number;
  categories: FacetCount[];
  locations: FacetCount[];
  skills: FacetCount[];
  last_checked_at: string | null;
}

export interface JobSource {
  id: string;
  provider: string;
  identifier: string;
  display_name: string;
  is_demo: boolean;
  enabled: boolean;
  last_fetched_at: string | null;
  last_status: string;
  last_error: string | null;
  last_fetch_count: number | null;
  active_listings: number;
}

export interface ProviderStatus {
  provider: string;
  name: string;
  configured: boolean;
  sources: string[];
  docs: string;
  notes: string;
  config_variable: string;
}

export interface SourcesResponse {
  sources: JobSource[];
  providers: ProviderStatus[];
  demo_enabled: boolean;
  unsupported_note: string;
}

export interface RefreshItem {
  provider: string;
  identifier: string;
  status: "ok" | "error" | "rate_limited" | "skipped_cooldown";
  fetched: number;
  created: number;
  updated: number;
  expired: number;
  duplicates: number;
  skipped_invalid: number;
  message: string | null;
}

export type ComponentKey =
  | "semantic_similarity"
  | "required_skill_coverage"
  | "preferred_skill_coverage"
  | "experience_compatibility"
  | "preference_compatibility"
  | "profile_relevance";

export type Components = Record<ComponentKey, number | null>;
export type Weights = Record<ComponentKey, number>;

export interface MatchSummary {
  id: string;
  run_id: string;
  rank: number;
  score: number;
  evidence_coverage: number;
  components: Components;
  matched_skills: string[];
  related_skills: string[];
  missing_required: string[];
  missing_preferred: string[];
  top_reason: string | null;
  job: JobSummary;
}

export interface MatchRun {
  run_id: string;
  created_at: string;
  semantic_backend: string;
  model_version: string;
  weights: Weights;
  total_considered: number;
  results: MatchSummary[];
  disclaimer: string;
}

export interface MatchPage {
  run_id: string | null;
  created_at: string | null;
  semantic_backend: string | null;
  model_version: string | null;
  weights: Weights | null;
  items: MatchSummary[];
  total: number;
  page: number;
  page_size: number;
  disclaimer: string;
}

export interface MatchEvidence {
  kind:
    | "reason"
    | "matched_skill"
    | "related_skill"
    | "missing_required"
    | "missing_preferred"
    | "relevant_experience"
    | "experience_level"
    | "preference"
    | "caveat";
  label: string;
  detail: string | null;
  requirement: Requirement | null;
}

export interface MatchDetail {
  id: string;
  run_id: string;
  rank: number;
  score: number;
  evidence_coverage: number;
  components: Components;
  weights: Weights;
  component_labels: Record<ComponentKey, string>;
  semantic_backend: string;
  model_version: string;
  created_at: string;
  evidence: MatchEvidence[];
  job: JobDetail;
  feedback: "relevant" | "not_relevant" | null;
  disclaimer: string;
}

export interface MatchRequest {
  preset?: "balanced" | "skills_first" | "preferences_first";
  weights?: Partial<Weights> | null;
  filters?: {
    employment_types?: string[];
    work_arrangements?: string[];
    experience_levels?: string[];
    categories?: string[];
    location?: string | null;
    include_demo?: boolean;
  };
  limit?: number;
}

export interface SavedJob {
  id: string;
  note: string | null;
  created_at: string;
  job: JobSummary;
}

export interface HistoryEntry {
  id: string;
  kind: "search" | "match";
  query: Record<string, unknown>;
  result_count: number;
  run_id: string | null;
  created_at: string;
}

export interface GapExample {
  job_id: string;
  title: string;
  company: string;
  requirement: Requirement;
  evidence: string | null;
  is_demo: boolean;
}

export interface SkillGap {
  skill: string;
  category: string | null;
  required_count: number;
  preferred_count: number;
  priority: number;
  in_development_list: boolean;
  examples: GapExample[];
}

export interface SkillGapReport {
  basis: string;
  jobs_analyzed: number;
  target_titles: string[];
  identified_skills: { skill: string; category: string | null; jobs_requesting: number }[];
  gaps: SkillGap[];
  skill_frequency: { skill: string; jobs: number; share: number; user_has: boolean }[];
  total_listings: number;
  note: string;
}

export interface SkillRecommendation {
  skill: string;
  why: string;
  project_idea: string;
  how_to_demonstrate: string;
  resources: { title: string; url: string; provider: string; cost: string }[];
  resources_note: string | null;
}

export interface Recommendations {
  basis: string;
  recommendations: SkillRecommendation[];
  note: string;
}

export interface EvaluationSummary {
  status: "evaluated" | "not_evaluated";
  source: string | null;
  report: Record<string, unknown> | null;
  message: string;
}

export type AssistantTask =
  | "explain_requirements"
  | "resume_suggestions"
  | "rewrite_bullet"
  | "portfolio_projects"
  | "interview_questions"
  | "cover_letter";

export interface AssistantResponse {
  task: AssistantTask;
  mode_used: "template" | "llm";
  model: string | null;
  title: string;
  sections: { heading: string; items: string[] }[];
  text: string;
  review_required: boolean;
  notice: string;
  fallback_reason: string | null;
}

export interface AssistantStatus {
  llm_configured: boolean;
  provider: string | null;
  consent_given: boolean;
  data_shared_with_llm: string[];
  note: string;
}
