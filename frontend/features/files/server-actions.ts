"use server";

import { attachToken, getApiBaseUrl } from "@/lib/api";
import { FileUploadStatus, ProjectFile, UploadFileResponse } from "./types";
import { parseResponse } from "@/lib/apiUtils";
import { revalidatePath } from "next/cache";

export async function getFiles(projectId: number) {
  const url = getApiBaseUrl();

  const response = await fetch(`${url}/api/projects/${projectId}/files`, {
    headers: {
      "Content-Type": "application:json",
      Authorization: await attachToken(),
    },
  });

  return (await response.json()) as ProjectFile[];
}
export async function uploadFiles(files: File[], projectId?: number) {
  const fileData = files.map((file) => ({
    size: file.size,
    name: file.name,
    mimeType: file.type,
  }));

  const baseUrl = await getApiBaseUrl();
  const url = new URL(`${baseUrl}/api/files`);

  if (projectId !== undefined) {
    url.searchParams.set("project_id", projectId.toString());
  }
  const response = await fetch(url, {
    method: "POST",
    body: JSON.stringify(fileData),
    headers: {
      "Content-Type": "application/json",
      Authorization: await attachToken(),
    },
  });

  const data = await parseResponse<UploadFileResponse>(response);
  revalidatePath("/dashboard");
  return data;
}

export async function confirmUploads(results: FileUploadStatus[]) {
  const baseUrl = await getApiBaseUrl();

  const response = await fetch(`${baseUrl}/api/files/confirm`, {
    method: "POST",
    body: JSON.stringify(results),
    headers: {
      "Content-Type": "application/json",
      Authorization: await attachToken(),
    },
  });
  revalidatePath("/dashboard");
  const data = await parseResponse<ProjectFile[]>(response);
  return data;
}

export async function viewFileContent(fileId: number) {
  const baseUrl = await getApiBaseUrl();

  const response = await fetch(`${baseUrl}/api/files/${fileId}`, {
    headers: {
      "Content-Type": "application/json",
      Authorization: await attachToken(),
    },
  });

  const data = await parseResponse<{ file: ProjectFile; url: string }>(
    response,
  );
  return data;
}

export async function deleteFile(fileId: number) {
  const baseUrl = await getApiBaseUrl();

  const response = await fetch(`${baseUrl}/api/files/${fileId}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      Authorization: await attachToken(),
    },
  });
  revalidatePath("/dashboard");
  const data = await parseResponse<number>(response);
  return data;
}
