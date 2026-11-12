// @vitest-environment node
import { describe, expect, it } from "vitest";

import { getErrorMessage, parseResponse } from "./apiUtils";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status });

const FALLBACK = "Something went wrong. Please try again.";

describe("parseResponse", () => {
  it("returns the parsed body on success", async () => {
    const result = await parseResponse<{ id: number }>(json({ id: 7 }, 201));

    expect(result).toEqual({ success: true, data: { id: 7 }, status: 201 });
  });

  it("uses a string detail as the message", async () => {
    const result = await parseResponse(json({ detail: "Invalid credentials." }, 401));

    expect(result).toEqual({
      success: false,
      data: null,
      message: "Invalid credentials.",
      details: null,
      status: 401,
    });
  });

  it("turns FastAPI validation errors into per-field messages", async () => {
    const result = await parseResponse(
      json(
        {
          detail: [
            { type: "value_error", loc: ["body", "password"], msg: "Must contain a digit." },
            { type: "value_error", loc: ["body", "password"], msg: "Must contain uppercase." },
            { type: "value_error", loc: ["body", "email"], msg: "Invalid email." },
          ],
        },
        422,
      ),
    );

    expect(result).toMatchObject({
      success: false,
      message: null,
      status: 422,
      details: {
        password: ["Must contain a digit.", "Must contain uppercase."],
        email: ["Invalid email."],
      },
    });
  });

  it("keeps nested field paths and groups errors with no field under 'form'", async () => {
    const result = await parseResponse(
      json(
        {
          detail: [
            { type: "x", loc: ["body", 0, "size"], msg: "Files cannot be empty" },
            { type: "x", loc: ["body"], msg: "Bad payload" },
          ],
        },
        422,
      ),
    );

    expect(result).toMatchObject({
      details: { "0.size": ["Files cannot be empty"], form: ["Bad payload"] },
    });
  });

  it("ignores malformed validation entries and falls back to a generic message", async () => {
    const result = await parseResponse(json({ detail: [{ nope: true }, "text"] }, 422));

    expect(result).toMatchObject({ success: false, details: null, message: FALLBACK });
  });

  it.each([
    ["no detail", {}],
    ["null detail", { detail: null }],
    ["blank detail", { detail: "   " }],
    ["object detail", { detail: { a: 1 } }],
  ])("falls back to a generic message for %s", async (_, body) => {
    const result = await parseResponse(json(body, 500));

    expect(result).toMatchObject({ success: false, message: FALLBACK, status: 500 });
  });

  it("copes with a non-JSON error body such as an HTML gateway page", async () => {
    const result = await parseResponse(new Response("<html>Bad gateway</html>", { status: 502 }));

    expect(result).toEqual({
      success: false,
      data: null,
      message: FALLBACK,
      details: null,
      status: 502,
    });
  });

  it("treats an unparsable success body as a failure rather than throwing", async () => {
    const result = await parseResponse(new Response("not json", { status: 200 }));

    expect(result.success).toBe(false);
  });
});

describe("getErrorMessage", () => {
  it("returns non-blank strings and falls back for everything else", () => {
    expect(getErrorMessage("Nope")).toBe("Nope");
    expect(getErrorMessage("  ")).toBe(FALLBACK);
    expect(getErrorMessage(undefined)).toBe(FALLBACK);
    expect(getErrorMessage(42)).toBe(FALLBACK);
  });
});
