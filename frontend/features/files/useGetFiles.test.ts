import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getFiles = vi.fn();
vi.mock("./server-actions", () => ({ getFiles: (...args: unknown[]) => getFiles(...args) }));

import useGetFiles from "./useGetFiles";

const file = (id: number, status: string) => ({
  id,
  name: `f${id}.txt`,
  mimeType: "text/plain",
  size: 1,
  projectId: 1,
  status,
});
const respond = (...files: ReturnType<typeof file>[]) => ({ success: true, data: files });
const failure = { success: false, data: null, message: "nope", details: null, status: 500 };

/** Let the pending fetch resolve, then move the clock forward one poll interval. */
async function nextPoll() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(3000);
  });
}

beforeEach(() => {
  getFiles.mockReset();
  vi.useFakeTimers();
});

describe("useGetFiles", () => {
  it("loads the project's files once when everything is already finished", async () => {
    getFiles.mockResolvedValue(respond(file(1, "processed"), file(2, "error")));

    const { result } = renderHook(() => useGetFiles(1));
    await act(async () => {});

    expect(result.current.files.map((f) => f.id)).toEqual([1, 2]);
    expect(result.current.error).toBe("");
    await nextPoll();
    expect(getFiles).toHaveBeenCalledTimes(1);
  });

  it("keeps polling every 3 seconds while a file is pending or processing, then stops", async () => {
    getFiles
      .mockResolvedValueOnce(respond(file(1, "pending")))
      .mockResolvedValueOnce(respond(file(1, "processing")))
      .mockResolvedValue(respond(file(1, "processed")));

    const { result } = renderHook(() => useGetFiles(1));
    await act(async () => {});
    expect(result.current.files[0].status).toBe("pending");

    await nextPoll();
    expect(result.current.files[0].status).toBe("processing");
    await nextPoll();
    expect(result.current.files[0].status).toBe("processed");
    expect(getFiles).toHaveBeenCalledTimes(3);

    await nextPoll();
    await nextPoll();
    expect(getFiles).toHaveBeenCalledTimes(3);
  });

  it("does not poll again before the interval has passed", async () => {
    getFiles.mockResolvedValue(respond(file(1, "processing")));

    renderHook(() => useGetFiles(1));
    await act(async () => {});
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2900);
    });

    expect(getFiles).toHaveBeenCalledTimes(1);
  });

  it("tolerates two failed polls in a row and recovers", async () => {
    getFiles
      .mockResolvedValueOnce(respond(file(1, "processing")))
      .mockResolvedValueOnce(failure)
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValue(respond(file(1, "processed")));

    const { result } = renderHook(() => useGetFiles(1));
    await act(async () => {});
    await nextPoll();
    await nextPoll();
    expect(result.current.error).toBe("");
    await nextPoll();

    expect(result.current.error).toBe("");
    expect(result.current.files[0].status).toBe("processed");
  });

  it("gives up with an error after three consecutive failures", async () => {
    getFiles.mockResolvedValue(failure);

    const { result } = renderHook(() => useGetFiles(1));
    await act(async () => {});
    await nextPoll();
    await nextPoll();

    expect(result.current.error).toBe("Sorry, could not get files...");
    await nextPoll();
    expect(getFiles).toHaveBeenCalledTimes(3);
  });

  it("stops polling after 100 attempts even if a file never finishes", async () => {
    getFiles.mockResolvedValue(respond(file(1, "processing")));

    renderHook(() => useGetFiles(1));
    await act(async () => {});
    for (let i = 0; i < 110; i++) await nextPoll();

    expect(getFiles).toHaveBeenCalledTimes(100);
  });

  it("does not call the API for an invalid project id", async () => {
    const { result } = renderHook(() => useGetFiles(0));
    await act(async () => {});

    expect(getFiles).not.toHaveBeenCalled();
    expect(result.current.files).toEqual([]);
  });

  it("switches to the new project's files and clears the old ones", async () => {
    getFiles.mockImplementation(async (projectId: number) =>
      respond(file(projectId * 10, "processed")),
    );

    const { result, rerender } = renderHook(({ id }) => useGetFiles(id), {
      initialProps: { id: 1 },
    });
    await act(async () => {});
    expect(result.current.files[0].id).toBe(10);

    rerender({ id: 2 });
    await act(async () => {});

    expect(result.current.files.map((f) => f.id)).toEqual([20]);
    expect(getFiles).toHaveBeenLastCalledWith(2);
  });

  it("stops polling the old project when the project changes", async () => {
    getFiles.mockImplementation(async (projectId: number) =>
      respond(file(projectId, projectId === 1 ? "processing" : "processed")),
    );

    const { rerender } = renderHook(({ id }) => useGetFiles(id), { initialProps: { id: 1 } });
    await act(async () => {});
    rerender({ id: 2 });
    await act(async () => {});
    getFiles.mockClear();
    await nextPoll();
    await nextPoll();

    expect(getFiles).not.toHaveBeenCalled();
  });

  it("refetch reloads immediately and resumes polling for newly uploaded files", async () => {
    getFiles
      .mockResolvedValueOnce(respond(file(1, "processed")))
      .mockResolvedValueOnce(respond(file(1, "processed"), file(2, "pending")))
      .mockResolvedValue(respond(file(1, "processed"), file(2, "processed")));

    const { result } = renderHook(() => useGetFiles(1));
    await act(async () => {});

    await act(async () => result.current.refetch());
    expect(result.current.files).toHaveLength(2);
    expect(result.current.files[1].status).toBe("pending");

    await nextPoll();
    expect(result.current.files[1].status).toBe("processed");
  });

  it("does not update state after unmounting", async () => {
    getFiles.mockResolvedValue(respond(file(1, "processing")));

    const { unmount } = renderHook(() => useGetFiles(1));
    await act(async () => {});
    unmount();
    getFiles.mockClear();
    await nextPoll();

    expect(getFiles).not.toHaveBeenCalled();
  });
});
