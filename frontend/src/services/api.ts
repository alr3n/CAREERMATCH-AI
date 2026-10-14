import type {
  AssistantResponse,
  AssistantStatus,
  AssistantTask,
  EvaluationSummary,
  Facets,
  HistoryEntry,
  JobDetail,
  JobFilters,
  JobSummary,
  MatchDetail,
  MatchPage,
  MatchRequest,
  MatchRun,
  Page,
  ProfileResponse,
  ProfileUpdate,
  Recommendations,
  RefreshItem,
  Resume,
  ResumeProfileUpdate,
  ResumeSummary,
  SavedJob,
  SkillGapReport,
  SourcesResponse,
  TokenResponse,
} from "../types/api";

export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }
}

// The access token lives in sessionStorage: it survives reloads but is cleared
// when the tab closes. See docs/PRIVACY_AND_SECURITY.md for the trade-offs.
const TOKEN_KEY = "careermatch.token";
let unauthorizedHandler: (() => void) | null = null;

export const tokenStore = {
  get: (): string | null => {
    try {
      return sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (token: string) => {
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* storage unavailable */
    }
  },
  clear: () => {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable */
    }
  },
};

export function onUnauthorized(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

type Query = Record<string, string | number | boolean | string[] | null | undefined>;

function buildUrl(path: string, query?: Query): string {
  const url = new URL(`${API_BASE}/api/v1${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === "") continue;
      if (Array.isArray(value)) value.forEach((v) => url.searchParams.append(key, v));
      else url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function request<T>(method: string, path: string, options: { body?: unknown; query?: Query; form?: FormData } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (options.form) body = options.form;
  else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), { method, headers, body });
  } catch {
    throw new ApiError(0, "network_error", "Can't reach the CareerMatch AI server. Check that the backend is running and try again.");
  }
  if (response.status === 204) return undefined as T;
  let data: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (!response.ok) {
    const err = (data as { error?: { code?: string; message?: string; details?: unknown } } | null)?.error;
    if (response.status === 401 && token) {
      tokenStore.clear();
      unauthorizedHandler?.();
    }
    throw new ApiError(response.status, err?.code ?? "error", err?.message ?? `Request failed (${response.status})`, err?.details);
  }
  return data as T;
}

export const api = {
  // auth
  register: (email: string, password: string) => request<TokenResponse>("POST", "/auth/register", { body: { email, password } }),
  login: (email: string, password: string) => request<TokenResponse>("POST", "/auth/login", { body: { email, password } }),

  // profile
  getProfile: () => request<ProfileResponse>("GET", "/profile"),
  updateProfile: (body: ProfileUpdate) => request<ProfileResponse>("PATCH", "/profile", { body }),
  deleteAccount: () => request<void>("DELETE", "/profile"),

  // resumes
  listResumes: () => request<ResumeSummary[]>("GET", "/resumes"),
  getResume: (id: string) => request<Resume>("GET", `/resumes/${id}`),
  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Resume>("POST", "/resumes/upload", { form });
  },
  correctResume: (id: string, body: ResumeProfileUpdate) => request<Resume>("PATCH", `/resumes/${id}/profile`, { body }),
  deleteResume: (id: string) => request<void>("DELETE", `/resumes/${id}`),

  // jobs
  listJobs: (filters: JobFilters) => request<Page<JobSummary>>("GET", "/jobs", { query: filters as Query }),
  searchJobs: (filters: JobFilters) => request<Page<JobSummary>>("POST", "/jobs/search", { body: filters }),
  getJob: (id: string) => request<JobDetail>("GET", `/jobs/${id}`),
  facets: () => request<Facets>("GET", "/jobs/facets"),
  sources: () => request<SourcesResponse>("GET", "/jobs/sources"),
  refreshJobs: () => request<{ results: RefreshItem[]; refreshed_at: string }>("POST", "/jobs/refresh"),

  // matches
  runMatches: (body: MatchRequest) => request<MatchRun>("POST", "/matches", { body }),
  listMatches: (params: { run_id?: string; page?: number; page_size?: number } = {}) =>
    request<MatchPage>("GET", "/matches", { query: params }),
  getMatch: (id: string) => request<MatchDetail>("GET", `/matches/${id}`),
  sendFeedback: (id: string, rating: "relevant" | "not_relevant") => request<void>("POST", `/matches/${id}/feedback`, { body: { rating } }),

  // saved jobs
  listSaved: (page = 1, page_size = 50) => request<Page<SavedJob>>("GET", "/saved-jobs", { query: { page, page_size } }),
  saveJob: (job_id: string) => request<SavedJob>("POST", "/saved-jobs", { body: { job_id } }),
  unsaveJob: (job_id: string) => request<void>("DELETE", `/saved-jobs/${job_id}`),

  // skills
  skillGaps: (top_k = 20) => request<SkillGapReport>("GET", "/skills/gaps", { query: { top_k } }),
  skillRecommendations: () => request<Recommendations>("GET", "/skills/recommendations"),

  // history
  history: (page = 1, page_size = 50) => request<Page<HistoryEntry>>("GET", "/history", { query: { page, page_size } }),
  clearHistory: () => request<void>("DELETE", "/history"),

  // evaluation
  evaluation: () => request<EvaluationSummary>("GET", "/evaluation/summary"),

  // assistant
  assistantStatus: () => request<AssistantStatus>("GET", "/assistant/status"),
  assistant: (body: { task: AssistantTask; job_id: string; input_text?: string; mode?: "auto" | "template" | "llm" }) =>
    request<AssistantResponse>("POST", "/assistant", { body }),
};
