import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getFiles = vi.fn();

vi.mock("../server-actions", () => ({
  getFiles: (...args: unknown[]) => getFiles(...args),
  uploadFiles: vi.fn(),
  confirmUploads: vi.fn(),
  deleteFile: vi.fn(),
  viewFileContent: vi.fn(),
}));
vi.mock("@/features/chat/server-actions", () => ({
  getMessages: vi.fn().mockResolvedValue({
    success: true,
    data: { messages: [], hasMore: false, nextCursor: null },
    status: 200,
  }),
  sendMessage: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/dashboard",
  useSearchParams: () => new URLSearchParams("projectId=3"),
}));
vi.mock("@/lib/analytics/client", () => ({ track: vi.fn() }));

import { Tabs } from "@/components/ui/tabs";
import ProjectTabs from "./ProjectTabs";

const file = (id: number, status: string) => ({
  id,
  name: `f${id}.txt`,
  mimeType: "text/plain",
  size: 1,
  projectId: 3,
  status,
});

async function renderTabs(files: ReturnType<typeof file>[], tab: "chat" | "files" = "chat") {
  getFiles.mockResolvedValue({ success: true, data: files, status: 200 });
  render(
    <Tabs defaultValue={tab}>
      <ProjectTabs projectId={3} />
    </Tabs>,
  );
  await act(async () => {});
}

beforeEach(() => getFiles.mockReset());

describe("ProjectTabs processing status", () => {
  it("warns that unfinished files cannot be searched yet", async () => {
    await renderTabs([file(1, "processed"), file(2, "processing")]);

    expect(screen.getByText("Some files are still processing.")).toBeInTheDocument();
    expect(screen.getByText("The AI cannot search through files being processed.")).toBeInTheDocument();
  });

  it("treats pending uploads as unfinished too", async () => {
    await renderTabs([file(1, "pending")]);

    expect(screen.getByText("Some files are still processing.")).toBeInTheDocument();
  });

  it("shows no warning once everything is processed", async () => {
    await renderTabs([file(1, "processed"), file(2, "processed")]);

    expect(screen.queryByText("Some files are still processing.")).toBeNull();
    expect(screen.getByPlaceholderText("Ask a question...")).toBeEnabled();
  });

  it("does not block on files that failed", async () => {
    await renderTabs([file(1, "processed"), file(2, "error")]);

    expect(screen.queryByText("Some files are still processing.")).toBeNull();
    expect(screen.getByPlaceholderText("Ask a question...")).toBeEnabled();
  });

  it("lets questions through while only some files are processing", async () => {
    await renderTabs([file(1, "processed"), file(2, "processing")]);

    expect(screen.getByPlaceholderText("Ask a question...")).toBeEnabled();
    expect(screen.queryByText("All files are still processing")).toBeNull();
  });

  it("blocks questions while every file is still processing", async () => {
    await renderTabs([file(1, "processing"), file(2, "pending")]);

    expect(screen.getByText("All files are still processing")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Ask a question...")).toBeDisabled();
  });

  it("shows the project's files on the files tab", async () => {
    await renderTabs([file(1, "processed")], "files");

    expect(screen.getByText("f1.txt")).toBeInTheDocument();
  });
});
