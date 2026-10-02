"use server";

import { attachToken, getApiBaseUrl } from "@/lib/api";
import { parseResponse } from "@/lib/apiUtils";
import { revalidatePath } from "next/cache";
import { Message } from "./types";

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
