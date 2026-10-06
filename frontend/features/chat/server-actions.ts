"use server";

import { attachToken, getApiBaseUrl } from "@/lib/api";
import { parseResponse } from "@/lib/apiUtils";
import { revalidatePath } from "next/cache";
import { Message } from "./types";
import { PaginatedMessages } from "./types";

export async function sendMessage(projectId: number, content: string) {
  const baseUrl = await getApiBaseUrl();

  const response = await fetch(
    `${baseUrl}/api/projects/${projectId}/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: await attachToken(),
      },
      body: JSON.stringify({ content }),
    },
  );

  const aiResponseMessage = parseResponse<Message>(response);
  revalidatePath("/dashboard");
  return aiResponseMessage;
}

export async function getMessages(
  projectId: number,
  nextCursor: number | null,
  limit: number = 30,
) {
  const baseUrl = await getApiBaseUrl();
  const params = new URLSearchParams({
    limit: String(limit),
  });
  if (nextCursor) {
    params.set("before_id", String(nextCursor));
  }
  const token = await attachToken();
  const response = await fetch(
    `${baseUrl}/api/projects/${projectId}/messages?${params.toString()}`,
    {
      headers: {
        Authorization: token,
      },
    },
  );
  const data = await parseResponse<PaginatedMessages>(response);
  return data;
}
