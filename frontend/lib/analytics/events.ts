export type AnalyticsEvent =
  | "view_page_home"
  | "view_page_login"
  | "view_page_register"
  | "view_page_dashboard"
  | "view_page_settings"
  | "view_page_privacy"
  | "view_page_terms"
  | "project_tab_viewed"
  | "login"
  | "login_failed"
  | "register"
  | "register_failed"
  | "demo_started"
  | "logout"
  | "project_renamed"
  | "project_deleted"
  | "file_upload_started"
  | "file_upload_completed"
  | "file_upload_failed"
  | "file_deleted"
  | "file_viewed"
  | "chat_message_sent"
  | "citation_opened";

export type AnalyticsValue = string | number | boolean | string[] | null;

export type AnalyticsProperties = Record<string, AnalyticsValue>;

const PAGE_EVENTS: Record<string, AnalyticsEvent> = {
  "/": "view_page_home",
  "/login": "view_page_login",
  "/register": "view_page_register",
  "/dashboard": "view_page_dashboard",
  "/settings": "view_page_settings",
  "/privacy": "view_page_privacy",
  "/terms": "view_page_terms",
};

export function pageEventFor(pathname: string): AnalyticsEvent | null {
  return PAGE_EVENTS[pathname] ?? null;
}

const FILE_TYPES: Record<string, string> = {
  "application/pdf": "pdf",
  "application/msword": "doc",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
    "docx",
  "text/plain": "txt",
  "text/markdown": "md",
  "text/csv": "csv",
};

export function fileTypeLabel(mimeType: string): string {
  return FILE_TYPES[mimeType] ?? "other";
}

export function lengthBucket(length: number): string {
  if (length <= 50) return "short";
  if (length <= 250) return "medium";
  return "long";
}

export function failureReason(message?: string, status?: number): string {
  if (status === 429) return "rate_limited";
  if (status === 409) return "conflict";
  if (status === 401 || status === 403) return "unauthorised";
  if (status === 400 || status === 422) return "validation";
  if (status && status >= 500) return "server_error";
  if (!message) return "unknown";
  return "other";
}
