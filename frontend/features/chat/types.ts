export interface Message {
  id: number;
  content: string;
  owner: "user" | "assistant";
}
