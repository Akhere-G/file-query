const EXTENSION_MIME_TYPES: Record<string, string> = {
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
