import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { AuthProvider } from "../hooks/useAuth";
import { api, tokenStore } from "../services/api";
import { job } from "../test/fixtures";
import type { Facets, Page, JobSummary, SourcesResponse } from "../types/api";
import { JobsPage, NO_LIVE_LISTINGS } from "./JobsPage";

const facets: Facets = {
  total_active: 2,
  with_salary: 1,
  categories: [],
  locations: [],
  skills: [],
  platforms: [{ value: "Lever", count: 2 }],
  companies: [{ value: "Test Company", count: 2 }],
  last_checked_at: new Date().toISOString(),
};
const sources: SourcesResponse = {
  sources: [],
  providers: [],
  last_successful_refresh_at: null,
  location_filter: "ph",
  unsupported_note: "No scraping.",
};
const page = (items: JobSummary[]): Page<JobSummary> => ({ items, total: items.length, page: 1, page_size: 20 });

function renderJobs() {
  return render(
    <MemoryRouter initialEntries={["/app/jobs"]}>
      <Routes>
        <Route path="/app/jobs" element={<JobsPage />} />
        <Route path="/app/jobs/:jobId" element={<p>Detail page</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("JobsPage", () => {
  beforeEach(() => {
    vi.spyOn(api, "facets").mockResolvedValue(facets);
    vi.spyOn(api, "sources").mockResolvedValue(sources);
  });

  it("searches with filters and records the search", async () => {
    vi.spyOn(api, "listJobs").mockResolvedValue(page([job(), job({ id: "job-2", title: "HR Intern" })]));
    const search = vi.spyOn(api, "searchJobs").mockResolvedValue(page([job({ id: "job-3", title: "Remote BI Intern" })]));
    renderJobs();
    expect(await screen.findByText("2 listings")).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText("Remote"));
    await userEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    expect(await screen.findByText("Remote BI Intern")).toBeInTheDocument();
    expect(search).toHaveBeenCalledWith(expect.objectContaining({ work_arrangements: ["remote"] }));
  });

  it("saves and unsaves a job", async () => {
    vi.spyOn(api, "listJobs").mockResolvedValue(page([job()]));
    const save = vi.spyOn(api, "saveJob").mockResolvedValue({ id: "s1", note: null, created_at: "", job: job({ is_saved: true }) });
    const unsave = vi.spyOn(api, "unsaveJob").mockResolvedValue(undefined);
    renderJobs();
    const card = await screen.findByRole("article");
    await userEvent.click(within(card).getByRole("button", { name: "Save" }));
    expect(save).toHaveBeenCalledWith("job-1");
    const savedButton = await within(card).findByRole("button", { name: "Saved" });
    expect(savedButton).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(savedButton);
    expect(unsave).toHaveBeenCalledWith("job-1");
    expect(await within(card).findByRole("button", { name: "Save" })).toBeInTheDocument();
  });

  it("navigates to job details", async () => {
    vi.spyOn(api, "listJobs").mockResolvedValue(page([job()]));
    renderJobs();
    await userEvent.click(await screen.findByRole("link", { name: "Data Analyst Intern" }));
    expect(await screen.findByText("Detail page")).toBeInTheDocument();
  });

  it("searches by keyword from the search bar", async () => {
    vi.spyOn(api, "listJobs").mockResolvedValue(page([job()]));
    const search = vi.spyOn(api, "searchJobs").mockResolvedValue(page([job({ id: "job-9", title: "Grab Analyst" })]));
    renderJobs();
    await screen.findByText("1 listing");
    await userEvent.type(screen.getByLabelText("Job title, keyword or company"), "Grab");
    await userEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(await screen.findByText("Grab Analyst")).toBeInTheDocument();
    expect(search).toHaveBeenCalledWith(expect.objectContaining({ q: "Grab", page: 1 }));
    expect(screen.getByText(/Last updated/)).toBeInTheDocument();
  });

  it("says when no live listings are available instead of showing sample jobs", async () => {
    vi.spyOn(api, "facets").mockResolvedValue({ ...facets, total_active: 0, platforms: [], last_checked_at: null });
    vi.spyOn(api, "listJobs").mockResolvedValue(page([]));
    renderJobs();
    expect(await screen.findByText(NO_LIVE_LISTINGS)).toBeInTheDocument();
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });

  it("reports unavailable sources", async () => {
    vi.spyOn(api, "sources").mockResolvedValue({
      ...sources,
      sources: [
        { id: "s1", provider: "lever", identifier: "coins", display_name: "Coins", enabled: true, last_fetched_at: null,
          last_status: "error", last_error: "The provider did not respond in time", last_fetch_count: null, active_listings: 3 },
      ],
    });
    vi.spyOn(api, "listJobs").mockResolvedValue(page([job()]));
    renderJobs();
    expect(await screen.findByText("1 source is temporarily unavailable")).toBeInTheDocument();
    expect(screen.getByText(/did not respond in time/)).toBeInTheDocument();
  });

  it("shows an empty state and errors", async () => {
    vi.spyOn(api, "listJobs").mockResolvedValueOnce(page([]));
    renderJobs();
    expect(await screen.findByText("No listings match your search")).toBeInTheDocument();
    vi.spyOn(api, "searchJobs").mockRejectedValueOnce(new Error("Can't reach the CareerMatch AI server."));
    await userEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Can't reach the CareerMatch AI server.");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});

describe("Routing", () => {
  it("redirects unauthenticated users from the dashboard to sign in", async () => {
    tokenStore.clear();
    render(
      <MemoryRouter initialEntries={["/app/matches"]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows server errors on sign in", async () => {
    vi.spyOn(api, "login").mockRejectedValue(new Error("Incorrect email or password"));
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-pass1");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password");
  });

  it("renders the landing page without invented statistics", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Your skills. Your next opportunity.");
    expect(screen.getByText("Illustrative example of a recommendation")).toBeInTheDocument();
    await waitFor(() => expect(document.body.textContent).not.toMatch(/users|testimonial|hired \d+/i));
  });
});
