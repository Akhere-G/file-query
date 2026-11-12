import { describe, expect, it } from "vitest";

import { failureReason, fileTypeLabel, lengthBucket, pageEventFor } from "./events";

describe("analytics helpers", () => {
  it("maps known paths to page events and ignores the rest", () => {
    expect(pageEventFor("/dashboard")).toBe("view_page_dashboard");
    expect(pageEventFor("/")).toBe("view_page_home");
    expect(pageEventFor("/unknown")).toBeNull();
  });

  it("labels file types without leaking file names", () => {
    expect(fileTypeLabel("application/pdf")).toBe("pdf");
    expect(fileTypeLabel("text/markdown")).toBe("md");
    expect(fileTypeLabel("image/png")).toBe("other");
  });

  it.each([
    [0, "short"],
    [50, "short"],
    [51, "medium"],
    [250, "medium"],
    [251, "long"],
  ])("buckets a message of %d characters as %s", (length, bucket) => {
    expect(lengthBucket(length)).toBe(bucket);
  });

  it.each([
    [undefined, 429, "rate_limited"],
    [undefined, 409, "conflict"],
    [undefined, 401, "unauthorised"],
    [undefined, 403, "unauthorised"],
    [undefined, 400, "validation"],
    [undefined, 422, "validation"],
    [undefined, 503, "server_error"],
    [undefined, undefined, "unknown"],
    ["Something", 418, "other"],
  ])("classifies (%s, %s) as %s", (message, status, reason) => {
    expect(failureReason(message, status)).toBe(reason);
  });
});
