export type FastApiValidationError = {
  type: string;
  loc: Array<string | number>;
  msg: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
};

export type FieldErrors = Record<string, string[]>;

export type ApiResponse<T> =
  | { success: true; data: T; status: number }
  | {
      success: false;
      data: null;
      message: string | null;
      details: FieldErrors | null;
      status: number;
    };

export type ActionResult =
  | { success: true }
  | { success: false; message: string | null; details: FieldErrors | null };

const FALLBACK_ERROR_MESSAGE = "Something went wrong. Please try again.";

function isFastApiValidationError(
  value: unknown,
): value is FastApiValidationError {
  return (
    typeof value === "object" &&
    value !== null &&
    "loc" in value &&
    Array.isArray(value.loc) &&
    "msg" in value &&
    typeof value.msg === "string"
  );
}

function getFieldName(location: Array<string | number>): string {
  const [source, ...path] = location;
  const fieldPath = ["body", "query", "path"].includes(String(source))
    ? path
    : location;

  return fieldPath.map(String).join(".") || "form";
}

function getFieldErrors(detail: unknown): FieldErrors | null {
  if (!Array.isArray(detail)) return null;

  const details: FieldErrors = {};
  for (const error of detail) {
    if (!isFastApiValidationError(error)) continue;

    const field = getFieldName(error.loc);
    details[field] ??= [];
    details[field].push(error.msg);
  }

  return Object.keys(details).length > 0 ? details : null;
}

export function getErrorMessage(detail: unknown): string {
  return typeof detail === "string" && detail.trim()
    ? detail
    : FALLBACK_ERROR_MESSAGE;
}

export async function parseResponse<T>(
  response: Response,
): Promise<ApiResponse<T>> {
  let body: unknown;

  try {
    body = await response.json();
  } catch {
    return {
      success: false,
      message: FALLBACK_ERROR_MESSAGE,
      details: null,
      data: null,
      status: response.status,
    };
  }

  if (response.ok) {
    return {
      success: true,
      data: body as T,

      status: response.status,
    };
  }

  const detail =
    typeof body === "object" && body !== null && "detail" in body
      ? body.detail
      : null;
  const details = getFieldErrors(detail);

  return {
    success: false,
    message: details ? null : getErrorMessage(detail),
    details,
    data: null,
    status: response.status,
  };
}
