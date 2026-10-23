import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchMock = vi.fn();
const clientHeaders = vi.fn();

vi.mock("@/lib/api", () => ({
  getApiBaseUrl: async () => "http://api.test",
  attachToken: async () => "Bearer tok",
  getClientHeaders: () => clientHeaders(),
}));
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

import { getMessages, sendMessage } from "./server-actions";

const ok = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

beforeEach(() => {
  fetchMock.mockReset();
  clientHeaders.mockReset().mockResolvedValue({});
  vi.stubGlobal("fetch", fetchMock);
});

describe("sendMessage", () => {
  it("posts the question and returns the answer with its citations", async () => {
    const answer = {
      id: 2,
      content: "Thirty days.",
      owner: "assistant",
      citations: [{ id: 9, fileId: 1, fileName: "policy.md", title: null, content: "..." }],
    };
    fetchMock.mockResolvedValue(ok(answer));

    const result = await sendMessage(4, "How long do refunds take?");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://api.test/api/projects/4/messages");
    expect(init.method).toBe("POST");
    expect(init.headers.Authorization).toBe("Bearer tok");
    expect(JSON.parse(init.body)).toEqual({ content: "How long do refunds take?" });
    expect(result).toEqual({ success: true, data: answer, status: 200 });
  });

  it("forwards the visitor's IP so rate limits apply per person", async () => {
    clientHeaders.mockResolvedValue({ "X-Client-IP": "203.0.113.7", "X-Internal-Secret": "s" });
    fetchMock.mockResolvedValue(ok({}));

    await sendMessage(4, "hi");

    expect(fetchMock.mock.calls[0][1].headers).toMatchObject({ "X-Client-IP": "203.0.113.7" });
  });

  it.each([
    [429, "Free accounts can only send 40 per month."],
    [404, "The item you were looking for was not found"],
  ])("returns the API's %d message so it can be shown to the user", async (status, detail) => {
    fetchMock.mockResolvedValue(ok({ detail }, status));

    expect(await sendMessage(4, "hi")).toMatchObject({ success: false, message: detail, status });
  });
});

describe("getMessages", () => {
  it("asks for the newest page when there is no cursor", async () => {
    fetchMock.mockResolvedValue(ok({ messages: [], hasMore: false, nextCursor: null }));

    await getMessages(4, null, 20);

    expect(fetchMock.mock.calls[0][0]).toBe("http://api.test/api/projects/4/messages?limit=20");
  });

  it("pages backwards using before_id", async () => {
    fetchMock.mockResolvedValue(ok({ messages: [], hasMore: false, nextCursor: null }));

    await getMessages(4, 77);

    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://api.test/api/projects/4/messages?limit=30&before_id=77",
    );
  });
});
