"use client";

import { Message } from "@/features/chat/types";
import MessageCard from "./MessageCard";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { Button } from "@/components/ui/button";
import { Send } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { sendMessage as sendMessageAction } from "@/features/chat/server-actions";
import { toast } from "@/components/ui/toast";
import { getMessages } from "@/features/chat/actions";

const PAGE_SIZE = 20;
const LOAD_MORE_THRESHOLD_PX = 50;

const showError = (message?: string | null) =>
  toast.add({ title: message ?? "Something went wrong", type: "error" });

const createOptimisticMessage = (content: string): Message => ({
  id: -Date.now(),
  owner: "user",
  content,
  createdAt: new Date().toISOString(),
});

interface ChatTabProps {
  projectId: number | null;
}

const ChatTab = ({ projectId }: ChatTabProps) => (
  <ChatPanel key={projectId ?? "none"} projectId={projectId} />
);

const ChatPanel = ({ projectId }: ChatTabProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [isSending, setIsSending] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  const cursorRef = useRef<number | null>(null);
  const hasMoreRef = useRef(true);
  const isLoadingRef = useRef(false);

  const scrollBeforePrependRef = useRef<{
    height: number;
    top: number;
  } | null>(null);

  const loadOlder = useCallback(async () => {
    if (!projectId || isLoadingRef.current || !hasMoreRef.current) return;

    isLoadingRef.current = true;
    const isFirstPage = cursorRef.current === null;

    try {
      const res = await getMessages(projectId, cursorRef.current, PAGE_SIZE);

      if (!res.success) {
        showError(res.message ?? "Something went wrong");
        return;
      }

      cursorRef.current = res.data.nextCursor;
      hasMoreRef.current = res.data.hasMore;

      const container = containerRef.current;
      if (!isFirstPage && container) {
        scrollBeforePrependRef.current = {
          height: container.scrollHeight,
          top: container.scrollTop,
        };
      }

      setMessages((prev) => [...res.data.messages, ...prev]);
    } catch {
      showError();
    } finally {
      isLoadingRef.current = false;
    }
  }, [projectId]);

  useEffect(() => {
    loadOlder();
  }, [loadOlder]);

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container || messages.length === 0) return;

    const before = scrollBeforePrependRef.current;

    if (before) {
      container.scrollTop =
        before.top + (container.scrollHeight - before.height);
      scrollBeforePrependRef.current = null;
    } else {
      container.scrollTop = container.scrollHeight;
    }

    if (container.scrollHeight <= container.clientHeight) {
      loadOlder();
    }
  }, [messages, loadOlder]);

  const handleScroll = () => {
    if (
      containerRef.current &&
      containerRef.current.scrollTop <= LOAD_MORE_THRESHOLD_PX
    ) {
      loadOlder();
    }
  };

  const sendMessage = async () => {
    const content = text.trim();
    if (!projectId || isSending || !content) return;

    const optimistic = createOptimisticMessage(content);
    setMessages((prev) => [...prev, optimistic]);
    setText("");
    setIsSending(true);

    const result = await sendMessageAction(projectId, content).catch(
      () => null,
    );
    setIsSending(false);

    if (result?.success) {
      setMessages((prev) => [...prev, result.data]);
      return;
    }

    setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
    setText(content);
    showError(result?.message);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="relative h-full min-h-0 max-h-[85vh] flex flex-col p-4">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-2 [overflow-anchor:none]"
      >
        {messages.map((message) => (
          <MessageCard key={message.id} message={message} />
        ))}

        {!projectId && (
          <div className="border-dashed border-2 p-4 py-20 text-center rounded-2xl">
            <h3 className="font-medium">Upload files to start chatting</h3>
          </div>
        )}
      </div>

      <div className="relative">
        <Textarea
          className="mt-4 min-h-0 shrink-0 bg-secondary rounded-md border-0 pl-4"
          placeholder="Ask a question..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSending || !projectId}
        />

        <Button
          className="right-2 top-6 absolute h-8 w-8 p-0 rounded-md"
          onClick={sendMessage}
          disabled={isSending || !projectId}
        >
          <Send size={16} />
        </Button>
      </div>
    </div>
  );
};

export default ChatTab;
