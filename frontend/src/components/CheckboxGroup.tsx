interface Option<T extends string> {
  value: T;
  label: string;
}

interface Props<T extends string> {
  legend: string;
  options: Option<T>[];
  values: T[];
  onChange: (values: T[]) => void;
  hint?: string;
}

export function CheckboxGroup<T extends string>({ legend, options, values, onChange, hint }: Props<T>) {
  return (
    <fieldset>
      <legend className="field-label">{legend}</legend>
      {hint && <p className="mb-2 text-sm text-muted">{hint}</p>}
      <div className="flex flex-wrap gap-2">
        {options.map((o) => {
          const checked = values.includes(o.value);
          return (
            <label
              key={o.value}
              className={`flex min-h-9 cursor-pointer items-center gap-2 rounded border px-3 py-1.5 text-sm max-md:min-h-11 pointer-coarse:min-h-11 ${
                checked ? "border-teal bg-teal-tint text-teal-dark" : "border-line bg-surface"
              }`}
            >
              <input
                type="checkbox"
                className="h-4 w-4 accent-teal"
                checked={checked}
                onChange={() => onChange(checked ? values.filter((v) => v !== o.value) : [...values, o.value])}
              />
              {o.label}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
