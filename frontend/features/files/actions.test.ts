import { afterEach, describe, expect, it, vi } from "vitest";

import { sendFilesToS3 } from "./actions";

const presigned = (id: number) => ({
  id,
  key: `key-${id}`,
  url: `https://s3.test/bucket-${id}`,
  fields: { key: `key-${id}`, "Content-Type": "text/plain" },
});

const file = (name: string) => new File(["hello"], name, { type: "text/plain" });

afterEach(() => vi.unstubAllGlobals());

describe("sendFilesToS3", () => {
  it("posts each file to its own presigned URL with the signed fields before the file", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await sendFilesToS3([presigned(1), presigned(2)], [file("a.txt"), file("b.txt")]);

    expect(result).toEqual([
      { id: 1, error: undefined },
      { id: 2, error: undefined },
    ]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const [url, init] = fetchMock.mock.calls[1];
    expect(url).toBe("https://s3.test/bucket-2");
    expect(init.method).toBe("POST");
    const body = init.body as FormData;
    expect([...body.keys()]).toEqual(["key", "Content-Type", "file"]); // S3 needs the file last
    expect((body.get("file") as File).name).toBe("b.txt");
    expect(body.get("key")).toBe("key-2");
  });

  it("reports a rejected upload without failing the other files", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(new Response(null, { status: 403 }))
        .mockResolvedValueOnce(new Response(null, { status: 204 })),
    );

    const result = await sendFilesToS3([presigned(1), presigned(2)], [file("a.txt"), file("b.txt")]);

    expect(result).toEqual([
      { id: 1, error: "Could not upload" },
      { id: 2, error: undefined },
    ]);
  });

  it("reports network failures per file instead of throwing", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const result = await sendFilesToS3([presigned(1)], [file("a.txt")]);

    expect(result).toEqual([{ id: 1, error: "Failed to fetch" }]);
  });
});
