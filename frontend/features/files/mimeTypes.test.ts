import { describe, expect, it } from "vitest";

import { mimeTypeFor } from "./mimeTypes";

describe("mimeTypeFor", () => {
  it.each([
    ["report.pdf", "application/pdf"],
    ["old.doc", "application/msword"],
    ["new.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    ["notes.txt", "text/plain"],
    ["readme.md", "text/markdown"],
    ["readme.markdown", "text/markdown"],
    ["data.csv", "text/csv"],
  ])("maps %s to %s", (name, mime) => {
    expect(mimeTypeFor(name)).toBe(mime);
  });

  it("ignores case and uses only the last extension", () => {
    expect(mimeTypeFor("REPORT.PDF")).toBe("application/pdf");
    expect(mimeTypeFor("archive.tar.csv")).toBe("text/csv");
    expect(mimeTypeFor("invoice.pdf.exe")).toBeNull();
  });

  it.each(["noextension", "image.png", "script.js", "trailingdot.", ""])(
    "returns null for %j",
    (name) => {
      expect(mimeTypeFor(name)).toBeNull();
    },
  );
});
