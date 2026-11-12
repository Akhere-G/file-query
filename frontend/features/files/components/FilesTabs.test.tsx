import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
let search = "";
const uploadFiles = vi.fn();
const confirmUploads = vi.fn();
const sendFilesToS3 = vi.fn();
const toastAdd = vi.fn();
const track = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/dashboard",
  useSearchParams: () => new URLSearchParams(search),
}));
vi.mock("../server-actions", () => ({
  uploadFiles: (...args: unknown[]) => uploadFiles(...args),
  confirmUploads: (...args: unknown[]) => confirmUploads(...args),
  deleteFile: vi.fn(),
  viewFileContent: vi.fn(),
}));
vi.mock("../actions", () => ({ sendFilesToS3: (...args: unknown[]) => sendFilesToS3(...args) }));
vi.mock("@/components/ui/toast", () => ({ toast: { add: (...args: unknown[]) => toastAdd(...args) } }));
vi.mock("@/lib/analytics/client", () => ({ track: (...args: unknown[]) => track(...args) }));

import { ProjectFile } from "../types";
import FilesTabs from "./FilesTabs";

const ok = (data: unknown) => ({ success: true, data, status: 200 });
const presigned = (ids: number[], projectId = 9) =>
  ok({
    files: ids.map((id) => ({ id, key: `k${id}`, url: `https://s3.test/${id}`, fields: {} })),
    projectId,
  });

const existing = (id: number, status: string): ProjectFile => ({
  id,
  name: `existing-${id}.txt`,
  mimeType: "text/plain",
  size: 10,
  projectId: 9,
  status,
});

function setup(props: Partial<React.ComponentProps<typeof FilesTabs>> = {}) {
  const onFilesChanged = vi.fn();
  const view = render(
    <FilesTabs files={[]} isLoading={false} error="" onFilesChanged={onFilesChanged} {...props} />,
  );
  const input = view.container.querySelector<HTMLInputElement>("input[type=file]")!;
  return { ...view, input, onFilesChanged, user: userEvent.setup() };
}

const txt = (name: string, content = "hello") => new File([content], name, { type: "text/plain" });
const uploadButton = (count = 1) =>
  screen.getByRole("button", { name: new RegExp(`Upload ${count} files?`) });

beforeEach(() => {
  search = "";
  [push, uploadFiles, confirmUploads, sendFilesToS3, toastAdd, track].forEach((m) => m.mockReset());
});

describe("choosing files", () => {
  it("offers an upload area and no upload button until a file is chosen", () => {
    setup();

    expect(screen.getByText("Upload your files")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Choose files" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Upload \d/ })).toBeNull();
  });

  it("lists chosen files with their type and size, and lets one be removed", async () => {
    const { user, input } = setup();

    await user.upload(input, [txt("a.txt", "x".repeat(2048)), txt("b.txt")]);

    expect(screen.getByText("Files to upload")).toBeInTheDocument();
    expect(screen.getByText("2 files")).toBeInTheDocument();
    expect(screen.getByText("TXT · 2.00 KB")).toBeInTheDocument();
    expect(screen.getByText("TXT · 5 B")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Remove a.txt" }));

    expect(screen.queryByText("a.txt")).toBeNull();
    expect(screen.getByText("1 file")).toBeInTheDocument();
  });

  it("accepts dropped files", () => {
    const { container } = setup();
    const dropZone = container.firstElementChild!;

    const dropEvent = new Event("drop", { bubbles: true, cancelable: true });
    Object.assign(dropEvent, { dataTransfer: { files: [txt("dropped.txt")] } });
    dropZone.dispatchEvent(dropEvent);

    return waitFor(() => expect(screen.getByText("dropped.txt")).toBeInTheDocument());
  });

  it("shows the project's existing files", () => {
    setup({ files: [existing(1, "processed"), existing(2, "processing")] });

    expect(screen.getByText("Your files")).toBeInTheDocument();
    expect(screen.getByText("existing-1.txt")).toBeInTheDocument();
    expect(screen.getByText("existing-2.txt")).toBeInTheDocument();
  });

  it("warns when the file list could not be loaded", () => {
    setup({ error: "Sorry, could not get files..." });

    expect(screen.getByText("Sorry, something went wrong...")).toBeInTheDocument();
  });
});

describe("uploading", () => {
  it("presigns, sends to S3 then confirms, in that order, using the chosen files", async () => {
    const calls: string[] = [];
    uploadFiles.mockImplementation(async () => (calls.push("presign"), presigned([1])));
    sendFilesToS3.mockImplementation(async () => (calls.push("s3"), [{ id: 1 }]));
    confirmUploads.mockImplementation(async () => (calls.push("confirm"), ok([])));
    search = "projectId=9";
    const { user, input, onFilesChanged } = setup();
    const file = txt("a.txt");

    await user.upload(input, file);
    await user.click(uploadButton());

    await waitFor(() => expect(onFilesChanged).toHaveBeenCalledTimes(1));
    expect(calls).toEqual(["presign", "s3", "confirm"]);
    expect(uploadFiles).toHaveBeenCalledWith([file], 9);
    expect(sendFilesToS3).toHaveBeenCalledWith(expect.any(Array), [file]);
    expect(confirmUploads).toHaveBeenCalledWith([{ id: 1 }]);
    expect(screen.queryByText("Files to upload")).toBeNull();
    expect(track).toHaveBeenCalledWith("file_upload_completed", expect.any(Object));
  });

  it("disables the upload button while the upload is in progress", async () => {
    let finish!: (value: unknown) => void;
    uploadFiles.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    const { user, input } = setup();

    await user.upload(input, txt("a.txt"));
    await user.click(uploadButton());

    expect(uploadButton()).toBeDisabled();

    sendFilesToS3.mockResolvedValue([{ id: 1 }]);
    confirmUploads.mockResolvedValue(ok([]));
    finish(presigned([1]));
    await waitFor(() => expect(screen.queryByText("Files to upload")).toBeNull());
  });

  it("opens the new project after the first upload", async () => {
    uploadFiles.mockResolvedValue(presigned([1], 42));
    sendFilesToS3.mockResolvedValue([{ id: 1 }]);
    confirmUploads.mockResolvedValue(ok([]));
    const { user, input } = setup();

    await user.upload(input, txt("a.txt"));
    await user.click(uploadButton());

    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard?projectId=42"));
    expect(uploadFiles).toHaveBeenCalledWith(expect.any(Array), undefined);
  });

  it("stays on the current project when uploading into an existing one", async () => {
    uploadFiles.mockResolvedValue(presigned([1]));
    sendFilesToS3.mockResolvedValue([{ id: 1 }]);
    confirmUploads.mockResolvedValue(ok([]));
    search = "projectId=9";
    const { user, input, onFilesChanged } = setup();

    await user.upload(input, txt("a.txt"));
    await user.click(uploadButton());

    await waitFor(() => expect(onFilesChanged).toHaveBeenCalled());
    expect(push).not.toHaveBeenCalled();
  });
});

describe("upload failures", () => {
  it("shows the server's validation errors and keeps the files so they can be fixed", async () => {
    uploadFiles.mockResolvedValue({
      success: false,
      data: null,
      message: null,
      details: { "0.name": ["notes.exe is not a valid .txt file name"] },
      status: 422,
    });
    const { user, input } = setup();

    await user.upload(input, txt("notes.txt"));
    await user.click(uploadButton());

    expect(await screen.findByText(/File 1: notes.exe is not a valid/)).toBeInTheDocument();
    expect(screen.getByText("notes.txt")).toBeInTheDocument();
    expect(sendFilesToS3).not.toHaveBeenCalled();
    expect(track).toHaveBeenCalledWith(
      "file_upload_failed",
      expect.objectContaining({ stage: "presign", reason: "validation" }),
    );
    expect(uploadButton()).not.toBeDisabled();
  });

  it("shows the API message in a toast when the request is rejected", async () => {
    uploadFiles.mockResolvedValue({
      success: false,
      data: null,
      message: "Free accounts can only have up to 3 projects",
      details: null,
      status: 429,
    });
    const { user, input } = setup();

    await user.upload(input, txt("a.txt"));
    await user.click(uploadButton());

    await waitFor(() =>
      expect(toastAdd).toHaveBeenCalledWith({
        title: "Free accounts can only have up to 3 projects",
        type: "error",
      }),
    );
    expect(screen.getByText("File 1: Something went wrong...")).toBeInTheDocument();
  });

  it("keeps only the files that failed to reach storage so they can be retried", async () => {
    uploadFiles.mockResolvedValue(presigned([1, 2]));
    sendFilesToS3.mockResolvedValue([{ id: 1 }, { id: 2, error: "Could not upload" }]);
    confirmUploads.mockResolvedValue(ok([]));
    search = "projectId=9";
    const { user, input, onFilesChanged } = setup();

    await user.upload(input, [txt("good.txt"), txt("bad.txt")]);
    await user.click(uploadButton(2));

    await waitFor(() =>
      expect(toastAdd).toHaveBeenCalledWith({
        title: "Some files could not be uploaded. Try them again.",
        type: "error",
      }),
    );
    expect(screen.queryByText("good.txt")).toBeNull();
    expect(screen.getByText("bad.txt")).toBeInTheDocument();
    expect(onFilesChanged).toHaveBeenCalled();
  });

  it("reports a confirmation failure and keeps the files", async () => {
    uploadFiles.mockResolvedValue(presigned([1]));
    sendFilesToS3.mockResolvedValue([{ id: 1 }]);
    confirmUploads.mockResolvedValue({
      success: false,
      data: null,
      message: "Storage limit reached",
      details: null,
      status: 400,
    });
    search = "projectId=9";
    const { user, input } = setup();

    await user.upload(input, txt("a.txt"));
    await user.click(uploadButton());

    await waitFor(() =>
      expect(toastAdd).toHaveBeenCalledWith({ title: "Storage limit reached", type: "error" }),
    );
    expect(screen.getByText("a.txt")).toBeInTheDocument();
  });

  it("recovers from an unexpected error and lets the user try again", async () => {
    uploadFiles.mockRejectedValue(new Error("fetch failed"));
    const { user, input } = setup();

    await user.upload(input, txt("a.txt"));
    await user.click(uploadButton());

    await waitFor(() =>
      expect(toastAdd).toHaveBeenCalledWith({ title: "fetch failed", type: "error" }),
    );
    expect(uploadButton()).not.toBeDisabled();
    expect(track).toHaveBeenCalledWith(
      "file_upload_failed",
      expect.objectContaining({ reason: "exception" }),
    );
  });
});

describe("demo mode", () => {
  it("is read-only: shows files but no way to upload", () => {
    setup({ isDemo: true, files: [existing(1, "processed")] });

    expect(screen.getByText("The demo is read-only")).toBeInTheDocument();
    expect(screen.getByText("existing-1.txt")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Choose files" })).toBeNull();
  });
});
