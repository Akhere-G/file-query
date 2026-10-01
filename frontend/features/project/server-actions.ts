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
