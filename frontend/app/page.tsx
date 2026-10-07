import Link from "next/link";
import {
  BrainCircuit,
  UploadCloud,
  Wand2,
  Search,
  ListOrdered,
  KanbanSquare,
  ArrowRight,
} from "lucide-react";

export default function Home() {
  const features = [
    {
      title: "RAG AI Integration",
      description:
        "Chat with your documents using Retrieval-Augmented Generation. Answers are written only from the information retrieved from your own files.",
      icon: <BrainCircuit className="w-8 h-8 text-primary" />,
    },
    {
      title: "File Upload & View ",
      description:
        "Upload text, markdown, pdfs, documents, or csv files, and preview them in the app.",
      icon: <UploadCloud className="w-8 h-8 text-primary" />,
    },
    {
      title: "Query Rewriting",
      description:
        "Follow-up questions are rewritten using your chat history, so searches make sense even when your question doesn't stand on its own.",
      icon: <Wand2 className="w-8 h-8 text-primary" />,
    },
    {
      title: "Hybrid Search",
      description:
        "Combines semantic search (matching meaning) with PostgreSQL keyword search (matching exact terms), merged using Reciprocal Rank Fusion, so you always find what you need to know.",
      icon: <Search className="w-8 h-8 text-primary" />,
    },
    {
      title: "Reranking",
      description:
        "After searching, the best-matching passages are re-checked against your question and reordered, so the most useful ones come first.",
      icon: <ListOrdered className="w-8 h-8 text-primary" />,
    },
    {
      title: "Project Management",
      description:
        "Organise files and conversations into separate projects. Searches only ever look at the files in the project you are working in.",
      icon: <KanbanSquare className="w-8 h-8 text-primary" />,
    },
  ];

  const stack = [
    "Next.js",
    "TypeScript",
    "Tailwind CSS",
    "React",
    "FastAPI",
    "Python",
    "SQLAlchemy",
    "PostgreSQL",
    "pgvector",
    "Amazon Bedrock",
  ];

  return (
    <div className="min-h-screen bg-background selection:bg-primary/30 selection:text-primary-foreground">
      <div className="container mx-auto px-4 md:px-6 pt-24 pb-16 lg:pt-32 flex flex-col items-center justify-center text-center">
        <div className="space-y-6 max-w-4xl mx-auto">
          <div className="inline-flex items-center rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-sm text-primary">
            <span className="flex h-2 w-2 rounded-full bg-primary mr-2"></span>
            Production-Ready AI Search
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-foreground">
            Intelligent Document <br className="hidden md:block" />
            <span className="text-primary">Query & Management</span>
          </h1>

          <p className="max-w-2xl mx-auto text-lg md:text-xl text-muted-foreground">
            A fullstack platform built to ingest, process, and query your
            knowledge base using retrieval-augmented generation, hybrid search,
            and reranking.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-8">
            <Link
              href="/dashboard"
              className="inline-flex h-12 items-center justify-center rounded-xl bg-primary px-8 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Get Started
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link
              href="https://github.com/Akhere-G/file-query"
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-12 items-center justify-center rounded-xl border border-border bg-background px-8 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              View Source
            </Link>
          </div>
        </div>

        <div className="mt-24 w-full max-w-5xl">
          <p className="text-sm font-semibold tracking-wider text-muted-foreground uppercase mb-8">
            Powered by modern technologies
          </p>
          <div className="flex flex-wrap justify-center gap-3 md:gap-6">
            {stack.map((tech) => (
              <div
                key={tech}
                className="px-4 py-2 rounded-lg border border-border bg-card text-card-foreground text-sm font-medium"
              >
                {tech}
              </div>
            ))}
          </div>
        </div>

        <div className="mt-32 w-full max-w-6xl text-left">
          <div className="mb-12 text-center">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
              Platform Features
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              Engineered from the ground up to provide a robust, accurate, and
              scalable document query experience.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <div
                key={index}
                className="rounded-2xl border border-border bg-card p-8 flex flex-col gap-4"
              >
                <div className="h-14 w-14 rounded-xl bg-primary/10 flex items-center justify-center mb-2">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-bold text-card-foreground">
                  {feature.title}
                </h3>
                <p className="text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-32 mb-16 w-full max-w-4xl rounded-3xl border border-border bg-card p-12 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to experience it?</h2>
          <p className="text-muted-foreground mb-8 text-lg max-w-xl mx-auto">
            Dive into the dashboard to start uploading documents, setting up
            projects, and querying your data.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex h-12 items-center justify-center rounded-xl bg-foreground px-8 text-sm font-medium text-background hover:bg-foreground/90"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
