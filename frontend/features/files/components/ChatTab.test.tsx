import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getMessages = vi.fn();
const sendMessage = vi.fn();
const toastAdd = vi.fn();
const track = vi.fn();

vi.mock("@/features/chat/server-actions", () => ({
  getMessages: (...args: unknown[]) => getMessages(...args),
  sendMessage: (...args: unknown[]) => sendMessage(...args),
}));
vi.mock("@/components/ui/toast", () => ({ toast: { add: (...args: unknown[]) => toastAdd(...args) } }));
vi.mock("@/lib/analytics/client", () => ({ track: (...args: unknown[]) => track(...args) }));

import { Message } from "@/features/chat/types";
import ChatTab from "./ChatTab";

const ok = (data: unknown) => ({ success: true, data, status: 200 });
const page = (messages: Message[] = [], hasMore = false) =>
  ok({ messages, hasMore, nextCursor: hasMore ? 1 : null });

const answer: Message = {
  id: 20,
  owner: "assistant",
  content: "Refunds are accepted within thirty days.",
  createdAt: "2026-01-01T00:00:00Z",
  citations: [
    {
      id: 7,
      fileId: 1,
      fileName: "policy.md",
      title: "Refund window",
      content: "Refunds are accepted within thirty days of purchase.",
    },
  ],
};

function setup(props: Partial<React.ComponentProps<typeof ChatTab>> = {}) {
  render(
    <ChatTab
      projectId={4}
      files={[]}
      isLoading={false}
      error=""
      allFilesProcessing={false}
      {...props}
    />,
  );
  return { user: userEvent.setup(), box: screen.getByPlaceholderText("Ask a question...") };
}

beforeEach(() => {
  [getMessages, sendMessage, toastAdd, track].forEach((m) => m.mockReset());
  getMessages.mockResolvedValue(page());
});

describe("history", () => {
  it("loads and shows the earlier conversation with its citations", async () => {
    getMessages.mockResolvedValue(
      page([{ ...answer, id: 1, owner: "user", content: "How long do refunds take?", citations: [] }, answer]),
    );

    setup();

    expect(await screen.findByText("How long do refunds take?")).toBeInTheDocument();
    expect(screen.getByText(/accepted within thirty days\.$/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refund window" })).toBeInTheDocument();
    expect(getMessages).toHaveBeenCalledWith(4, null, 20);
  });

  it("reports a history that could not be loaded", async () => {
    getMessages.mockResolvedValue({ success: false, data: null, message: "Boom", details: null, status: 500 });

    setup();

    await waitFor(() => expect(toastAdd).toHaveBeenCalledWith({ title: "Boom", type: "error" }));
  });

  it("prompts to upload when there is no project yet", () => {
    setup({ projectId: null });

    expect(screen.getByText("Upload files to start chatting")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Ask a question...")).toBeDisabled();
    expect(getMessages).not.toHaveBeenCalled();
  });
});

describe("asking a question", () => {
  it("shows the question straight away, then the answer with its source", async () => {
    let reply!: (value: unknown) => void;
    sendMessage.mockReturnValue(new Promise((resolve) => (reply = resolve)));
    const { user, box } = setup();
    await waitFor(() => expect(getMessages).toHaveBeenCalled());

    await user.type(box, "How long do refunds take?{Enter}");

    expect(screen.getByText("How long do refunds take?")).toBeInTheDocument();
    expect(box).toHaveValue("");
    expect(box).toBeDisabled(); // no second question while waiting
    expect(sendMessage).toHaveBeenCalledWith(4, "How long do refunds take?");

    reply(ok(answer));

    expect(await screen.findByText(/accepted within thirty days\.$/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refund window" })).toBeInTheDocument();
    await waitFor(() => expect(box).toBeEnabled());
    expect(screen.getAllByText("How long do refunds take?")).toHaveLength(1);
  });

  it("sends with the button as well as the Enter key", async () => {
    sendMessage.mockResolvedValue(ok(answer));
    const { user, box } = setup();

    await user.type(box, "hello");
    await user.click(screen.getAllByRole("button").at(-1)!);

    expect(sendMessage).toHaveBeenCalledWith(4, "hello");
  });

  it("trims the question and does not send blank ones", async () => {
    sendMessage.mockResolvedValue(ok(answer));
    const { user, box } = setup();

    await user.type(box, "   {Enter}");
    expect(sendMessage).not.toHaveBeenCalled();

    await user.type(box, "  padded question  {Enter}");
    expect(sendMessage).toHaveBeenCalledWith(4, "padded question");
  });

  it("uses Shift+Enter for a new line instead of sending", async () => {
    const { user, box } = setup();

    await user.type(box, "line one{Shift>}{Enter}{/Shift}line two");

    expect(sendMessage).not.toHaveBeenCalled();
    expect(box).toHaveValue("line one\nline two");
  });

  it("limits questions to 2000 characters", () => {
    const { box } = setup();

    expect(box).toHaveAttribute("maxlength", "2000");
  });

  it("takes the question back and explains the problem when the answer fails", async () => {
    sendMessage.mockResolvedValue({
      success: false,
      data: null,
      message: "Free accounts can only send 40 per month.",
      details: null,
      status: 429,
    });
    const { user, box } = setup();

    await user.type(box, "How long do refunds take?{Enter}");

    await waitFor(() =>
      expect(toastAdd).toHaveBeenCalledWith({
        title: "Free accounts can only send 40 per month.",
        type: "error",
      }),
    );
    expect(box).toHaveValue("How long do refunds take?");
    expect(screen.queryByText("How long do refunds take?", { selector: "p" })).toBeNull();
    expect(box).toBeEnabled();
  });

  it("copes with the request itself blowing up", async () => {
    sendMessage.mockRejectedValue(new Error("network"));
    const { user, box } = setup();

    await user.type(box, "question{Enter}");

    await waitFor(() =>
      expect(toastAdd).toHaveBeenCalledWith({ title: "Something went wrong", type: "error" }),
    );
    expect(box).toHaveValue("question");
  });

  it("records only the length bucket of the question, never its text", async () => {
    sendMessage.mockResolvedValue(ok(answer));
    const { user, box } = setup();

    await user.type(box, "secret question{Enter}");

    expect(track).toHaveBeenCalledWith("chat_message_sent", expect.objectContaining({ length_bucket: "short" }));
    expect(JSON.stringify(track.mock.calls)).not.toContain("secret");
  });
});

describe("when asking is not possible", () => {
  it("explains that files are still processing and blocks questions", () => {
    const { box } = setup({ allFilesProcessing: true });

    expect(screen.getByText("All files are still processing")).toBeInTheDocument();
    expect(box).toBeDisabled();
  });

  it("blocks questions while files are loading", () => {
    const { box } = setup({ isLoading: true });

    expect(box).toBeDisabled();
  });

  it("blocks questions and shows a warning when files could not be loaded", () => {
    const { box } = setup({ error: "Sorry, could not get files..." });

    expect(screen.getByText("Sorry, something went wrong...")).toBeInTheDocument();
    expect(box).toBeDisabled();
  });
});
