import { attachToken, getApiBaseUrl } from "@/lib/api";
import { parseResponse } from "@/lib/apiUtils";
import { PaginatedMessages } from "./types";

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
