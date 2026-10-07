# FileQuery

A document question-answering platform that lets users upload files into project-based knowledge bases and ask questions grounded in their documents using Retrieval-Augmented Generation (RAG).

**🔗 [Live Deployment](https://file-query-frontend-752853711822.europe-west1.run.app/)**

---

## Core Features

* **Project-Based Knowledge Bases:** Organise uploaded documents into separate projects so each conversation only uses the relevant project files.
* **Multi-Format File Support:** Upload and extract text from TXT, Markdown, CSV, PDF, DOC, and DOCX files.
* **Structured Document Extraction:** Extracts document text while preserving useful structure such as headings and tables where supported.
* **Smart Text Splitting:** Uses LangChain text splitters to create overlapping chunks while respecting Markdown headings and natural text boundaries.
* **Semantic Retrieval:** Generates vector embeddings for document chunks using Amazon Titan Text Embeddings V2 and searches them with PostgreSQL and pgvector.
* **Query Rewriting:** Rewrites conversational or vague questions into clearer standalone search queries before retrieval, improving the quality of relevant document context.
* **Grounded AI Answers:** Uses Amazon Nova Micro to answer questions using retrieved document context and instructs the model not to rely on information outside the uploaded documents.
* **Conversational Context:** Uses previous messages to resolve references and follow-up questions such as "What about the other one?"
* **Asynchronous File Processing:** Uploaded files are processed through an SQS queue and Lambda worker so embedding generation does not block the main API.
* **Source-Aware Conversations:** Retrieved document chunks can be associated with assistant messages so responses can be traced back to the underlying document content.
* **Secure Project Access:** Projects and files are scoped to the authenticated user.

---

## Technical Architecture

The platform uses a modern full-stack architecture with Next.js and FastAPI, backed by PostgreSQL and AWS services for storage, asynchronous processing, embeddings, and AI generation.

### Backend Layer

The backend handles authentication, project and file management, document processing, retrieval, and AI orchestration.

* **Language:** Python 3.14
* **Framework:** FastAPI
* **ORM:** SQLAlchemy 2.0
* **Database:** PostgreSQL
* **Vector Search:** pgvector
* **Authentication:** JWT with HTTP-only cookies
* **Object Storage:** Amazon S3
* **Background Processing:** Amazon SQS + AWS Lambda
* **Embeddings:** Amazon Titan Text Embeddings V2
* **Chat Model:** Amazon Nova Micro

### Frontend Layer

The frontend provides the project workspace, file management, chat interface, and asynchronous API communication.

* **Framework:** Next.js
* **Language:** TypeScript
* **Styling:** Tailwind CSS
* **UI Components:** shadcn/ui
* **Data Fetching:** Next.js Server Actions and API requests
* **Authentication:** HTTP-only access-token cookie

### RAG Pipeline

FileQuery processes documents through the following pipeline:

```text
File Upload
    ↓
Amazon S3
    ↓
SQS Queue
    ↓
AWS Lambda
    ↓
Text Extraction
    ↓
LangChain Text Splitting
    ↓
Amazon Titan Text Embeddings V2
    ↓
PostgreSQL + pgvector
    ↓
Query Rewriting
    ↓
Vector Retrieval
    ↓
Retrieved Context
    ↓
Amazon Nova Micro
    ↓
Grounded Answer
```

---

## Technology Matrix

| Component | Technology | Primary Purpose |
| :--- | :--- | :--- |
| **Frontend** | Next.js / TypeScript | Web application and user interface |
| **UI** | Tailwind CSS / shadcn/ui | Responsive styling and reusable components |
| **Backend** | Python / FastAPI | REST API and application logic |
| **ORM** | SQLAlchemy 2.0 | Database access and relational state management |
| **Database** | PostgreSQL | Application and document metadata storage |
| **Vector Search** | pgvector | Semantic similarity search over document embeddings |
| **Object Storage** | Amazon S3 | Persistent file storage |
| **Queue** | Amazon SQS | Asynchronous file-processing jobs |
| **Worker** | AWS Lambda | Document extraction and embedding generation |
| **Embeddings** | Amazon Titan Text Embeddings V2 | Convert document chunks and queries into vectors |
| **AI Model** | Amazon Nova Micro | Generate grounded answers from retrieved context |
| **Text Splitting** | LangChain Text Splitters | Chunk documents for retrieval |
| **Deployment** | Google Cloud Run | Host the frontend and backend services |

---

## Supported File Types

| Format | Purpose |
| :--- | :--- |
| **TXT** | Plain-text documents |
| **Markdown** | Structured text and documentation |
| **CSV** | Tabular data |
| **PDF** | Documents and reports |
| **DOCX** | Microsoft Word documents |
| **DOC** | Legacy Microsoft Word documents |

---

## Retrieval Flow

When a user asks a question, FileQuery:

1. Uses the conversation history to rewrite the question into a clearer retrieval query when necessary.
2. Generates an embedding for the rewritten query.
3. Searches project-scoped document chunks using pgvector.
4. Provides the most relevant chunks as context to Amazon Nova Micro.
5. Generates a response grounded only in the retrieved document content.

This allows conversational questions to be resolved using both the current message and the previous conversation context.

---

## Deployment

The application is deployed using Google Cloud Run, while AWS services are used for document storage, asynchronous processing, embeddings, and AI inference.

The frontend and backend are deployed independently, while document-processing jobs run asynchronously through SQS and Lambda.

---

## Goals

FileQuery is designed to demonstrate practical full-stack and backend engineering alongside a production-style RAG architecture, including:

* document ingestion and processing
* asynchronous background jobs
* vector search with PostgreSQL
* conversational retrieval
* cloud storage and compute
* AI-powered question answering
* secure project-scoped data access
