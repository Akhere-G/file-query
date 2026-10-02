"use client";

import { Message } from "@/features/chat/types";
import MessageCard from "./MessageCard";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Send } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { sendMessage as sendMessageAction } from "@/features/chat/server-actions";
import { toast } from "@/components/ui/toast";
interface ChatTabProps {
  messages: Message[];
  projectId: number | null;
}

const ChatTab = ({ messages, projectId }: ChatTabProps) => {
  const [chatMessages, setChatMessages] = useState(messages);
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "end",
      });
    });

    function updateChatMessages() {
      setChatMessages(messages);
    }
    updateChatMessages();
  }, [messages]);

  const sendMessage = async () => {
    if (isSending || !projectId) return;
    try {
      setIsSending(true);
      const aiResponse = await sendMessageAction(projectId, message);
      if (aiResponse.success) {
        setChatMessages((prev) => prev.concat(aiResponse.data));
        setMessage("");
      } else {
        toast.add({
          title: aiResponse.message ?? "Something went wrong",
          type: "error",
        });
      }
    } catch {
      toast.add({ title: "Something went wrong", type: "error" });
    } finally {
      setIsSending(false);
    }
  };
  return (
    <div className="h-full min-h-0 max-h-[85vh] flex flex-col p-4">
      <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-2">
        {chatMessages.map((message) => (
          <MessageCard key={message.id} message={message} />
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="relative">
        <Textarea
          className="mt-4 min-h-0 shrink-0 bg-secondary rounded-md border-0 pl-4"
          placeholder="Ask a question..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={isSending}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
        />
        <Button
          className="right-2 top-6 absolute h-8 w-8 p-0 rounded-md"
          onClick={sendMessage}
          disabled={isSending}
        >
          <Send size={16} />
        </Button>
      </div>
    </div>
  );
};

export default ChatTab;
