import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { SCREENSHOTS } from "@/lib/screenshots";
import {
  ArrowLeft,
  BrainCircuit,
  FolderKanban,
  ListOrdered,
  Search,
  UploadCloud,
  Wand2,
} from "lucide-react";

export const metadata: Metadata = {
  title: "About FileQuery",
  description:
    "What FileQuery does, how a question becomes an answer, and how it is built.",
};

const features = [
  {
    title: "Answers from your documents",
    description:
      "Ask a question in plain language. The answer is written only from passages found in your own files, and it links back to them.",
    icon: BrainCircuit,
  },
  {
    title: "Six file types",
    description:
      "Upload TXT, Markdown, CSV, PDF, DOC or DOCX files and preview them in the app.",
    icon: UploadCloud,
  },
  {
    title: "Follow-up questions",
    description:
      "A question like “What about the other one?” is rewritten using the conversation so far, so the search still makes sense.",
    icon: Wand2,
  },
  {
    title: "Two kinds of search",
    description:
      "Search by meaning and by exact words at the same time, then merge the two lists, so both paraphrases and exact terms are found.",
    icon: Search,
  },
  {
    title: "Best passages first",
    description:
      "A second model re-checks the top passages against your question and puts the most useful ones first.",
    icon: ListOrdered,
  },
  {
    title: "Separate projects",
    description:
      "Each project has its own files and conversations. A search only looks at the project you are in.",
    icon: FolderKanban,
  },
];

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto max-w-5xl px-4 md:px-6 pt-16 pb-24">
        <Link
          href="/"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to home
        </Link>

        <h1 className="mt-8 text-4xl md:text-5xl font-extrabold tracking-tight text-foreground">
          About FileQuery
        </h1>
        <p className="mt-4 max-w-3xl text-lg text-muted-foreground leading-relaxed">
          FileQuery lets you ask questions about your own documents. When the
          documents do not contain the answer, it tells you so instead of
          guessing.
        </p>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map(({ title, description, icon: Icon }) => (
            <div
              key={title}
              className="rounded-2xl border border-border bg-card p-8 flex flex-col gap-4"
            >
              <div className="h-14 w-14 rounded-xl bg-primary/10 flex items-center justify-center mb-2">
                <Icon className="w-8 h-8 text-primary" aria-hidden="true" />
              </div>
              <h2 className="text-xl font-bold text-card-foreground">
                {title}
              </h2>
              <p className="text-muted-foreground leading-relaxed">
                {description}
              </p>
            </div>
          ))}
        </div>

        <section className="mt-16">
          <h2 className="text-2xl font-bold text-foreground">See it working</h2>
          <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
            {SCREENSHOTS.map((shot) => (
              <figure key={shot.src} className="m-0">
                <Image
                  src={shot.src}
                  alt={shot.alt}
                  width={1440}
                  height={900}
                  className="w-full h-auto rounded-2xl border border-border"
                />
                <figcaption className="mt-2 text-sm text-muted-foreground">
                  {shot.caption}
                </figcaption>
              </figure>
            ))}
          </div>
        </section>

        <section className="mt-16 rounded-2xl border border-border bg-card p-8 md:p-10">
          <h2 className="text-2xl font-bold text-card-foreground">
            How it&apos;s built
          </h2>
          <p className="mt-4 max-w-3xl text-muted-foreground leading-relaxed">
            Files upload straight to cloud storage, and a background worker
            reads each one, splits it into passages and stores a numeric
            fingerprint of each passage in PostgreSQL. A question is searched
            two ways, merged, reranked and handed to a language model that may
            only use what was found. The test suite runs the whole pipeline
            with stand-ins for the AI services, so it never calls them.
          </p>
          <p className="mt-4 max-w-3xl text-muted-foreground leading-relaxed">
            The README explains each decision, what it costs and where the
            code is, and lists the known limitations.
          </p>
          <Link
            href="https://github.com/Akhere-G/file-query"
            target="_blank"
            rel="noreferrer"
            className="mt-6 inline-flex h-12 items-center justify-center rounded-xl border border-border bg-background px-8 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Read the code on GitHub
          </Link>
        </section>
      </main>
    </div>
  );
}
