import { useState, type FormEvent } from "react";
import type { Facets, JobFilters as Filters } from "../types/api";
import { CheckboxGroup } from "./CheckboxGroup";

interface Props {
  value: Filters;
  facets?: Facets;
  onApply: (filters: Filters) => void;
  showSearch?: boolean;
  showSalary?: boolean;
}

const TYPES = [
  { value: "internship", label: "Internship" },
  { value: "full_time", label: "Full-time" },
  { value: "part_time", label: "Part-time" },
  { value: "contract", label: "Contract" },
];
const ARRANGEMENTS = [
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "On-site" },
];
const LEVELS = [
  { value: "internship", label: "Internship" },
  { value: "entry", label: "Entry level" },
  { value: "mid", label: "Mid level" },
  { value: "senior", label: "Senior" },
];

export function JobFilters({ value, facets, onApply, showSearch = true, showSalary = true }: Props) {
  const [draft, setDraft] = useState<Filters>(value);
  const set = <K extends keyof Filters>(key: K, v: Filters[K]) => setDraft((d) => ({ ...d, [key]: v }));

  function submit(e: FormEvent) {
    e.preventDefault();
    onApply({ ...draft, page: 1 });
  }

  function reset() {
    const cleared: Filters = { include_demo: true, sort: draft.sort ?? "recently_checked", page: 1 };
    setDraft(cleared);
    onApply(cleared);
  }

  return (
    <form onSubmit={submit} className="panel space-y-5 p-5" aria-label="Job filters">
      {showSearch && (
        <div>
          <label htmlFor="filter-q" className="field-label">
            Keywords
          </label>
          <input id="filter-q" className="field-input" value={draft.q ?? ""} onChange={(e) => set("q", e.target.value)} placeholder="e.g. data analyst, React" />
        </div>
      )}
      <CheckboxGroup legend="Employment type" options={TYPES} values={draft.employment_types ?? []} onChange={(v) => set("employment_types", v)} />
      <CheckboxGroup legend="Work arrangement" options={ARRANGEMENTS} values={draft.work_arrangements ?? []} onChange={(v) => set("work_arrangements", v)} />
      <CheckboxGroup legend="Experience level" options={LEVELS} values={draft.experience_levels ?? []} onChange={(v) => set("experience_levels", v)} />
      <div>
        <label htmlFor="filter-location" className="field-label">
          Location
        </label>
        <input
          id="filter-location"
          className="field-input"
          list="filter-locations"
          value={draft.location ?? ""}
          onChange={(e) => set("location", e.target.value)}
          placeholder="e.g. Makati, Cebu"
        />
        <datalist id="filter-locations">
          {facets?.locations.map((l) => <option key={l.value} value={l.value} />)}
        </datalist>
      </div>
      <div>
        <label htmlFor="filter-category" className="field-label">
          Job category
        </label>
        <select
          id="filter-category"
          className="field-input"
          value={draft.categories?.[0] ?? ""}
          onChange={(e) => set("categories", e.target.value ? [e.target.value] : [])}
        >
          <option value="">Any category</option>
          {facets?.categories.map((c) => (
            <option key={c.value} value={c.value}>
              {c.value} ({c.count})
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="filter-skill" className="field-label">
          Requires skill
        </label>
        <select
          id="filter-skill"
          className="field-input"
          value={draft.skills?.[0] ?? ""}
          onChange={(e) => set("skills", e.target.value ? [e.target.value] : [])}
        >
          <option value="">Any skill</option>
          {facets?.skills.map((s) => (
            <option key={s.value} value={s.value}>
              {s.value} ({s.count})
            </option>
          ))}
        </select>
      </div>
      {showSalary && (
        <div>
          <label htmlFor="filter-salary" className="field-label">
            Minimum monthly salary (PHP)
          </label>
          <input
            id="filter-salary"
            className="field-input num"
            type="number"
            min={0}
            step={1000}
            value={draft.salary_min ?? ""}
            onChange={(e) => {
              const v = e.target.value ? Number(e.target.value) : null;
              setDraft((d) => ({ ...d, salary_min: v, salary_currency: v ? "PHP" : null }));
            }}
          />
          <p className="mt-1 text-xs text-muted">Only listings that publish a salary are shown when this is set.</p>
        </div>
      )}
      <div>
        <label htmlFor="filter-checked" className="field-label">
          Last checked
        </label>
        <select
          id="filter-checked"
          className="field-input"
          value={draft.checked_within_days ?? ""}
          onChange={(e) => set("checked_within_days", e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">Any time</option>
          <option value="1">Within 24 hours</option>
          <option value="7">Within 7 days</option>
          <option value="30">Within 30 days</option>
        </select>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" className="accent-teal" checked={draft.saved_only ?? false} onChange={(e) => set("saved_only", e.target.checked)} />
        Saved jobs only
      </label>
      {facets && facets.demo_active > 0 && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="accent-teal" checked={draft.include_demo ?? true} onChange={(e) => set("include_demo", e.target.checked)} />
          Include demo listings ({facets.demo_active})
        </label>
      )}
      <div className="flex gap-2">
        <button type="submit" className="btn-primary">
          Apply filters
        </button>
        <button type="button" className="btn-ghost" onClick={reset}>
          Clear
        </button>
      </div>
    </form>
  );
}
