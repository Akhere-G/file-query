"use client";

import { Input } from "@/components/ui/input";
import { Message } from "@/features/chat/types";
import MessageCard from "./MessageCard";
import { useEffect, useRef } from "react";

interface ChatTabProps {
  messages: Message[];
}

const ChatTab = ({ messages }: ChatTabProps) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [messages]);
  return (
    <div className="h-full min-h-0 max-h-[85vh] flex flex-col p-4">
      <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-2">
        {messages.map((message) => (
          <MessageCard key={message.id} message={message} />
        ))}
        <div ref={bottomRef} />
      </div>

      <Input
        className="mt-4 shrink-0 bg-secondary rounded-md border-0 pl-4"
        placeholder="Ask a question..."
      />
    </div>
  );
};

export default ChatTab;
