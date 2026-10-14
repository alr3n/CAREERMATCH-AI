const PROVIDER_NAME: Record<string, string> = { greenhouse: "Greenhouse", lever: "Lever", demo: "Demo" };

export function SourceBadge({ provider, sourceName, isDemo }: { provider: string; sourceName: string; isDemo: boolean }) {
  if (isDemo) {
    return (
      <span
        className="inline-flex items-center rounded border border-dashed border-ink/50 px-2 py-0.5 text-xs font-semibold text-ink"
        title="Fictional listing used to demonstrate the app. Not a real vacancy."
      >
        Demo data, not a real job
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded border border-line bg-paper px-2 py-0.5 text-xs text-muted" title={`Retrieved from ${PROVIDER_NAME[provider] ?? provider}`}>
      Via {PROVIDER_NAME[provider] ?? provider}: {sourceName}
    </span>
  );
}
