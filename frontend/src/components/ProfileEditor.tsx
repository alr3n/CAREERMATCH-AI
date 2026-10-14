import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import type { Profile, ProfileUpdate } from "../types/api";
import { CheckboxGroup } from "./CheckboxGroup";
import { InlineStatus } from "./States";
import { TagInput } from "./TagInput";

const schema = z.object({
  career_stage: z.enum(["", "student", "fresh_graduate", "entry_level", "experienced", "career_transition"]),
  goal: z.enum(["", "internship", "entry_level", "experienced", "career_transition"]),
  preferred_titles: z.array(z.string().max(120)).max(20),
  preferred_industries: z.array(z.string().max(120)).max(20),
  preferred_locations: z.array(z.string().max(120)).max(20),
  work_arrangements: z.array(z.enum(["remote", "hybrid", "onsite"])),
  employment_types: z.array(z.enum(["full_time", "part_time", "contract", "internship", "temporary"])),
  min_salary: z
    .string()
    .refine((v) => v === "" || (/^\d+(\.\d{1,2})?$/.test(v) && Number(v) >= 0), "Enter a positive amount, or leave it empty"),
  salary_currency: z.enum(["PHP", "USD"]),
  skills_to_develop: z.array(z.string().max(120)).max(20),
});

type FormValues = z.infer<typeof schema>;

export const CATEGORY_OPTIONS = [
  "Data & Analytics",
  "Software Engineering",
  "Design",
  "IT & Infrastructure",
  "Product & Project Management",
  "Marketing & Content",
  "Sales & Business Development",
  "Customer Support",
  "Finance & Accounting",
  "Human Resources",
  "Operations & Administration",
];
const LOCATION_SUGGESTIONS = ["Metro Manila", "Makati", "Taguig", "Quezon City", "Pasig", "Cebu City", "Davao City", "Iloilo City", "Baguio"];

export function profileToForm(p: Profile): FormValues {
  return {
    career_stage: p.career_stage ?? "",
    goal: p.goal ?? "",
    preferred_titles: p.preferred_titles,
    preferred_industries: p.preferred_industries,
    preferred_locations: p.preferred_locations,
    work_arrangements: p.work_arrangements,
    employment_types: p.employment_types,
    min_salary: p.min_salary ? String(Number(p.min_salary)) : "",
    salary_currency: (p.salary_currency as "PHP" | "USD") ?? "PHP",
    skills_to_develop: p.skills_to_develop,
  };
}

interface Props {
  profile: Profile;
  suggestions?: { titles?: string[]; locations?: string[]; skills?: string[] };
  onSave: (update: ProfileUpdate) => Promise<void>;
  submitLabel?: string;
}

export function ProfileEditor({ profile, suggestions, onSave, submitLabel = "Save preferences" }: Props) {
  const [status, setStatus] = useState<{ message: string | null; tone: "info" | "success" | "error" }>({ message: null, tone: "info" });
  const {
    control,
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
    reset,
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: profileToForm(profile) });

  // Pick up changes made elsewhere (e.g. "Use these as my preferences") unless the user is editing.
  useEffect(() => {
    if (!isDirty) reset(profileToForm(profile));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile.updated_at]);

  async function submit(values: FormValues) {
    setStatus({ message: null, tone: "info" });
    const salary = values.min_salary === "" ? null : Number(values.min_salary);
    const update: ProfileUpdate = {
      ...values,
      career_stage: values.career_stage || null,
      goal: values.goal || null,
      min_salary: salary,
      salary_currency: salary === null ? null : values.salary_currency,
      onboarding_completed: true,
    };
    try {
      await onSave(update);
      reset(values);
      setStatus({ message: "Preferences saved.", tone: "success" });
    } catch (e) {
      setStatus({ message: e instanceof Error ? e.message : "Saving failed.", tone: "error" });
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-8" noValidate>
      <section className="grid gap-5 md:grid-cols-2">
        <div>
          <label htmlFor="career_stage" className="field-label">
            Career stage
          </label>
          <select id="career_stage" className="field-input" {...register("career_stage")}>
            <option value="">Prefer not to say</option>
            <option value="student">Student</option>
            <option value="fresh_graduate">Fresh graduate</option>
            <option value="entry_level">Entry-level professional</option>
            <option value="experienced">Experienced professional</option>
            <option value="career_transition">Changing careers</option>
          </select>
        </div>
        <div>
          <label htmlFor="goal" className="field-label">
            What are you looking for?
          </label>
          <select id="goal" className="field-input" {...register("goal")}>
            <option value="">Not sure yet</option>
            <option value="internship">An internship</option>
            <option value="entry_level">An entry-level job</option>
            <option value="experienced">An experienced role</option>
            <option value="career_transition">A role in a new field</option>
          </select>
        </div>
      </section>

      <Controller
        control={control}
        name="preferred_titles"
        render={({ field }) => (
          <TagInput label="Job titles you're interested in" values={field.value} onChange={field.onChange} placeholder="e.g. Data Analyst" suggestions={suggestions?.titles} />
        )}
      />
      <Controller
        control={control}
        name="preferred_industries"
        render={({ field }) => (
          <TagInput label="Job categories or industries" values={field.value} onChange={field.onChange} placeholder="e.g. Data & Analytics" suggestions={CATEGORY_OPTIONS} />
        )}
      />
      <Controller
        control={control}
        name="work_arrangements"
        render={({ field }) => (
          <CheckboxGroup
            legend="Work arrangement"
            hint="Leave empty if any arrangement is fine."
            options={[
              { value: "remote", label: "Remote" },
              { value: "hybrid", label: "Hybrid" },
              { value: "onsite", label: "On-site" },
            ]}
            values={field.value}
            onChange={field.onChange}
          />
        )}
      />
      <Controller
        control={control}
        name="employment_types"
        render={({ field }) => (
          <CheckboxGroup
            legend="Employment type"
            options={[
              { value: "internship", label: "Internship" },
              { value: "full_time", label: "Full-time" },
              { value: "part_time", label: "Part-time" },
              { value: "contract", label: "Contract" },
              { value: "temporary", label: "Temporary" },
            ]}
            values={field.value}
            onChange={field.onChange}
          />
        )}
      />
      <Controller
        control={control}
        name="preferred_locations"
        render={({ field }) => (
          <TagInput
            label="Preferred locations in the Philippines"
            hint="Optional. Remote roles always count as a location match."
            values={field.value}
            onChange={field.onChange}
            placeholder="e.g. Cebu City"
            suggestions={[...(suggestions?.locations ?? []), ...LOCATION_SUGGESTIONS]}
          />
        )}
      />
      <section className="grid gap-5 md:grid-cols-[1fr_8rem]">
        <div>
          <label htmlFor="min_salary" className="field-label">
            Minimum monthly salary (optional)
          </label>
          <input id="min_salary" inputMode="decimal" className="field-input num" placeholder="Leave empty to skip" {...register("min_salary")} aria-invalid={Boolean(errors.min_salary)} aria-describedby="salary-help" />
          <p id="salary-help" className="mt-1 text-sm text-muted">
            {errors.min_salary?.message ?? "Only compared with listings that publish a salary in the same currency."}
          </p>
        </div>
        <div>
          <label htmlFor="salary_currency" className="field-label">
            Currency
          </label>
          <select id="salary_currency" className="field-input" {...register("salary_currency")}>
            <option value="PHP">PHP</option>
            <option value="USD">USD</option>
          </select>
        </div>
      </section>
      <Controller
        control={control}
        name="skills_to_develop"
        render={({ field }) => (
          <TagInput label="Skills you want to develop" values={field.value} onChange={field.onChange} placeholder="e.g. Power BI" suggestions={suggestions?.skills} />
        )}
      />
      <div className="flex items-center gap-4">
        <button type="submit" className="btn-primary" disabled={isSubmitting || (!isDirty && profile.onboarding_completed)}>
          {isSubmitting ? "Saving…" : submitLabel}
        </button>
        <InlineStatus message={status.message} tone={status.tone} />
      </div>
    </form>
  );
}
