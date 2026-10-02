export interface Message {
  id: number;
  content: string;
  owner: "user" | "assistant";
  createdAt: string;
}

export interface PaginatedMessages {
  messages: Message[];
  hasMore: boolean;
  nextCursor: number | null;
}
