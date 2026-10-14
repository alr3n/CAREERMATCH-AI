import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { job, match, weights } from "../test/fixtures";
import { JobCard } from "./JobCard";
import { JobFilters } from "./JobFilters";
import { MatchScore } from "./MatchScore";
import { SkillGapPanel } from "./SkillGapPanel";
import { EmptyState, ErrorState } from "./States";

describe("MatchScore", () => {
  it("shows the rounded score with an accessible description and coverage note", () => {
    render(<MatchScore score={72.4} components={match().components} weights={weights} evidenceCoverage={0.95} />);
    expect(screen.getByText("72")).toBeInTheDocument();
    expect(screen.getByText(/Compatibility score 72 out of 100, based on 95% of the scoring weight/)).toBeInTheDocument();
    expect(screen.getByText("Based on 95% of the scoring weight")).toBeInTheDocument();
  });

  it("lists every component, marking unevaluated ones", () => {
    render(<MatchScore score={72.4} components={match().components} weights={weights} evidenceCoverage={0.95} variant="full" />);
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(7);
    expect(within(table).getByText("not enough info")).toBeInTheDocument();
  });
});

describe("JobCard", () => {
  it("labels demo data and shows matched and missing skills", () => {
    render(
      <MemoryRouter>
        <JobCard job={job()} match={match()} weights={weights} detailHref="/app/matches/match-1" onToggleSave={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Demo data, not a real job")).toBeInTheDocument();
    expect(screen.getByText("Power BI")).toBeInTheDocument();
    expect(screen.getByText("Required, not found in your resume")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View details" })).toHaveAttribute("href", "/app/matches/match-1");
    expect(screen.getByRole("link", { name: /Demo link/ })).toHaveAttribute("href", "https://example.com/demo-jobs/1");
  });

  it("calls the save handler", async () => {
    const onToggle = vi.fn();
    render(
      <MemoryRouter>
        <JobCard job={job()} detailHref="/x" onToggleSave={onToggle} />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onToggle).toHaveBeenCalledWith(expect.objectContaining({ id: "job-1" }));
  });
});

describe("JobFilters", () => {
  it("applies the selected filters and can clear them", async () => {
    const onApply = vi.fn();
    render(<JobFilters value={{ include_demo: true }} onApply={onApply} />);
    await userEvent.type(screen.getByLabelText("Keywords"), "analyst");
    const types = screen.getByRole("group", { name: "Employment type" });
    await userEvent.click(within(types).getByLabelText("Internship"));
    await userEvent.click(screen.getByLabelText("Remote"));
    await userEvent.type(screen.getByLabelText("Location"), "Cebu");
    await userEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    expect(onApply).toHaveBeenLastCalledWith(
      expect.objectContaining({ q: "analyst", employment_types: ["internship"], work_arrangements: ["remote"], location: "Cebu", page: 1 }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(onApply).toHaveBeenLastCalledWith(expect.objectContaining({ include_demo: true, page: 1 }));
    expect(onApply.mock.lastCall?.[0].q).toBeUndefined();
  });
});

describe("SkillGapPanel", () => {
  it("shows the posting evidence for each gap", () => {
    render(
      <MemoryRouter>
        <SkillGapPanel
          jobsAnalyzed={5}
          gaps={[
            {
              skill: "Power BI",
              category: "Data & Analytics",
              required_count: 2,
              preferred_count: 1,
              priority: 5,
              in_development_list: true,
              examples: [{ job_id: "j1", title: "BI Intern", company: "Co", requirement: "required", evidence: "Power BI dashboards", is_demo: false }],
            },
          ]}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText("Required in 2")).toBeInTheDocument();
    expect(screen.getByText(/Power BI dashboards/)).toBeInTheDocument();
    expect(screen.getByText("on your learning list")).toBeInTheDocument();
  });

  it("handles no gaps", () => {
    render(<SkillGapPanel gaps={[]} jobsAnalyzed={3} />);
    expect(screen.getByText(/Every skill detected/)).toBeInTheDocument();
  });
});

describe("States", () => {
  it("error state offers a retry", async () => {
    const retry = vi.fn();
    render(<ErrorState error={new Error("Server unavailable")} onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Server unavailable");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalled();
  });

  it("empty state renders its action", () => {
    render(<EmptyState title="Nothing here" action={<button type="button">Do it</button>} />);
    expect(screen.getByRole("heading", { name: "Nothing here" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Do it" })).toBeInTheDocument();
  });
});
