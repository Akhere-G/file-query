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
import { FileWarningIcon, Info, Loader2, Send } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import {
  getMessages,
  sendMessage as sendMessageAction,
} from "@/features/chat/server-actions";
import { toast } from "@/components/ui/toast";
import { ProjectFile } from "../types";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { track } from "@/lib/analytics/client";
import { lengthBucket } from "@/lib/analytics/events";

const PAGE_SIZE = 20;
const MAX_MESSAGE_LENGTH = 2000;
const LOAD_MORE_THRESHOLD_PX = 50;

const showError = (message?: string | null) =>
  toast.add({ title: message ?? "Something went wrong", type: "error" });

const createOptimisticMessage = (content: string): Message => ({
  id: -Date.now(),
  owner: "user",
  content,
  createdAt: new Date().toISOString(),
  citations: [],
});

interface ChatTabProps {
  projectId: number | null;
  files: ProjectFile[];
  isLoading: boolean;
  error: string;
  allFilesProcessing: boolean;
}

const ChatTab = ({ projectId, ...props }: ChatTabProps) => (
  <ChatPanel key={projectId ?? "none"} projectId={projectId} {...props} />
);

const ChatPanel = ({
  projectId,
  isLoading,
  allFilesProcessing,
  error,
}: ChatTabProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isFetchingMessages, setIsFetchingMessages] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  const cursorRef = useRef<number | null>(null);
  const hasMoreRef = useRef(true);
  const isLoadingRef = useRef(false);

  const scrollBeforePrependRef = useRef<{
    height: number;
    top: number;
  } | null>(null);

  const loadOlder = useCallback(async () => {
    if (!projectId || isLoadingRef.current || !hasMoreRef.current) {
      return;
    }

    setIsFetchingMessages(true);
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

      setMessages((prev) => {
        if (prev) return [...res.data.messages, ...prev];
        return res.data.messages;
      });
    } catch {
      showError();
    } finally {
      isLoadingRef.current = false;
      setIsFetchingMessages(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadOlder();
  }, [loadOlder]);

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container || messages?.length === 0) return;

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

    track("chat_message_sent", {
      length_bucket: lengthBucket(content.length),
      is_first_message: messages.length === 0 && !hasMoreRef.current,
    });

    const optimistic = createOptimisticMessage(content);
    setMessages((prev) => {
      if (prev) return [...prev, optimistic];
      return [optimistic];
    });
    setText("");
    setIsSending(true);

    const result = await sendMessageAction(projectId, content).catch(
      () => null,
    );
    setIsSending(false);

    if (result?.success) {
      setMessages((prev) => {
        if (prev) return [...prev, result.data];
        return [result.data];
      });
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

  const cannotSend =
    !projectId || isSending || isLoading || allFilesProcessing || !!error;

  return (
    <div className="relative h-full min-h-0 max-h-[85vh] flex flex-col p-4">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-2 [overflow-anchor:none]"
      >
        {isFetchingMessages && (
          <div className="w-full flex flex-col justify-center items-center gap-2 p-4">
            <h2 className="font-bold">Loading...</h2>
            <Loader2 className="animate-spin" width={24} height={24} />
          </div>
        )}
        {messages?.map((message) => (
          <MessageCard key={message.id} message={message} />
        ))}

        {!projectId && (
          <div className="border-dashed border-2 p-4 py-20 text-center rounded-2xl">
            <h3 className="font-medium">Upload files to start chatting</h3>
          </div>
        )}
      </div>
      {allFilesProcessing && (
        <Alert className="mt-4">
          <Info />
          <AlertTitle>All files are still processing</AlertTitle>
          <AlertDescription>
            Once some files are successfuly uploaded and processed you can query
            them in the chat.
          </AlertDescription>
        </Alert>
      )}
      {error && (
        <Alert className="mt-4">
          <FileWarningIcon />
          <AlertTitle>Sorry, something went wrong...</AlertTitle>
          <AlertDescription>
            Please refresh the page and try again
          </AlertDescription>
        </Alert>
      )}

      <div className="relative">
        <Textarea
          className="mt-4 min-h-0 shrink-0 bg-secondary rounded-md border-0 pl-4"
          placeholder="Ask a question..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={MAX_MESSAGE_LENGTH}
          disabled={cannotSend}
        />

        <Button
          className="right-2 top-6 absolute h-8 w-8 p-0 rounded-md"
          onClick={sendMessage}
          disabled={cannotSend}
        >
          <Send size={16} />
        </Button>
      </div>
    </div>
  );
};

export default ChatTab;
