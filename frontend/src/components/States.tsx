import type { ReactNode } from "react";
import { ApiError } from "../services/api";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-3 py-10 text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-teal-soft border-t-teal" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ error, onRetry, title = "Something went wrong" }: { error: unknown; onRetry?: () => void; title?: string }) {
  const message = error instanceof ApiError || error instanceof Error ? error.message : "An unexpected error occurred.";
  return (
    <div role="alert" className="rounded-lg border border-danger/30 bg-danger-tint px-4 py-3 text-sm">
      <p className="font-semibold text-danger">{title}</p>
      <p className="mt-1 text-ink">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn-secondary mt-3">
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-surface px-6 py-10">
      <h3 className="text-lg font-semibold">{title}</h3>
      {children && <div className="mt-2 max-w-prose text-muted">{children}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function InlineStatus({ message, tone = "info" }: { message: string | null; tone?: "info" | "success" | "error" }) {
  const color = tone === "error" ? "text-danger" : tone === "success" ? "text-teal" : "text-muted";
  return (
    <p role="status" aria-live="polite" className={`min-h-[1.35rem] text-sm ${color}`}>
      {message}
    </p>
  );
}
