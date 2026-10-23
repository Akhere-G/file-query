import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const deleteFile = vi.fn();
const viewFileContent = vi.fn();
const toastAdd = vi.fn();
const track = vi.fn();

vi.mock("../server-actions", () => ({
  deleteFile: (...args: unknown[]) => deleteFile(...args),
  viewFileContent: (...args: unknown[]) => viewFileContent(...args),
}));
vi.mock("@/components/ui/toast", () => ({ toast: { add: (...args: unknown[]) => toastAdd(...args) } }));
vi.mock("@/lib/analytics/client", () => ({ track: (...args: unknown[]) => track(...args) }));

import { ProjectFile } from "../types";
import FileCard from "./FileCard";

const file = (overrides: Partial<ProjectFile> = {}): ProjectFile => ({
  id: 5,
  name: "policy.md",
  mimeType: "text/markdown",
  size: 100,
  projectId: 1,
  status: "processed",
  error: null,
  ...overrides,
});

const ok = (data: unknown) => ({ success: true, data, status: 200 });
const failed = { success: false, data: null, message: "nope", details: null, status: 500 };

async function openMenu(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button"));
  return screen.findByRole("menu");
}

beforeEach(() => {
  deleteFile.mockReset();
  viewFileContent.mockReset();
  toastAdd.mockReset();
  track.mockReset();
});

describe("FileCard status", () => {
  it.each(["pending", "processing"])("shows a spinner while the file is %s", (status) => {
    const { container } = render(<FileCard file={file({ status })} />);

    expect(container.querySelector(".animate-spin")).not.toBeNull();
  });

  it("shows no spinner and no error once processed", () => {
    const { container } = render(<FileCard file={file()} />);

    expect(container.querySelector(".animate-spin")).toBeNull();
    expect(screen.queryByText(/problem with uploading/i)).toBeNull();
  });

  it("explains what to do when processing failed", () => {
    render(<FileCard file={file({ status: "error", error: "We couldn't read this file." })} />);

    expect(screen.getByText(/problem with uploading this file/i)).toBeInTheDocument();
    expect(screen.getByText("policy.md")).toBeInTheDocument();
  });
});

describe("FileCard actions", () => {
  it("opens a processed file in a new tab using the temporary link", async () => {
    const user = userEvent.setup();
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    viewFileContent.mockResolvedValue(ok({ file: file(), url: "https://s3.test/signed" }));
    render(<FileCard file={file()} />);

    await openMenu(user);
    await user.click(screen.getByRole("menuitem", { name: "View" }));

    await waitFor(() =>
      expect(open).toHaveBeenCalledWith("https://s3.test/signed", "_blank", "noopener,noreferrer"),
    );
    expect(viewFileContent).toHaveBeenCalledWith(5);
  });

  it("tells the user when a file cannot be opened", async () => {
    const user = userEvent.setup();
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    viewFileContent.mockResolvedValue(failed);
    render(<FileCard file={file()} />);

    await openMenu(user);
    await user.click(screen.getByRole("menuitem", { name: "View" }));

    await waitFor(() =>
      expect(toastAdd).toHaveBeenCalledWith({ title: "Could not view file", type: "error" }),
    );
    expect(open).not.toHaveBeenCalled();
  });

  it.each([
    ["error", "error", /problem with uploading/i],
    ["pending", "info", /still being uploading/i],
  ])("does not try to open a file in the %s state", async (status, type, title) => {
    const user = userEvent.setup();
    render(<FileCard file={file({ status })} />);

    await openMenu(user);
    await user.click(screen.getByRole("menuitem", { name: "View" }));

    expect(viewFileContent).not.toHaveBeenCalled();
    expect(toastAdd).toHaveBeenCalledWith({ title: expect.stringMatching(title), type });
  });

  it("asks for confirmation before deleting, then deletes and notifies the parent", async () => {
    const user = userEvent.setup();
    const onDeleted = vi.fn();
    deleteFile.mockResolvedValue(ok(5));
    render(<FileCard file={file()} onDeleted={onDeleted} />);

    await openMenu(user);
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("Do you want to delete this file?");
    expect(deleteFile).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(onDeleted).toHaveBeenCalledTimes(1));
    expect(deleteFile).toHaveBeenCalledWith(5);
    expect(toastAdd).toHaveBeenCalledWith({ title: "Deleted file" });
  });

  it("cancelling the dialog deletes nothing", async () => {
    const user = userEvent.setup();
    render(<FileCard file={file()} onDeleted={vi.fn()} />);

    await openMenu(user);
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    await user.click(await screen.findByRole("button", { name: "Cancel" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(deleteFile).not.toHaveBeenCalled();
  });

  it("keeps the dialog open and reports a failed delete", async () => {
    const user = userEvent.setup();
    const onDeleted = vi.fn();
    deleteFile.mockResolvedValue(failed);
    render(<FileCard file={file()} onDeleted={onDeleted} />);

    await openMenu(user);
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    await user.click(await screen.findByRole("button", { name: "Delete" }));

    await waitFor(() =>
      expect(toastAdd).toHaveBeenCalledWith({ title: "Could not delete file", type: "error" }),
    );
    expect(onDeleted).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("will not delete a file that is still uploading", async () => {
    const user = userEvent.setup();
    render(<FileCard file={file({ status: "pending" })} />);

    await openMenu(user);
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    await user.click(await screen.findByRole("button", { name: "Delete" }));

    expect(deleteFile).not.toHaveBeenCalled();
    expect(toastAdd).toHaveBeenCalledWith({
      title: expect.stringMatching(/still being uploading/i),
      type: "info",
    });
  });

  it("offers only 'View' in the read-only demo", async () => {
    const user = userEvent.setup();
    render(<FileCard file={file()} isDemo />);

    await openMenu(user);

    expect(screen.getByRole("menuitem", { name: "View" })).toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: "Delete" })).toBeNull();
  });
});
