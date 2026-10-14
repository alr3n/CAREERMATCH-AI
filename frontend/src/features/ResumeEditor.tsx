import { useId, useMemo, useState } from "react";
import { SkillChip } from "../components/SkillChip";
import { InlineStatus } from "../components/States";
import { TagInput } from "../components/TagInput";
import type { Education, Experience, Resume, ResumeProfileUpdate, ResumeProject } from "../types/api";

type EduRow = Omit<Education, "source">;
type ExpRow = Omit<Experience, "source">;
type ProjRow = Omit<ResumeProject, "source">;

const blankEdu: EduRow = { institution: "", degree: "", field_of_study: "", start_date: "", end_date: "" };
const blankExp: ExpRow = { title: "", organization: "", start_date: "", end_date: "", duration_months: null, is_internship: false, description: "" };
const blankProj: ProjRow = { name: "", description: "", skills: [] };

function strip<T extends { source?: string }>(rows: T[]): Omit<T, "source">[] {
  return rows.map(({ source: _source, ...rest }) => rest);
}

const nullIfEmpty = (v: string | null | undefined) => (v && v.trim() ? v.trim() : null);

interface Props {
  resume: Resume;
  onSave: (update: ResumeProfileUpdate) => Promise<void>;
}

export function ResumeEditor({ resume, onSave }: Props) {
  const [skills, setSkills] = useState<string[]>(resume.skills.map((s) => s.skill));
  const [education, setEducation] = useState<EduRow[]>(strip(resume.education));
  const [experience, setExperience] = useState<ExpRow[]>(strip(resume.experience));
  const [projects, setProjects] = useState<ProjRow[]>(strip(resume.projects));
  const [certifications, setCertifications] = useState<string[]>(resume.certifications);
  const [summary, setSummary] = useState(resume.summary ?? "");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<{ message: string | null; tone: "info" | "success" | "error" }>({ message: null, tone: "info" });
  const evidence = useMemo(() => new Map(resume.skills.map((s) => [s.skill, s])), [resume.skills]);

  async function save() {
    const invalidProject = projects.find((p) => !p.name.trim());
    if (invalidProject) {
      setStatus({ message: "Every project needs a name (or remove the empty project).", tone: "error" });
      return;
    }
    setSaving(true);
    setStatus({ message: null, tone: "info" });
    try {
      await onSave({
        skills: skills.map((skill) => ({ skill })),
        education: education
          .filter((e) => e.institution?.trim() || e.degree?.trim())
          .map((e) => ({
            institution: nullIfEmpty(e.institution),
            degree: nullIfEmpty(e.degree),
            field_of_study: nullIfEmpty(e.field_of_study),
            start_date: nullIfEmpty(e.start_date),
            end_date: nullIfEmpty(e.end_date),
          })),
        experience: experience
          .filter((e) => e.title?.trim() || e.organization?.trim())
          .map((e) => ({
            ...e,
            title: nullIfEmpty(e.title),
            organization: nullIfEmpty(e.organization),
            start_date: nullIfEmpty(e.start_date),
            end_date: nullIfEmpty(e.end_date),
            description: nullIfEmpty(e.description),
          })),
        projects: projects.map((p) => ({ ...p, name: p.name.trim(), description: nullIfEmpty(p.description) })),
        certifications,
        summary: nullIfEmpty(summary),
      });
      setStatus({ message: "Your corrections are saved. Matching will use them.", tone: "success" });
    } catch (e) {
      setStatus({ message: e instanceof Error ? e.message : "Saving failed.", tone: "error" });
    } finally {
      setSaving(false);
    }
  }

  const update = <T,>(rows: T[], setRows: (r: T[]) => void, i: number, patch: Partial<T>) =>
    setRows(rows.map((row, idx) => (idx === i ? { ...row, ...patch } : row)));

  return (
    <div className="space-y-10">
      <section aria-labelledby="skills-heading">
        <h2 id="skills-heading" className="text-lg font-semibold">
          Skills
        </h2>
        <p className="mt-1 max-w-prose text-sm text-muted">
          Remove anything that isn't right and add skills we missed. Hover a skill to see the line it was found on.
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {skills.map((s) => {
            const info = evidence.get(s);
            return (
              <SkillChip
                key={s}
                skill={s}
                variant={info?.source === "extracted" ? "matched" : "user"}
                title={info?.evidence ? `Found in: “${info.evidence}”` : "Added by you"}
                onRemove={() => setSkills(skills.filter((x) => x !== s))}
              />
            );
          })}
          {skills.length === 0 && <p className="text-sm text-muted">No skills yet. Add some below.</p>}
        </div>
        <div className="mt-4 max-w-xl">
          <TagInput label="Add a skill" values={[]} onChange={(v) => v[0] && !skills.includes(v[0]) && setSkills([...skills, v[0]])} placeholder="e.g. Power BI" />
        </div>
      </section>

      <section aria-labelledby="summary-heading">
        <label id="summary-heading" htmlFor="summary" className="text-lg font-semibold">
          Summary or objective
        </label>
        <textarea id="summary" className="field-input mt-2 min-h-[5rem] max-w-prose" maxLength={1000} value={summary} onChange={(e) => setSummary(e.target.value)} />
      </section>

      <section aria-labelledby="edu-heading">
        <div className="flex items-center justify-between">
          <h2 id="edu-heading" className="text-lg font-semibold">
            Education
          </h2>
          <button type="button" className="btn-ghost" onClick={() => setEducation([...education, { ...blankEdu }])}>
            Add education
          </button>
        </div>
        {education.length === 0 && <p className="mt-2 text-sm text-muted">No education entries found. Add one if it's relevant.</p>}
        <div className="mt-3 space-y-3">
          {education.map((e, i) => (
            <fieldset key={i} className="panel grid gap-3 p-4 md:grid-cols-2">
              <legend className="sr-only">Education entry {i + 1}</legend>
              <Text label="School" value={e.institution} onChange={(v) => update(education, setEducation, i, { institution: v })} />
              <Text label="Degree" value={e.degree} onChange={(v) => update(education, setEducation, i, { degree: v })} />
              <Text label="Field of study" value={e.field_of_study} onChange={(v) => update(education, setEducation, i, { field_of_study: v })} />
              <div className="grid grid-cols-2 gap-3">
                <Text label="Start" value={e.start_date} onChange={(v) => update(education, setEducation, i, { start_date: v })} />
                <Text label="End" value={e.end_date} onChange={(v) => update(education, setEducation, i, { end_date: v })} />
              </div>
              <div className="md:col-span-2">
                <button type="button" className="text-sm text-danger" onClick={() => setEducation(education.filter((_, idx) => idx !== i))}>
                  Remove this entry
                </button>
              </div>
            </fieldset>
          ))}
        </div>
      </section>

      <section aria-labelledby="exp-heading">
        <div className="flex items-center justify-between">
          <h2 id="exp-heading" className="text-lg font-semibold">
            Experience and internships
          </h2>
          <button type="button" className="btn-ghost" onClick={() => setExperience([...experience, { ...blankExp }])}>
            Add experience
          </button>
        </div>
        {experience.length === 0 && <p className="mt-2 text-sm text-muted">No experience entries found. Internships, part-time work and volunteering all count.</p>}
        <div className="mt-3 space-y-3">
          {experience.map((e, i) => (
            <fieldset key={i} className="panel grid gap-3 p-4 md:grid-cols-2">
              <legend className="sr-only">Experience entry {i + 1}</legend>
              <Text label="Role" value={e.title} onChange={(v) => update(experience, setExperience, i, { title: v })} />
              <Text label="Organisation" value={e.organization} onChange={(v) => update(experience, setExperience, i, { organization: v })} />
              <div className="grid grid-cols-3 gap-3 md:col-span-2">
                <Text label="Start" value={e.start_date} onChange={(v) => update(experience, setExperience, i, { start_date: v })} />
                <Text label="End" value={e.end_date} onChange={(v) => update(experience, setExperience, i, { end_date: v })} />
                <div>
                  <label className="field-label" htmlFor={`months-${i}`}>
                    Months
                  </label>
                  <input
                    id={`months-${i}`}
                    type="number"
                    min={0}
                    max={600}
                    className="field-input num"
                    value={e.duration_months ?? ""}
                    onChange={(ev) => update(experience, setExperience, i, { duration_months: ev.target.value ? Number(ev.target.value) : null })}
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm md:col-span-2">
                <input type="checkbox" className="accent-teal" checked={e.is_internship} onChange={(ev) => update(experience, setExperience, i, { is_internship: ev.target.checked })} />
                This was an internship or OJT
              </label>
              <div className="md:col-span-2">
                <label className="field-label" htmlFor={`desc-${i}`}>
                  What you did
                </label>
                <textarea id={`desc-${i}`} className="field-input min-h-[4rem]" maxLength={3000} value={e.description ?? ""} onChange={(ev) => update(experience, setExperience, i, { description: ev.target.value })} />
              </div>
              <div className="md:col-span-2">
                <button type="button" className="text-sm text-danger" onClick={() => setExperience(experience.filter((_, idx) => idx !== i))}>
                  Remove this entry
                </button>
              </div>
            </fieldset>
          ))}
        </div>
      </section>

      <section aria-labelledby="proj-heading">
        <div className="flex items-center justify-between">
          <h2 id="proj-heading" className="text-lg font-semibold">
            Projects
          </h2>
          <button type="button" className="btn-ghost" onClick={() => setProjects([...projects, { ...blankProj }])}>
            Add project
          </button>
        </div>
        {projects.length === 0 && <p className="mt-2 text-sm text-muted">No projects found. School, capstone and personal projects are strong evidence of skills.</p>}
        <div className="mt-3 space-y-3">
          {projects.map((p, i) => (
            <fieldset key={i} className="panel space-y-3 p-4">
              <legend className="sr-only">Project {i + 1}</legend>
              <Text label="Project name" value={p.name} onChange={(v) => update(projects, setProjects, i, { name: v })} />
              <div>
                <label className="field-label" htmlFor={`pdesc-${i}`}>
                  Description
                </label>
                <textarea id={`pdesc-${i}`} className="field-input min-h-[4rem]" maxLength={3000} value={p.description ?? ""} onChange={(ev) => update(projects, setProjects, i, { description: ev.target.value })} />
              </div>
              <TagInput label="Skills used" values={p.skills} onChange={(v) => update(projects, setProjects, i, { skills: v })} />
              <button type="button" className="text-sm text-danger" onClick={() => setProjects(projects.filter((_, idx) => idx !== i))}>
                Remove this project
              </button>
            </fieldset>
          ))}
        </div>
      </section>

      <section className="max-w-xl">
        <TagInput label="Certifications and trainings" values={certifications} onChange={setCertifications} max={40} placeholder="e.g. Google Data Analytics Certificate" />
      </section>

      <div className="sticky bottom-0 -mx-4 flex items-center gap-4 border-t border-line bg-paper/95 px-4 py-4 backdrop-blur md:-mx-10 md:px-10">
        <button type="button" className="btn-primary" onClick={save} disabled={saving}>
          {saving ? "Saving…" : "Save corrections"}
        </button>
        <InlineStatus message={status.message} tone={status.tone} />
      </div>
    </div>
  );
}

function Text({ label, value, onChange }: { label: string; value: string | null; onChange: (v: string) => void }) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="field-label">
        {label}
      </label>
      <input id={id} className="field-input" value={value ?? ""} maxLength={200} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
