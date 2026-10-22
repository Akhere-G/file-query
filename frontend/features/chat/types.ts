export interface Message {
  id: number;
  content: string;
  owner: "user" | "assistant";
  createdAt: string;
  citations: Citation[];
}

export interface PaginatedMessages {
  messages: Message[];
  hasMore: boolean;
  nextCursor: number | null;
}

export interface Citation {
  id: number;
  title: string | null;
  content: string;
  fileId: number;
  fileName: string;
}
