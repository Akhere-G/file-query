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
  title: string;
  content: string;
  fileId: number;
  fileName: string;
}
