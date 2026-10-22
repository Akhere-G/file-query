# Audit remediation spec (F1–F20)

**Status:** proposed, nothing implemented. Findings are described in `docs/audit/2026-10-22-findings.md`. Paths are relative to the repo root. "Tests" means pytest unless stated. Effort is from the findings file.

## 0. Decisions already made

| Topic | Decision |
|---|---|
| Demo | Read-only. A decorator blocks every mutating route for demo users. Chat is still allowed but is **not persisted**. |
| Rate-limit key | Authenticated routes: user id. Login, register, demo: client IP forwarded by the Next.js server. Demo chat: client IP. |
| F2 | Application-side limits only. SQS, Lambda and budget settings are out of scope. |
| F4 | Simplest approach: mark the file as errored on failure, tolerant text decoding, no background reconciler. |

## 1. Open choices (defaults in bold, change them before implementing if you disagree)

- **F8:** install `antiword` in the Lambda image if it is one line; otherwise **drop `.doc` support**.
- **F2:** default `MAX_FILE_SIZE` becomes **50 MB** (was 500 MB). The upload hint text changes with it.
- **F2:** chunk titles become **heuristic** (no LLM call per chunk). The LLM mode stays available behind a setting.
- **F18:** `frontend/public/og-image.jpg` needs an image from you. Until then the metadata reference stays broken.

## 2. Implementation order

1. **F17 harness first** (pytest, conftest, Postgres+pgvector test DB, CI workflow). Every later item adds tests to it.
2. **F13** (shared AWS clients, engine settings). F2 and F8 build on it.
3. **F1** (limiter) together with the small frontend header change.
4. **F3** (demo guard) and **F11** (chat refactor). Both touch `chat_service.send_user_message`, so do them in one PR.
5. **F10**, then **F4**, **F2**, **F8**, **F9**, **F14**.
6. **F7** (index migration), then **F6** (slim project endpoints).
7. Frontend batch: **F5**, **F15**, **F16**, **F12** (Next upgrade).
8. **F18**, **F19**, **F20**.

Migrations are added by F7 and F19 only. Current Alembic head is `7c1e4b9a2d35`.

---

## F1. Make rate limiting work and key it correctly

**Goal:** limits are enforced, and one user or visitor cannot consume another's budget.

**Changes**
1. Fix the decorator order in `backend/src/features/auth/user_routes.py` (register, token, login, me), `backend/src/features/files/file_routes.py` (`upload_files`) and `backend/src/features/chat/chat_routes.py` (`send_chat_messsage`). Required order, top to bottom: `@router.post(...)`, `@limiter.limit(...)`, optional `@block_demo` (see F3), then `def`. Every limited function needs `request: Request` (they already have it).
2. Add `@limiter.limit("30/hour")` to `POST /api/auth/demo` (it needs a `request: Request` parameter).
3. `backend/src/limiter.py`: replace `get_remote_address` with `rate_limit_key(request)`:
   - If an `Authorization: Bearer` token decodes (use `jwt.decode`, no DB call) and the claims do **not** contain `demo: true`, return `user:<sub>`.
   - Otherwise, if header `X-Internal-Secret` equals `settings.INTERNAL_API_SECRET` (compare with `hmac.compare_digest`) and `X-Client-IP` is present, return `ip:<X-Client-IP>`.
   - Otherwise return `ip:<socket address>`.
   - Construct the limiter with `swallow_errors=True` so a Redis outage logs instead of failing every request.
4. `backend/src/settings.py`: add `INTERNAL_API_SECRET: str | None = None`. When unset (local dev) the forwarded header is ignored.
5. Frontend, `frontend/lib/api.ts`: add `getClientHeaders()` that reads `x-forwarded-for` (first entry) from `headers()` and returns `X-Client-IP` plus `X-Internal-Secret` (from `process.env.INTERNAL_API_SECRET`). Use it in `authenticate()` in `frontend/features/auth/api/authApi.ts` (login, register, demo) and in `sendMessage` in `frontend/features/chat/server-actions.ts` (demo chat is keyed by IP).
6. Limits: keep the current 20/hour on register, login and token, 20/hour on upload, 30/hour on chat. Add 30/hour on demo.

**Tests**
- 21st login attempt from the same forwarded IP returns 429; a different forwarded IP does not.
- Two different users do not share an upload bucket.
- A request with a wrong `X-Internal-Secret` and a spoofed `X-Client-IP` is keyed by socket address.
- Regression test that fails if any `@limiter.limit` sits above a route decorator (inspect `router.routes` and check each limited endpoint is wrapped).

**Done when:** the reproduction from the audit shows `200, 200, 429` for the real routes. **Effort:** S + M.

---

## F2. Bound document processing (application side)

**Goal:** no single file or request can create unbounded chunks, Bedrock calls or time.

**Changes**
1. `backend/src/settings.py`: add `MAX_FILES_PER_REQUEST=10`, `MAX_PDF_PAGES=300`, `MAX_EXTRACTED_CHARS=1_500_000`, `MAX_CHUNKS_PER_FILE=1000`, `EMBED_CONCURRENCY=4`, `CHUNK_TITLE_MODE="heuristic"`. Change `MAX_FILE_SIZE` default to 50 MB.
2. `backend/src/features/files/file_routes.py` `upload_files`: reject `len(files_in) > MAX_FILES_PER_REQUEST` with `BadRequestError`.
3. New `ProcessingLimitError(Exception)` with a user-safe `message` in `backend/src/exceptions.py`.
4. `file_extraction_service.py`:
   - `extract_pdf`: check `document.page_count > MAX_PDF_PAGES` before `to_markdown`.
   - `extract_file`: after extraction, raise if `len(text) > MAX_EXTRACTED_CHARS`.
5. `file_processing_service.py`:
   - after chunking, raise `ProcessingLimitError("This file is too large to process")` if `len(chunks) > MAX_CHUNKS_PER_FILE`.
   - `create_chunks`: compute titles with a new `derive_chunk_title(content)` (first markdown heading line, else first sentence truncated to 100 characters) when `CHUNK_TITLE_MODE == "heuristic"`; keep the current LLM call for `"llm"`.
   - generate embeddings with `ThreadPoolExecutor(max_workers=EMBED_CONCURRENCY)` using `map` to preserve chunk order.
6. Use the shared cached clients from F13 so there is no client construction per call.
7. Demo and normal paths share the same limits. Fix the message in `demo_service` if the function survives F3 (it will be removed there).
8. Frontend upload hint in `frontend/features/files/components/FilesTabs.tsx` ("up to 500MB") reads the real limit (export it as a constant or fetch it once).

**Tests:** a 1,001-chunk fixture is rejected with `status=error`; a 301-page PDF is rejected; heuristic titles are non-empty and at most 100 characters; embeddings keep input order under concurrency (fake client with random delays).

**Done when:** an oversize file ends in `error` with a readable message and makes zero Bedrock calls beyond the cap. **Effort:** S for caps, M for titles and concurrency.

---

## F3. Read-only demo through a decorator

**Goal:** demo users cannot mutate anything through the API. Chat works but is not persisted.

**Changes**
1. New `backend/src/features/demo/demo_guard.py`:
   - `block_demo(func)` using `functools.wraps`. At decoration time it checks that the function is synchronous (all current routes are `def`) and has a parameter annotated `User`; otherwise it raises `TypeError` so misuse fails at import, not at request time. At call time it finds the `User` argument in `kwargs` and raises `DemoReadOnlyError` if `user.is_demo`.
   - `DemoReadOnlyError(AppError)`: status 403, message "The shared demo is read-only. Register to upload and manage your own files."
2. Apply `@block_demo` directly above the function on: `upload_files`, `confirm_uploads`, `delete_file` (`file_routes.py`), `rename_project`, `delete_project` (`project_routes.py`). Not on any `GET`. Not on chat.
3. Remove `demo_service.enforce_upload_limits` and the `if user.is_demo` branch in `upload_files` (now unreachable). `demo_seed_service` calls services directly, so seeding is unaffected.
4. Demo chat without persistence:
   - Split `chat_service.send_user_message` into `generate_answer(db, project_id, content, conversation) -> (text, citations)` and the persisting wrapper (this is the same refactor F11 needs).
   - In `chat_routes.send_chat_messsage`, if `user.is_demo`: call `generate_answer` with `conversation=""` (stateless, so follow-up questions do not see earlier turns), and return a `MessageResponse` built in memory (negative id from the current time in ms, `project_id`, `owner="assistant"`, `created_at=now`, citations from the chunks).
   - Demo limits: the monthly DB count no longer applies. Add a Redis counter `demo:chat:<YYYY-MM-DD>` (INCR, expire 2 days) with `DEMO_MAX_DAILY_MESSAGES=100`, and a per-IP limit of 10/hour (the F1 key function keys demo tokens by IP).
5. `backend/src/features/auth/user_service.py` `get_demo_access_token`: expiry from new `DEMO_TOKEN_EXPIRE_MINUTES=120`.
6. Frontend: pass `isDemo` (from `isDemoSession()` in `components/common/DemoBanner.tsx`) into `ProjectSidebar`, `FilesTabs` and `FileCard`; hide or disable upload, rename and delete for demo and show the 403 message if one slips through. Update the banner copy to say the demo is read-only and chat answers are not saved.

**Tests:** each of the five blocked routes returns 403 for a demo token and works for a normal user; a demo `GET` of projects, files and messages works; demo chat returns an answer and leaves the `messages` table unchanged; the daily cap returns 429; `block_demo` raises `TypeError` when applied to a function with no `User` parameter; `seed_demo` still completes against a test DB.

**Done when:** an anonymous visitor cannot change or delete anything in the demo project. **Effort:** S–M.

---

## F4. Failed processing marks the file as errored (simplest approach)

**Goal:** no file stays on "processing" because of a parse, decode or enqueue failure.

**Changes**
1. `file_processing_service.py`: add `mark_file_error(file_id, message)` that opens its own `SessionLocal`, and sets `status=error`, `error=message` only if the file is currently `processing`.
2. `process_file`: in the extract-stage `except`, send the analytics event, call `mark_file_error` (use `ProcessingLimitError.message` when applicable, otherwise "We couldn't read this file. Check that it isn't corrupt or password-protected."), and **return without re-raising**. Deterministic failures should not be retried by SQS. The existing embed-stage error handling stays as is.
3. `file_extraction_service.py`: add `decode_text(data)` that tries `utf-8-sig`, then falls back to `cp1252` with `errors="replace"`. Use it in `extract_text`, `extract_csv` and `extract_doc`.
4. `file_routes.confirm_uploads`: wrap `enqueue_files(files)` in `try/except`. On failure, mark those files `error` ("Could not start processing. Please re-upload.") and raise `AppError` with a 503.
5. Frontend polling ceiling is covered in F15.
6. Explicitly out of scope: a reconciler for files stuck in `processing` for hours.

**Tests:** a cp1252 CSV is processed; a corrupt PDF ends in `error` and is not re-raised; a simulated SQS failure leaves files in `error`; the message in `file.error` contains no stack trace or internal path.

**Effort:** S.

---

## F5. Keep chat history when a send fails

**Change** in `frontend/features/files/components/ChatTab.tsx` (the failure path around lines 175-179):

```ts
setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
setText(content);
showError(result?.message);
```

**Verify:** with two messages on screen, force a 429 and confirm both remain and the failed text returns to the box. **Effort:** S.

---

## F6. Slim the project endpoints and stop over-fetching

**Goal:** the dashboard no longer loads messages, citations or chunks.

**Changes**
1. `backend/src/features/project/project_schema.py`: add `ProjectSummary(id, name)`; use it as `response_model` for `GET /api/projects`, `GET /api/projects/{id}` and `PATCH /api/projects/{id}`. The frontend only uses `id` and `name` (`ProjectSidebar.tsx`), and the detail call is only a 404/403 check (`app/dashboard/page.tsx`).
2. `project_service.get_project`: remove the `with_messages` option (unused after this change); keep `with_files` for `delete_project`.
3. `frontend/features/project/types.ts`: reduce `Project` to `{ id, name }`.
4. `frontend/app/dashboard/page.tsx`: call `getProjects()` and `getProject()` with `Promise.all`.
5. `frontend/features/files/server-actions.ts`: remove `revalidatePath("/dashboard")` from `getFiles` (it runs on every 3-second poll). Keep it on upload, confirm and delete.
6. Eager-load the returned message's chunks and files in the chat response (`selectinload`) to avoid the small N+1 there.

**Tests:** with 3 projects × 50 messages × 5 citations, `GET /api/projects` issues at most 3 SQL statements (count with a SQLAlchemy `before_cursor_execute` listener); payload contains no `messages` or `files` keys.

**Effort:** M.

---

## F7. Add the missing indexes

**Changes**
1. New Alembic revision (down revision `7c1e4b9a2d35`) that, inside `op.get_context().autocommit_block()`, creates with `postgresql_concurrently=True, if_not_exists=True`: `ix_files_project_id`, `ix_chunks_file_id`, `ix_messages_project_id`, `ix_projects_user_id`, `ix_citations_chunk_id`. `downgrade` drops them.
2. Add `index=True` to those columns in the models so autogenerate stays clean (`file_model.py`, `message_model.py`).
3. No HNSW index now. Revisit when chunk counts justify it; the `similarity >= threshold` filter would need to change to benefit.

**Verify:** run `alembic upgrade head` on a copy of production data, then `EXPLAIN ANALYZE` the semantic and keyword queries before and after. **Effort:** S.

---

## F8. `.doc` support in the Lambda image

**Changes**
1. Check availability first: `docker run --rm --entrypoint dnf public.ecr.aws/lambda/python:3.14 info antiword`.
2. If available: add `RUN dnf install -y antiword && dnf clean all` to `backend/embedding_worker.Dockerfile`, and run the container locally with a sample `.doc`.
3. If not available in one line: remove `application/msword` from `file_schema.accepted_mime_types`, `file_extraction_service.EXTRACTION_METHODS`, `file_processing_service.mime_types`, the upload hint in `FilesTabs.tsx`, and the README table.
4. Either way, harden `extract_doc`: `subprocess.run(..., timeout=30)`, and convert a non-zero exit or timeout into a `ProcessingLimitError`-style user-safe failure (handled by F4).

**Tests:** a sample `.doc` extracts (if kept); a garbage file named `.doc` ends in `error`. **Effort:** S.

---

## F9. Upload, quota and cleanup fixes

**Changes**
1. `file_schema.FileBase.validate_size`: reject `v <= 0`.
2. `file_service.confirm_uploads`: replace `break` with marking the file `error` ("You have run out of storage"), deleting its S3 object, and continuing, so no file is left `pending`.
3. `file_service.get_used_storage`: use `select(func.coalesce(func.sum(File.size), 0))` instead of loading rows.
4. Delete the duplicate `max_user_storage` constants in `file_service.py` and use `settings.MAX_USER_STORAGE` everywhere.
5. `delete_file` and `project_service.delete_project`: delete the S3 object for every status (deleting a missing key is a no-op), and wrap the S3 call in `try/except` that logs, since the DB row is already gone.
6. New `backend/src/scripts/cleanup_pending.py` (same style as `seed_demo.py`, `--apply` flag): delete files that have been `pending` for more than 24 hours, together with their S3 objects. Scheduling it is out of scope.

**Tests:** negative size is rejected; a batch that overflows quota ends with every file either `processing` or `error`, none `pending`; deleting a pending file calls S3 delete; storage sum matches the old implementation on a fixture. **Effort:** M.

---

## F10. Don't overwrite a user's project name

**Changes**
1. `project_service.py`: add `DEFAULT_PROJECT_NAME = "New Project"` and use it in `file_routes.upload_files`.
2. `file_routes.confirm_uploads`: call `enqueue_files(files, rename_project=(project.name == DEFAULT_PROJECT_NAME))`; same condition in `process_files_locally`.
3. `file_processing_service.process_file`: replace the `is_last` flag with a DB check that no file in the project is still `pending` or `processing`, and only then call `name_project`.
4. `name_project`: re-check inside that the name still equals `DEFAULT_PROJECT_NAME` before writing; replace the `selectinload(Project.files).selectinload(File.chunks)` load with a query for file names and at most 30 chunk titles (`select(Chunk.title) ... limit(30)`).

**Tests:** renaming a project then uploading another file keeps the custom name; a new project still gets an AI name; no embeddings are loaded by `name_project` (query inspection). **Effort:** S.

---

## F11. Chat message validation and persistence

**Changes**
1. `chat_schema.MessageCreate.content`: `Field(min_length=1, max_length=2000)`, stripped. Match the frontend `Textarea` with `maxLength={2000}`.
2. `chat_routes.py`: `>=` instead of `>` in the monthly check.
3. `chat_service`: generate the answer first, then save the user message and assistant message together in one transaction (`create_message_pair`), so a Bedrock failure saves nothing and does not use up quota. This shares the `generate_answer` split with F3.
4. `get_messages`: `limit = min(max(limit or 30, 1), 30)` and guard `messages[-1]` against an empty list.
5. Known and accepted: the monthly cap check is not atomic; two simultaneous requests can exceed it by one.

**Tests:** 2,001-character message returns 422; the 41st message in a month is rejected; a failing Bedrock call leaves the message table unchanged; `?limit=-1` and `?limit=0` return 200. **Effort:** S.

---

## F12. Dependencies

**Changes**
1. `frontend/package.json`: `next` and `eslint-config-next` to `16.4.2` (pinned the same way); move `shadcn` to `devDependencies`; run `npm audit fix`; remove `cn` and add `clsx` and `tailwind-merge`.
2. `frontend/lib/utils.ts`: `export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }`. Change `from "cn"` to `from "@/lib/utils"` in `frontend/components/ui/*.tsx`.
3. `frontend/Dockerfile`: `npm ci` instead of `npm install`.
4. Backend: split `requirements.txt` into runtime and `requirements-dev.txt` (pytest, ruff, httpx, pip-audit). Remove `openai`, `onnxruntime`, `networkx` and other packages that a clean-venv import test shows are unused (verify with `pipdeptree` first; `sentry-sdk` stays if F17 wires it up).
5. Add `pip-audit` and `npm audit --omit=dev` to CI (F17).

**Verify:** `npm run build`, `tsc --noEmit`, `eslint`, a manual smoke test of dialogs, tabs and the sidebar (the `cn` swap touches every UI component); backend tests pass in a venv built from the trimmed requirements; the Lambda image builds and is smaller. **Effort:** S.

---

## F13. Shared AWS clients and database settings

**Changes**
1. New `backend/src/aws.py` with `@lru_cache` factories for `s3`, `sqs`, `bedrock-runtime` and `bedrock-agent-runtime`, all using one botocore `Config(connect_timeout=5, read_timeout=60, retries={"mode": "adaptive", "max_attempts": 5})`. Replace `file_service.get_s3_client`, `file_processing_service.get_sqs_client` and the two factories in `embedding_service.py`. Keep the S3 `signature_version="s3v4"` and virtual-addressing config.
2. `settings.py`: add `BEDROCK_RERANK_REGION="eu-central-1"` and `BEDROCK_RERANK_MODEL_ARN`, and use them in `rerank_chunks` instead of the hardcoded values.
3. `database.py`: `create_engine(url, pool_pre_ping=True, pool_recycle=1800, pool_size=DB_POOL_SIZE, max_overflow=DB_MAX_OVERFLOW)`; use `NullPool` when `AWS_LAMBDA_FUNCTION_NAME` is set so concurrent Lambdas do not each hold a pool.
4. Optional, measure first: end the read transaction in `send_user_message` before the Bedrock calls so a pooled connection is not held for the whole request.

**Tests:** clients are created once (patch `boto3.client` and count); the engine is built with `pool_pre_ping`. **Effort:** S–M.

---

## F14. File type detection

**Changes**
1. `frontend/features/files/server-actions.ts`: derive `mimeType` from the file extension (`.pdf`, `.doc`/`.docx` if kept, `.txt`, `.md`, `.csv`), falling back to `file.type`. Reject unsupported extensions in `FilesTabs.addFiles` with a toast, before any network call.
2. `backend/src/features/files/file_schema.py`: one shared constant mapping mime type to extension, with the `.doc` and `.docx` labels corrected; `FileCreate` validator that the filename extension matches the declared type; `name` limited to 255 characters with any path stripped.

**Tests:** `.md` with an empty browser type and `.csv` with `application/vnd.ms-excel` upload successfully; `report.pdf` declared as `text/csv` is rejected. **Effort:** S.

---

## F15. Upload feedback and polling

**Changes**
1. `FilesTabs.handleUpload`: if `confirmUploads` fails, show a toast with the server message and keep the files in the list; if some S3 uploads fail, toast "N file(s) failed to upload" and remove only the successful ones from the list.
2. `useGetFiles.ts`: retry a failed poll up to 3 times with backoff before showing the error; stop polling after about 5 minutes (100 polls) and show "Still processing, refresh to check again".
3. Remove the unused `isLoading` prop in `FilesTabs`.

**Tests (manual or component):** simulate a 400 on confirm and a rejected S3 upload; confirm the toast text and the list contents. **Effort:** S.

---

## F16. Block remote images in assistant markdown, add CSP

**Changes**
1. `frontend/features/files/components/MessageCard.tsx`: `<ReactMarkdown skipHtml components={{ img: () => null, a: (props) => <a {...props} target="_blank" rel="noopener noreferrer" /> }}>`.
2. `frontend/next.config.ts` `headers()`: add `Content-Security-Policy-Report-Only` first (default-src 'self'; img-src 'self' data:; connect-src 'self' the PostHog host and the S3 bucket host; script-src with what Next needs). Review the browser console for violations over a few days, then switch to enforcing.

**Verify:** a message containing `![x](https://example.com/a.png)` renders no image and sends no request. **Effort:** S.

---

## F17. Tests, CI and observability

**Changes**
1. `backend/requirements-dev.txt` plus `backend/tests/conftest.py`: set the required env vars, start from a Postgres + pgvector database (`pgvector/pgvector:pg16` service in CI, local Docker otherwise), run Alembic, and provide fixtures for a client, two users and a demo user. Monkeypatch `src/aws.py` clients with fakes. Bedrock embeddings return deterministic vectors.
2. First test files: `test_auth.py`, `test_ownership.py` (every route with another user's id), `test_rate_limit.py`, `test_uploads.py`, `test_extraction.py`, `test_demo_guard.py`, `test_chat.py`, and the regression tests named in F1–F11.
3. `.github/workflows/ci.yml` on pull requests and pushes to `main`: backend job (`ruff check`, `pytest`, `pip-audit`), frontend job (`npm ci`, `tsc --noEmit`, `eslint`, `npm audit --omit=dev --audit-level=high`, `npm run build`). Start `pip-audit` and `npm audit` as non-blocking and make them blocking after the F12 upgrades.
4. `build-and-push.yml`: run only after CI succeeds (`workflow_run` or a `needs` on the same workflow).
5. Delete `.github/workflows/test-aws.yml`.
6. Observability: initialise `sentry_sdk` in `src/main.py` when `SENTRY_DSN` is set (the package is already installed); no behaviour change when unset.
7. Delete `backend/test_bedrock.py` once the chat tests cover it.

**Done when:** CI is green on a clean checkout and fails on the F1 and F5-style regressions. **Effort:** M for the harness and first tests, L for broad coverage.

---

## F18. Hardening and config hygiene

**Changes**
1. `backend/src/main.py`: `allow_origins=[settings.FRONTEND_URL]`, plus `http://localhost:3000` only when `ENVIRONMENT != "production"`. Create the app with `docs_url=None, redoc_url=None, openapi_url=None` when `ENVIRONMENT == "production"`.
2. `frontend/next.config.ts` `headers()`: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (camera, microphone, geolocation off), `Strict-Transport-Security`. CSP is covered in F16.
3. `backend/Dockerfile` and `frontend/Dockerfile`: create and switch to a non-root user (`USER node` in the Next.js runner stage).
4. `frontend/public/`: add `.gitkeep` (git does not track empty directories) and the `og-image.jpg` from open choices; add `COPY --from=builder /app/public ./public` to the frontend Dockerfile.
5. `frontend/lib/analytics/client.ts`: remove the two `console.log` calls and the hardcoded fallback key, so analytics is simply off when the env var is unset (matches the README).

**Verify:** `curl -I` shows the headers; `/docs` returns 404 with `ENVIRONMENT=production`; both containers start as non-root. **Effort:** S.

---

## F19. Authentication hardening

**Changes**
1. Normalise emails (`strip().lower()`) in the `UserBase` validator and in `get_user_by_email`. New Alembic revision: check for existing case-collisions first (a query that lists them, and stop if any), lowercase existing emails, add a unique index on `lower(email)`.
2. Login: when the user does not exist, still run a bcrypt verification against a fixed dummy hash, so response time does not reveal which emails exist. Keep the 409 on register (usability), and rely on the F1 limit to slow enumeration.
3. Register: catch `IntegrityError` and return 409 instead of a generic 503.
4. Password maximum from 30 to 128 characters (backend `user_schema.py`, frontend `authSchema.ts`). `bcrypt_sha256` handles long inputs.
5. Add a small `get_owned_project(db, project_id, user)` helper that raises `NotFoundError` for both missing and not-owned projects, and use it in the project, file and chat routes. This also removes the duplicated ownership code and the 403-vs-404 difference.
6. Remove `storage_key` from `FileResponse` if a frontend search shows it is unused (it is declared in `frontend/features/files/types.ts`).
7. Token lifetime: unchanged (7 days). Revisit once you decide on a refresh or revocation approach.

**Tests:** `A@x.com` and `a@x.com` cannot both register; another user's project id returns 404 on every route; concurrent duplicate register returns 409. **Effort:** M.

---

## F20. Maintainability cleanup

**Changes**
1. Move `reprocess_all.py` and `add_titles.py` into `backend/src/scripts/`. Give both the same safety as `seed_demo.py`: print the target database and bucket and do nothing without `--apply`. `reprocess_all` additionally refuses to run when `ENVIRONMENT == "production"`.
2. `chat_service.py`: replace the root-logger lines with `logging.getLogger(__name__)`; configure the root level once in `main.py`.
3. Replace remaining `HTTPException` uses in `user_routes.py` with `AppError` subclasses (add `ConflictError`, 409).
4. `user_model.py`: `projects: Mapped[list["Project"]]`.
5. `frontend/features/files/components/CitationDetail.tsx` and `MessageCard.tsx`: use `key={citation.id}` (add `id: number` to the `Citation` type) and show `title ?? fileName` as the label.
6. Fix the 3 ESLint errors (`ThemeToggle.tsx`, `use-mobile.ts`; use `useSyncExternalStore` or a lazy `useState` initialiser) and the 6 warnings. Make `eslint` blocking in CI.
7. Add a root `CLAUDE.md` (commands, architecture, test and migration instructions, the shared-demo caveat).
8. Developer note, not a code change: use a scoped IAM user or SSO profile for local development instead of static keys in `backend/.env`.

**Effort:** S–M.

---

## 3. Verification checklist (end to end)

1. `cd backend && pytest` passes; `ruff check` is clean.
2. `cd frontend && npx tsc --noEmit && npx eslint . && npm run build` passes.
3. Manual, with the demo account: upload, rename and delete all return the read-only message; chat answers; reload loses the demo visitor's own messages but keeps the seeded history.
4. Manual, with a normal account: upload a cp1252 CSV, a corrupt PDF and an oversize file, and confirm each ends `processed` or `error` within a minute with no endless spinner; send a message that fails and confirm history stays on screen.
5. Fire 25 login requests from one IP and confirm 429 on request 21; confirm a second IP is unaffected.
6. `GET /api/projects` returns only `id` and `name`, and the dashboard makes no `revalidatePath` calls while polling.
7. `alembic upgrade head` on a copy of production data completes; `EXPLAIN` shows index use on the retrieval queries.
8. `npm audit --omit=dev` reports no high or critical findings after the upgrade.

## 4. Not covered by this spec

SQS, Lambda, S3 lifecycle, IAM and budget settings; a stuck-file reconciler; HNSW vector indexes; retrieval-quality changes (rerank score threshold, citing only the chunks used); token revocation; broad frontend tests.
