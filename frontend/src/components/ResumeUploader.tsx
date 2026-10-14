import { useRef, useState, type DragEvent } from "react";
import { api } from "../services/api";
import type { Resume } from "../types/api";

const MAX_MB = 5;
const ACCEPT = [".pdf", ".docx"];

export function validateResumeFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPT.some((ext) => name.endsWith(ext))) return "Choose a PDF or DOCX file.";
  if (file.size === 0) return "The file is empty.";
  if (file.size > MAX_MB * 1024 * 1024) return `The file is larger than ${MAX_MB} MB.`;
  return null;
}

type Status = { kind: "idle" } | { kind: "uploading"; name: string } | { kind: "error"; message: string };

export function ResumeUploader({ onUploaded }: { onUploaded: (resume: Resume) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [dragging, setDragging] = useState(false);

  async function handle(file: File | undefined) {
    if (!file) return;
    const problem = validateResumeFile(file);
    if (problem) {
      setStatus({ kind: "error", message: problem });
      return;
    }
    setStatus({ kind: "uploading", name: file.name });
    try {
      const resume = await api.uploadResume(file);
      setStatus({ kind: "idle" });
      onUploaded(resume);
    } catch (e) {
      setStatus({ kind: "error", message: e instanceof Error ? e.message : "Upload failed." });
    } finally {
      if (input.current) input.current.value = "";
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    void handle(e.dataTransfer.files[0]);
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`rounded-lg border-2 border-dashed px-6 py-10 text-center ${dragging ? "border-teal bg-teal-tint" : "border-line bg-surface"}`}
      >
        <p className="text-lg font-semibold">Upload your resume</p>
        <p className="mt-1 text-sm text-muted">PDF or DOCX, up to {MAX_MB} MB. Text-based files work best; scanned images can't be read.</p>
        <button type="button" className="btn-primary mt-4" onClick={() => input.current?.click()} disabled={status.kind === "uploading"}>
          {status.kind === "uploading" ? "Reading your resume…" : "Choose a file"}
        </button>
        <label htmlFor="resume-file" className="sr-only">
          Resume file
        </label>
        <input
          id="resume-file"
          ref={input}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="sr-only"
          onChange={(e) => void handle(e.target.files?.[0])}
        />
      </div>
      <div role="status" aria-live="polite" className="mt-2 min-h-[1.35rem] text-sm">
        {status.kind === "uploading" && <span className="text-muted">Extracting skills, education and experience from {status.name}…</span>}
        {status.kind === "error" && <span className="text-danger">{status.message}</span>}
      </div>
    </div>
  );
}
