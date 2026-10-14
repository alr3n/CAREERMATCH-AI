import type { ComponentKey, Components, Weights } from "../types/api";
import { COMPONENT_COLOR, COMPONENT_ORDER, COMPONENT_SHORT, pct } from "../utils/format";

interface Props {
  score: number;
  components: Components;
  weights: Weights;
  evidenceCoverage: number;
  variant?: "compact" | "full";
  labels?: Partial<Record<ComponentKey, string>>;
}

/**
 * The score ledger: each segment's width is that component's share of the
 * final score (weight × value, renormalised over evaluated components).
 * Hatched space at the end is weight that could not be evaluated.
 */
export function MatchScore({ score, components, weights, evidenceCoverage, variant = "compact", labels }: Props) {
  const evaluated = COMPONENT_ORDER.filter((k) => components[k] !== null && components[k] !== undefined);
  const weightSum = evaluated.reduce((acc, k) => acc + (weights[k] ?? 0), 0) || 1;
  const segments = evaluated.map((k) => ({
    key: k,
    // contribution in score points (0..100)
    points: (100 * (weights[k] ?? 0) * (components[k] as number)) / weightSum,
  }));
  const rounded = Math.round(score);
  const description = `Compatibility score ${rounded} out of 100, based on ${pct(evidenceCoverage)} of the scoring weight.`;

  return (
    <div className={variant === "full" ? "space-y-4" : "space-y-1.5"}>
      <div className="flex items-baseline gap-2">
        <span className={`num font-bold leading-none ${variant === "full" ? "text-4xl" : "text-2xl"}`} aria-hidden="true">
          {rounded}
        </span>
        <span className="text-sm text-muted" aria-hidden="true">
          / 100 compatibility
        </span>
        <span className="sr-only">{description}</span>
      </div>
      <div className="relative h-2.5 w-full overflow-hidden rounded-sm bg-paper" aria-hidden="true">
        <div className="flex h-full">
          {segments.map((s) => (
            <div key={s.key} className={`${COMPONENT_COLOR[s.key]} h-full border-r border-surface last:border-r-0`} style={{ width: `${s.points}%` }} />
          ))}
        </div>
      </div>
      {evidenceCoverage < 0.999 && (
        <div className="flex items-center gap-2 text-xs text-muted">
          <span className="ledger-gap inline-block h-2.5 w-6 rounded-sm" aria-hidden="true" />
          Based on {pct(evidenceCoverage)} of the scoring weight
        </div>
      )}
      {variant === "full" && (
        <table className="w-full text-sm">
          <caption className="sr-only">Score components</caption>
          <thead>
            <tr className="border-b border-line text-left text-muted">
              <th className="py-1.5 font-normal">Component</th>
              <th className="py-1.5 text-right font-normal">Value</th>
              <th className="py-1.5 text-right font-normal">Weight</th>
              <th className="py-1.5 text-right font-normal">Points</th>
            </tr>
          </thead>
          <tbody>
            {COMPONENT_ORDER.map((k) => {
              const seg = segments.find((s) => s.key === k);
              return (
                <tr key={k} className="border-b border-line/60">
                  <td className="py-1.5">
                    <span className={`mr-2 inline-block h-2.5 w-2.5 rounded-sm align-middle ${components[k] === null ? "ledger-gap" : COMPONENT_COLOR[k]}`} aria-hidden="true" />
                    {labels?.[k] ?? COMPONENT_SHORT[k]}
                  </td>
                  <td className="num py-1.5 text-right">{components[k] === null ? <span className="text-muted">not enough info</span> : pct(components[k])}</td>
                  <td className="num py-1.5 text-right text-muted">{pct(weights[k])}</td>
                  <td className="num py-1.5 text-right">{seg ? seg.points.toFixed(1) : "–"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
