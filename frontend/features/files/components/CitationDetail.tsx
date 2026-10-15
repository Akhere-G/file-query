import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Citation } from "@/features/chat/types";
import { FileText } from "lucide-react";

export default function CitationDetail({ citation }: { citation: Citation }) {
  const { title, content, fileName } = citation;

  return (
    <Dialog>
      <DialogTrigger className="inline-flex max-w-56 items-center gap-2 rounded-lg border bg-card px-3 py-2 text-left text-sm transition-colors hover:bg-accent">
        <FileText className="size-4 shrink-0 text-muted-foreground" />
        <span className="truncate">{title}</span>
      </DialogTrigger>

      <DialogContent className="flex max-h-[85dvh] flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl">
        <DialogHeader className="border-b px-6 py-5 pr-12">
          <DialogTitle className="text-lg leading-snug">{title}</DialogTitle>
          <DialogDescription>Source citation</DialogDescription>
        </DialogHeader>

        <div className="min-h-0 space-y-6 overflow-y-auto px-6 py-5">
          <section className="space-y-2">
            <h3 className="text-sm font-semibold">Source file</h3>
            <div className="flex items-start gap-3 rounded-lg border bg-muted/40 p-3">
              <FileText className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
              <p className="break-all text-sm text-muted-foreground">
                {fileName}
              </p>
            </div>
          </section>

          <section className="space-y-2">
            <h3 className="text-sm font-semibold">Cited text</h3>
            <div className="rounded-lg border bg-muted/20 p-4">
              <p className="whitespace-pre-wrap wrap-break-word text-sm leading-7">
                {content}
              </p>
            </div>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
