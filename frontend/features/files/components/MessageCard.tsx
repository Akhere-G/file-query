import ReactMarkdown from "react-markdown";
import { Message } from "@/features/chat/types";
import CitationDetail from "./CitationDetail";

export default function MessageCard({ message }: { message: Message }) {
  const { content, owner, citations } = message;

  return (
    <div
      className={`rounded-2xl px-3 py-2 ${
        owner === "user"
          ? "ml-[10%] bg-primary text-primary-foreground"
          : "mr-[10%] bg-secondary text-secondary-foreground"
      }`}
    >
      <div
        className={`prose prose-sm max-w-none ${
          owner === "user"
            ? "shimmer-color-yellow-500 reverse-selection"
            : "dark:reverse-selection"
        }`}
      >
        <ReactMarkdown
          skipHtml
          components={{
            // A remote image in a reply can leak chat content through its URL
            // (for example after a prompt injection in an uploaded document).
            img: () => null,
            a: ({ href, children }) => (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
        {citations.length > 0 && (
          <div className="mt-4 flex gap-2 flex-wrap">
            {citations.map((citation) => (
              <CitationDetail key={citation.title} citation={citation} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
