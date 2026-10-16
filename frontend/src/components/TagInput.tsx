import { useId, useState, type KeyboardEvent } from "react";
import { SkillChip } from "./SkillChip";

interface Props {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  suggestions?: string[];
  hint?: string;
  max?: number;
}

/** Free-text list input: type and press Enter (or comma) to add. */
export function TagInput({ label, values, onChange, placeholder, suggestions = [], hint, max = 20 }: Props) {
  const id = useId();
  const [draft, setDraft] = useState("");

  function add(raw: string) {
    const value = raw.trim().replace(/\s+/g, " ");
    if (!value || values.length >= max) return;
    if (values.some((v) => v.toLowerCase() === value.toLowerCase())) return;
    onChange([...values, value]);
    setDraft("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add(draft);
    } else if (e.key === "Backspace" && !draft && values.length) {
      onChange(values.slice(0, -1));
    }
  }

  const unused = suggestions.filter((s) => !values.some((v) => v.toLowerCase() === s.toLowerCase())).slice(0, 8);
  return (
    <div>
      <label htmlFor={id} className="field-label">
        {label}
      </label>
      {hint && <p className="mb-2 text-sm text-muted">{hint}</p>}
      {values.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {values.map((v) => (
            <SkillChip key={v} skill={v} onRemove={() => onChange(values.filter((x) => x !== v))} />
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <input
          id={id}
          className="field-input"
          value={draft}
          placeholder={placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          maxLength={120}
        />
        <button type="button" className="btn-secondary" onClick={() => add(draft)} disabled={!draft.trim()}>
          Add
        </button>
      </div>
      {unused.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-sm">
          <span className="text-muted">Suggestions:</span>
          {unused.map((s) => (
            <button key={s} type="button" className="min-h-8 rounded border border-line px-2 py-0.5 text-sm hover:border-teal hover:text-teal max-md:min-h-11 max-md:px-3 pointer-coarse:min-h-11 pointer-coarse:px-3" onClick={() => add(s)}>
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
