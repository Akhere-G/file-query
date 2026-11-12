import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const track = vi.fn();
vi.mock("@/lib/analytics/client", () => ({ track: (...args: unknown[]) => track(...args) }));

import { Message } from "@/features/chat/types";
import MessageCard from "./MessageCard";

const message = (overrides: Partial<Message> = {}): Message => ({
  id: 1,
  content: "Refunds are accepted within thirty days.",
  owner: "assistant",
  createdAt: "2026-01-01T00:00:00Z",
  citations: [],
  ...overrides,
});

beforeEach(() => track.mockReset());

describe("MessageCard", () => {
  it("renders the message text as markdown", () => {
    render(<MessageCard message={message({ content: "**Thirty** days\n\n- one\n- two" })} />);

    expect(screen.getByText("Thirty").tagName).toBe("STRONG");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("never renders images from model output", () => {
    const { container } = render(
      <MessageCard message={message({ content: "![tracking](https://evil.test/p.png) hello" })} />,
    );

    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText(/hello/)).toBeInTheDocument();
  });

  it("does not turn raw HTML into elements", () => {
    const { container } = render(
      <MessageCard message={message({ content: "<script>alert(1)</script><b>bold</b>" })} />,
    );

    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
  });

  it("shows no citations section when the answer has none", () => {
    render(<MessageCard message={message()} />);

    expect(screen.queryByRole("button")).toBeNull();
  });

  it("shows one citation button per source, labelled by title or file name", () => {
    render(
      <MessageCard
        message={message({
          citations: [
            { id: 1, fileId: 1, fileName: "policy.md", title: "Refund window", content: "a" },
            { id: 2, fileId: 2, fileName: "faq.md", title: null, content: "b" },
          ],
        })}
      />,
    );

    expect(screen.getByRole("button", { name: "Refund window" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "faq.md" })).toBeInTheDocument();
  });

  it("opens the cited passage and its source file when a citation is clicked", async () => {
    const user = userEvent.setup();
    render(
      <MessageCard
        message={message({
          citations: [
            {
              id: 1,
              fileId: 1,
              fileName: "policy.md",
              title: "Refund window",
              content: "Refunds are accepted within thirty days of purchase.",
            },
          ],
        })}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Refund window" }));

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("Source citation");
    expect(dialog).toHaveTextContent("Source file");
    expect(dialog).toHaveTextContent("policy.md");
    expect(dialog).toHaveTextContent("Cited text");
    expect(dialog).toHaveTextContent("Refunds are accepted within thirty days of purchase.");
    expect(track).toHaveBeenCalledWith("citation_opened");
  });

  it("keeps line breaks of the cited text", async () => {
    const user = userEvent.setup();
    render(
      <MessageCard
        message={message({
          citations: [
            { id: 1, fileId: 1, fileName: "a.md", title: null, content: "line one\nline two" },
          ],
        })}
      />,
    );

    await user.click(screen.getByRole("button", { name: "a.md" }));

    expect((await screen.findByText(/line one/)).className).toContain("whitespace-pre-wrap");
  });
});
