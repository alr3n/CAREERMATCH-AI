import { useState } from "react";
import { api } from "../services/api";
import type { JobSummary } from "../types/api";

/** Save/unsave a job and report the new state through `onChange`. */
export function useSaveToggle(onChange: (jobId: string, saved: boolean) => void) {
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function toggle(job: Pick<JobSummary, "id" | "is_saved">) {
    setPending(job.id);
    setError(null);
    try {
      if (job.is_saved) await api.unsaveJob(job.id);
      else await api.saveJob(job.id);
      onChange(job.id, !job.is_saved);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update saved jobs.");
    } finally {
      setPending(null);
    }
  }

  return { toggle, pending, error };
}
