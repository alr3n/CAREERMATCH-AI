import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ResumeEditor } from "../features/ResumeEditor";
import { api } from "../services/api";
import { profile, resume } from "../test/fixtures";
import { ProfileEditor } from "./ProfileEditor";
import { ResumeUploader, validateResumeFile } from "./ResumeUploader";

describe("ResumeUploader", () => {
  it("validates type, emptiness and size before uploading", () => {
    expect(validateResumeFile(new File(["x"], "notes.txt"))).toMatch(/PDF or DOCX/);
    expect(validateResumeFile(new File([], "cv.pdf"))).toMatch(/empty/);
    const big = new File([new Uint8Array(5 * 1024 * 1024 + 1)], "cv.pdf");
    expect(validateResumeFile(big)).toMatch(/larger than 5 MB/);
    expect(validateResumeFile(new File(["%PDF-"], "cv.PDF"))).toBeNull();
  });

  it("uploads a valid file and reports server errors", async () => {
    const upload = vi.spyOn(api, "uploadResume").mockRejectedValueOnce(new Error("No readable text was found.")).mockResolvedValueOnce(resume);
    const onUploaded = vi.fn();
    render(<ResumeUploader onUploaded={onUploaded} />);
    const input = screen.getByLabelText("Resume file");
    await userEvent.upload(input, new File(["%PDF-1.7"], "scan.pdf", { type: "application/pdf" }));
    expect(await screen.findByText("No readable text was found.")).toBeInTheDocument();
    await userEvent.upload(input, new File(["%PDF-1.7"], "cv.pdf", { type: "application/pdf" }));
    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith(resume));
    expect(upload).toHaveBeenCalledTimes(2);
  });

  it("rejects unsupported files without calling the API", async () => {
    const upload = vi.spyOn(api, "uploadResume");
    render(<ResumeUploader onUploaded={() => {}} />);
    await userEvent.upload(screen.getByLabelText("Resume file"), new File(["hi"], "notes.txt"), { applyAccept: false });
    expect(await screen.findByText("Choose a PDF or DOCX file.")).toBeInTheDocument();
    expect(upload).not.toHaveBeenCalled();
  });
});

describe("ResumeEditor (profile correction)", () => {
  it("lets the user remove a wrongly extracted skill and add a missing one", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<ResumeEditor resume={resume} onSave={onSave} />);
    await userEvent.click(screen.getByRole("button", { name: "Remove Exel" }));
    await userEvent.type(screen.getByLabelText("Add a skill"), "Microsoft Excel{Enter}");
    await userEvent.click(screen.getByRole("button", { name: "Add education" }));
    await userEvent.type(screen.getByLabelText("School"), "Test University");
    await userEvent.click(screen.getByRole("button", { name: "Save corrections" }));
    await waitFor(() => expect(onSave).toHaveBeenCalled());
    const payload = onSave.mock.calls[0][0];
    expect(payload.skills).toEqual([{ skill: "Python" }, { skill: "Microsoft Excel" }]);
    expect(payload.education).toEqual([{ institution: "Test University", degree: null, field_of_study: null, start_date: null, end_date: null }]);
    expect(await screen.findByText(/corrections are saved/)).toBeInTheDocument();
  });

  it("requires project names", async () => {
    const onSave = vi.fn();
    render(<ResumeEditor resume={resume} onSave={onSave} />);
    await userEvent.click(screen.getByRole("button", { name: "Add project" }));
    await userEvent.click(screen.getByRole("button", { name: "Save corrections" }));
    expect(await screen.findByText(/Every project needs a name/)).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });
});

describe("ProfileEditor", () => {
  it("validates salary and sends optional fields as null", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<ProfileEditor profile={profile} onSave={onSave} />);
    await userEvent.type(screen.getByLabelText(/Minimum monthly salary/), "-5");
    await userEvent.click(screen.getByRole("button", { name: "Save preferences" }));
    expect(await screen.findByText(/Enter a positive amount/)).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();

    await userEvent.clear(screen.getByLabelText(/Minimum monthly salary/));
    await userEvent.selectOptions(screen.getByLabelText("Career stage"), "student");
    await userEvent.click(screen.getByLabelText("Remote"));
    await userEvent.click(screen.getByRole("button", { name: "Save preferences" }));
    await waitFor(() => expect(onSave).toHaveBeenCalled());
    expect(onSave.mock.calls[0][0]).toMatchObject({
      career_stage: "student",
      work_arrangements: ["remote"],
      min_salary: null,
      salary_currency: null,
      goal: null,
    });
    expect(await screen.findByText("Preferences saved.")).toBeInTheDocument();
  });
});
