type Variant = "matched" | "missing" | "related" | "neutral" | "user";

const STYLES: Record<Variant, string> = {
  matched: "bg-teal-tint text-teal-dark border-transparent",
  missing: "bg-amber-tint text-amber border-transparent",
  related: "bg-surface text-teal-dark border-teal-soft",
  neutral: "bg-paper text-ink border-line",
  user: "bg-surface text-ink border-ink/30",
};

const SR: Record<Variant, string> = {
  matched: "found in your resume",
  missing: "not found in your resume",
  related: "related skill found",
  neutral: "",
  user: "added by you",
};

interface Props {
  skill: string;
  variant?: Variant;
  title?: string;
  onRemove?: () => void;
}

export function SkillChip({ skill, variant = "neutral", title, onRemove }: Props) {
  return (
    <span
      className={`inline-flex max-w-full items-center gap-1 rounded border px-2 py-0.5 text-sm ${STYLES[variant]}`}
      title={title}
    >
      {variant === "missing" && <span aria-hidden="true">○</span>}
      {variant === "matched" && <span aria-hidden="true">●</span>}
      <span className="truncate">{skill}</span>
      {SR[variant] && <span className="sr-only">({SR[variant]})</span>}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="-my-1 -mr-1 ml-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded text-muted hover:bg-danger-tint hover:text-danger max-md:h-10 max-md:w-10 pointer-coarse:h-10 pointer-coarse:w-10"
          aria-label={`Remove ${skill}`}
        >
          ×
        </button>
      )}
    </span>
  );
}
