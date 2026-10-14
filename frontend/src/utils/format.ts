import type { ComponentKey, EmploymentType, ExperienceLevel, WorkArrangement } from "../types/api";

export const ARRANGEMENT_LABEL: Record<WorkArrangement | "unknown", string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
  unknown: "Arrangement not stated",
};

export const EMPLOYMENT_LABEL: Record<EmploymentType | "unknown", string> = {
  full_time: "Full-time",
  part_time: "Part-time",
  contract: "Contract",
  internship: "Internship",
  temporary: "Temporary",
  unknown: "Type not stated",
};

export const LEVEL_LABEL: Record<ExperienceLevel, string> = {
  internship: "Internship",
  entry: "Entry level",
  mid: "Mid level",
  senior: "Senior",
  unknown: "Level not stated",
};

export const STAGE_LABEL: Record<string, string> = {
  student: "Student",
  fresh_graduate: "Fresh graduate",
  entry_level: "Entry-level professional",
  experienced: "Experienced professional",
  career_transition: "Changing careers",
};

export const COMPONENT_ORDER: ComponentKey[] = [
  "semantic_similarity",
  "required_skill_coverage",
  "preferred_skill_coverage",
  "experience_compatibility",
  "preference_compatibility",
  "profile_relevance",
];

export const COMPONENT_SHORT: Record<ComponentKey, string> = {
  semantic_similarity: "Text similarity",
  required_skill_coverage: "Required skills",
  preferred_skill_coverage: "Preferred skills",
  experience_compatibility: "Experience fit",
  preference_compatibility: "Your preferences",
  profile_relevance: "Target roles",
};

export const COMPONENT_COLOR: Record<ComponentKey, string> = {
  semantic_similarity: "bg-ledger-semantic",
  required_skill_coverage: "bg-ledger-required",
  preferred_skill_coverage: "bg-ledger-preferred",
  experience_compatibility: "bg-ledger-experience",
  preference_compatibility: "bg-ledger-preference",
  profile_relevance: "bg-ledger-relevance",
};

export function formatDate(value: string | null | undefined): string {
  if (!value) return "Not stated";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function timeAgo(value: string | null | undefined, now: Date = new Date()): string {
  if (!value) return "never";
  const diff = now.getTime() - new Date(value).getTime();
  const minutes = Math.round(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export function formatSalary(min: string | null, max: string | null, currency: string | null, interval: string | null): string | null {
  if (!min && !max) return null;
  const fmt = (v: string) => Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 });
  const range = min && max ? `${fmt(min)}–${fmt(max)}` : fmt((min ?? max) as string);
  const per = interval?.includes("year") ? "/year" : interval?.includes("month") ? "/month" : interval?.includes("hour") ? "/hour" : "";
  return `${currency ?? ""} ${range}${per}`.trim();
}

export function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "n/a" : `${Math.round(value * 100)}%`;
}
