"use server";
import { attachToken, getApiBaseUrl } from "@/lib/api";
import { parseResponse } from "@/lib/apiUtils";
import { Project } from "./types";

export async function getProjects() {
  const baseUrl = await getApiBaseUrl();

  const res = await fetch(`${baseUrl}/api/projects`, {
    headers: {
      "Content-Type": "application/json",
      Authorization: await attachToken(),
    },
  });

  const data = parseResponse<Project[]>(res);
  return data;
}

export async function getProject(projectId: number) {
  const baseUrl = await getApiBaseUrl();

  const res = await fetch(`${baseUrl}/api/projects/${projectId}`, {
    headers: {
      "Content-Type": "application/json",
      Authorization: await attachToken(),
    },
  });

  const data = parseResponse<Project>(res);
  return data;
}

export async function renameProject(projectId: number, name: string) {
  const baseUrl = await getApiBaseUrl();

  const res = await fetch(`${baseUrl}/api/projects/${projectId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: await attachToken(),
    },
    body: JSON.stringify({ name }),
  });

  return parseResponse<Project>(res);
}

export async function deleteProject(projectId: number) {
  const baseUrl = await getApiBaseUrl();

  const res = await fetch(`${baseUrl}/api/projects/${projectId}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      Authorization: await attachToken(),
    },
  });

  return parseResponse<{ id: number }>(res);
}
