import { FileText, Image as ImageIcon, File as FileIcon } from "lucide-react";

export function getSizeStr(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  } else if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(2)} KB`;
  } else if (size < 1024 * 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  }

  return "Too Large";
}

export const getFileIcon = (file: File) => {
  if (file.type.startsWith("image/")) {
    return <ImageIcon className="size-5" />;
  }

  if (file.type === "application/pdf") {
    return <FileText className="size-5" />;
  }

  return <FileIcon className="size-5" />;
};
