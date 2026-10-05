export interface UploadFileResponse {
  files: {
    id: number;
    key: string;
    url: string;
    fields: Record<string, string>;
  }[];
  projectId: number;
}

export interface FileUploadStatus {
  id: number;
  error?: string;
}

export interface ProjectFile {
  id: number;
  name: string;
  mimeType: string;
  size: number;
  error?: string | null;
  projectId: number;
  storageKey: string;
  status: string;
}
