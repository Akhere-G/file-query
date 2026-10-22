// Keep in sync with MAX_FILE_SIZE and MAX_FILES_PER_REQUEST in backend/src/settings.py.
export const MAX_FILE_SIZE_MB = 50;
export const MAX_FILES_PER_UPLOAD = 10;

// Browsers report inconsistent MIME types (.md is often empty, .csv can be
// application/vnd.ms-excel), so the type is derived from the file extension.
// Keep in sync with accepted_mime_types in backend/src/features/files/file_schema.py.
export const EXTENSION_MIME_TYPES: Record<string, string> = {
  ".pdf": "application/pdf",
  ".doc": "application/msword",
  ".docx":
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".txt": "text/plain",
  ".md": "text/markdown",
  ".markdown": "text/markdown",
  ".csv": "text/csv",
};

export function mimeTypeFor(fileName: string): string | null {
  const dot = fileName.lastIndexOf(".");
  if (dot === -1) return null;
  return EXTENSION_MIME_TYPES[fileName.slice(dot).toLowerCase()] ?? null;
}
