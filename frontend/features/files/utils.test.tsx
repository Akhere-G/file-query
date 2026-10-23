import { describe, expect, it } from "vitest";

import { getSizeStr } from "./utils";

describe("getSizeStr", () => {
  it.each([
    [0, "0 B"],
    [1023, "1023 B"],
    [1024, "1.00 KB"],
    [1536, "1.50 KB"],
    [1024 * 1024 - 1, "1024.00 KB"],
    [1024 * 1024, "1.00 MB"],
    [50 * 1024 * 1024, "50.00 MB"],
    [1024 * 1024 * 1024, "Too Large"],
  ])("formats %d bytes as %s", (bytes, expected) => {
    expect(getSizeStr(bytes)).toBe(expected);
  });
});
