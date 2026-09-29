export interface Project {
  id: number;
  name: string;
  userId: number;
}

export interface Chat {
  id: number;
  content: string;
  role: string;
}

export interface File {
  id: number;
  name: string;
  url: string;
  thumbnail: string;
}

export interface UploadFileResponse {
  files: {
    id: number;
    key: string;
    url: string;
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
  mime_type: string;
  size: number;
  error?: string | null;
  project_id: number;
  storage_key: string;
  status: string;
}
