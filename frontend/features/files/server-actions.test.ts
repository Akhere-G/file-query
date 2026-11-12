import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchMock = vi.fn();
const revalidatePath = vi.fn();

vi.mock("@/lib/api", () => ({
  getApiBaseUrl: async () => "http://api.test",
  attachToken: async () => "Bearer tok",
  getClientHeaders: async () => ({}),
}));
vi.mock("next/cache", () => ({ revalidatePath: (...args: unknown[]) => revalidatePath(...args) }));

import { confirmUploads, deleteFile, getFiles, uploadFiles, viewFileContent } from "./server-actions";

const ok = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

beforeEach(() => {
  fetchMock.mockReset();
  revalidatePath.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

describe("getFiles", () => {
  it("requests the project's files with the user's token", async () => {
    fetchMock.mockResolvedValue(ok([{ id: 1, status: "processed" }]));

    const result = await getFiles(12);

    expect(fetchMock).toHaveBeenCalledWith("http://api.test/api/projects/12/files", {
      headers: { "Content-Type": "application/json", Authorization: "Bearer tok" },
    });
    expect(result).toMatchObject({ success: true, data: [{ id: 1, status: "processed" }] });
  });

  it("returns API errors instead of throwing", async () => {
    fetchMock.mockResolvedValue(ok({ detail: "The item you were looking for was not found" }, 404));

    expect(await getFiles(99)).toMatchObject({ success: false, status: 404 });
  });
});

describe("uploadFiles", () => {
  const file = (name: string, type: string, content = "hello") => new File([content], name, { type });

  it("describes each file for the backend, preferring the extension over the browser's MIME type", async () => {
    fetchMock.mockResolvedValue(ok({ files: [], projectId: 5 }));

    await uploadFiles([file("notes.md", ""), file("data.csv", "application/vnd.ms-excel", "a,b")]);

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("http://api.test/api/files");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual([
      { name: "notes.md", size: 5, mimeType: "text/markdown" },
      { name: "data.csv", size: 3, mimeType: "text/csv" },
    ]);
  });

  it("falls back to the browser's MIME type for unknown extensions", async () => {
    fetchMock.mockResolvedValue(ok({ files: [], projectId: 5 }));

    await uploadFiles([file("photo.png", "image/png")]);

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)[0].mimeType).toBe("image/png");
  });

  it("adds the project to the URL only when uploading into an existing project", async () => {
    fetchMock.mockResolvedValue(ok({ files: [], projectId: 5 }));

    await uploadFiles([file("a.txt", "text/plain")], 5);
    await uploadFiles([file("a.txt", "text/plain")]);

    expect(String(fetchMock.mock.calls[0][0])).toBe("http://api.test/api/files?project_id=5");
    expect(String(fetchMock.mock.calls[1][0])).toBe("http://api.test/api/files");
  });

  it("refreshes the dashboard and surfaces validation errors per field", async () => {
    fetchMock.mockResolvedValue(
      ok({ detail: [{ type: "x", loc: ["body", 0, "size"], msg: "Files cannot be empty" }] }, 422),
    );

    const result = await uploadFiles([file("a.txt", "text/plain", "")]);

    expect(revalidatePath).toHaveBeenCalledWith("/dashboard");
    expect(result).toMatchObject({ success: false, details: { "0.size": ["Files cannot be empty"] } });
  });
});

describe("confirmUploads", () => {
  it("sends the per-file results and refreshes the dashboard", async () => {
    fetchMock.mockResolvedValue(ok([]));

    await confirmUploads([{ id: 1 }, { id: 2, error: "Could not upload" }]);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://api.test/api/files/confirm");
    expect(JSON.parse(init.body)).toEqual([{ id: 1 }, { id: 2, error: "Could not upload" }]);
    expect(revalidatePath).toHaveBeenCalledWith("/dashboard");
  });
});

describe("viewFileContent and deleteFile", () => {
  it("fetches a temporary link for a file", async () => {
    fetchMock.mockResolvedValue(ok({ file: { id: 3 }, url: "https://s3.test/x" }));

    const result = await viewFileContent(3);

    expect(fetchMock.mock.calls[0][0]).toBe("http://api.test/api/files/3");
    expect(result).toMatchObject({ success: true, data: { url: "https://s3.test/x" } });
  });

  it("deletes with DELETE and refreshes the dashboard", async () => {
    fetchMock.mockResolvedValue(ok(3));

    await deleteFile(3);

    expect(fetchMock.mock.calls[0][1].method).toBe("DELETE");
    expect(revalidatePath).toHaveBeenCalledWith("/dashboard");
  });
});
