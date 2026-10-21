# Public Demo Mode — Implementation Specification

| | |
|---|---|
| **Status** | **Implemented (revision 2), not yet deployed.** See the revision notes below; where they conflict with later sections, the notes win. |
| **Date** | 2026-10-21 |
| **Goal** | A recruiter clicks **Try demo** and lands in a populated FileQuery account with no registration, and can upload documents, ask questions, and use the existing app. |
| **Non-goals** | Per-visitor isolated accounts, new UI beyond a button and a banner, changes to the RAG pipeline, new infrastructure beyond one scheduled job. |

---

## Revision 2 — decisions made after review (supersedes conflicting text below)

| Topic | Decision |
|---|---|
| Docs folder | `backend/example-docs/` (the old private folder was renamed `old-example-docs` and stays untracked). `.gitignore` allows it. |
| Documents | The four portfolio project files (FileQuery, Gains, TaskFlow, TripTrack). No CV, no trip/gift files. |
| Account | One shared demo account, with a banner. |
| Scheduling | **None.** There is no Cloud Run Job / Scheduler and no periodic full reset; the owner runs the script manually. Sections 6.6 and the scheduler steps in section 10 are dropped. |
| Files | **Never deleted** because they are old or recruiter-made. The script only creates a seeded file when it does not exist, and replaces a seeded file that is broken (not processed, no chunks, missing from S3, or content changed). Recruiter uploads are left alone. |
| Messages | If the chat has no messages, the script creates the conversation by asking five questions about the four projects through the existing `chat_service.send_user_message`. `--delete-messages-after DATE` deletes demo messages created after `DATE` (citations cascade); if that leaves the chat empty, the starter chat is regenerated. |
| Project names | If a visitor renames the seeded project, the script recognises it by its files and restores the manifest name. |
| Dropped flags | `--force-rebuild`, `--purge-only`, `--no-starter-chat`. Remaining flags: `--apply` (default is a dry run) and `--delete-messages-after`. |
| Tests | No test suite was added (the repo has none). Behaviour was verified with a throw-away integration script (not committed) against a local Postgres + pgvector with fake S3/Bedrock; see the PR/summary. |

Run it from `backend/`:

```bash
python -m src.scripts.seed_demo                                     # dry run
python -m src.scripts.seed_demo --apply
python -m src.scripts.seed_demo --apply --delete-messages-after 2026-10-21
```

Exit codes: `0` ok, `1` partial failure, `2` refused (for example the demo email belongs to a real user, or `alembic upgrade head` has not been run).

---

## 1. What I found in the codebase

This spec is based on reading the code, not on assumptions. The facts that shape the design:

### Backend (FastAPI, SQLAlchemy 2, Postgres + pgvector)

| Area | Finding | Source |
|---|---|---|
| **Auth** | `POST /api/auth/login` returns a JWT whose `sub` is the user's **email**. `get_current_user` decodes it and loads the user from the DB on every request. There are no roles or claims beyond `sub` and `exp`. Token TTL is 7 days. | `backend/src/features/auth/user_service.py`, `user_routes.py` |
| **User model** | `users(id, username, email unique, password_hash)`. No flags. | `user_model.py` |
| **Ownership** | Every route checks `resource.project.user_id != user.id`. A token for user X cannot read user Y's data. The demo account inherits this for free. | `file_routes.py`, `project_routes.py`, `chat_routes.py` |
| **Upload flow** | (1) `POST /api/files` creates `File` rows (`pending`) with key `filequery/{ENVIRONMENT}/projects/{project_id}/files/{uuid4}` and returns presigned S3 POSTs. (2) Browser posts bytes to S3. (3) `POST /api/files/confirm` `head_object`s each key, sets `status=processing` and overwrites `size` from S3. | `file_service.py`, `file_model.py` |
| **Processing** | After confirm: `ENVIRONMENT == "production"` → `enqueue_files` sends one SQS message per file → Lambda runs `process_file`. Otherwise → `process_files_locally` in a FastAPI background task. `process_file` = download from S3 → extract → chunk → for each chunk call Bedrock for a **title** and a Titan **embedding** → insert `Chunk` rows → set `status=processed`. | `file_routes.py`, `file_processing_service.py`, `src/file_embedding_worker.py` |
| **Gotcha: auto-rename** | `enqueue_files` / `process_files_locally` mark the last file `is_last: true`, which makes `process_file` call `name_project()` and **overwrite the project name** with an LLM-generated one. A seed script reusing these as-is would get non-deterministic project names. | `file_processing_service.py` |
| **Chat / RAG** | `POST /api/projects/{id}/messages`: rewrite query → semantic + keyword search → RRF merge → Bedrock rerank → Nova answer. Citations are rows in `citations(message_id, chunk_id)`. Per-user cap: `MAX_MONTHLY_MESSAGES` (40), counted from `messages` where owner = user this month. | `chat_service.py`, `chat_routes.py` |
| **Cascades** | `projects → files → chunks` and `projects → messages → citations` are all `ON DELETE CASCADE` at the DB level (verified in migrations). Deleting a project deletes everything under it in Postgres; **S3 objects must be deleted separately** (existing `delete_project` does this after commit). | `alembic/versions/*` |
| **Migrations** | Alembic. Current head is `554fd22cf31d`. | `alembic/versions/` |
| **Settings** | `pydantic-settings`; required: AWS_REGION, AWS_BUCKET_NAME, DATABASE_URL, SECRET_KEY, ALGORITHM, SQS_QUEUE_URL, BEDROCK_CHAT_MODEL_ID, REDIS_URI. | `settings.py` |
| **Accepted types** | `txt, md, csv, pdf, doc, docx`. `.txt` → `text/plain`, `.md` → `text/markdown`. (The label map in `file_schema.py` has `.doc`/`.docx` swapped; cosmetic, error text only.) | `file_schema.py` |
| **Docker** | `backend/Dockerfile` copies only `requirements.txt` and `src/`. Scripts in `backend/*.py` (e.g. `reprocess_all.py`) are **not** in the image. The Lambda image also copies only `src/`. | `Dockerfile`, `embedding_worker.Dockerfile` |
| **Tests** | None. No pytest, no `tests/`; only a manual `test_bedrock.py`. | — |

### Frontend (Next.js 16, server actions, httpOnly cookie)

- `features/auth/api/authApi.ts` calls the backend from a server action and stores the JWT in an httpOnly `access_token` cookie (`saveCookie`). All other server actions send it as `Authorization: Bearer`.
- `proxy.ts` only inspects the cookie's `exp`; it redirects `/dashboard` and `/settings` to `/login` when there is no live token, and `/login` + `/register` to `/dashboard` when there is one.
- `app/page.tsx` (landing) has "Get Started" → `/dashboard`. `app/layout.tsx` reads the cookie only to decide which header links to show.
- Uploads go browser → S3 via presigned POST (`features/files/actions.ts`); the dashboard already shows a loading/polling state for files being processed.
- **Important:** the browser never calls the backend directly. Every backend request comes from the Next.js server, so the backend sees the **frontend's** IP, not the visitor's.

### Findings that affect the design (existing issues, not fixed by this spec)

1. **Rate-limit decorators look inert.** In `file_routes.py`, `chat_routes.py`, and `user_routes.py`, `@limiter.limit(...)` sits *above* `@router.post(...)`. slowapi requires it *below*; as written the limiter wraps a function the router never registered. Even if fixed, per-IP limits would key on the Next.js server's IP (see above). **The demo therefore does not rely on slowapi.** Its protection is DB-backed caps (§5.4). I recommend verifying and fixing the decorator order separately.
2. **The demo user is a single shared account** (as requested). Per-user caps (`MAX_MONTHLY_MESSAGES`) become a pool shared by every recruiter, so the demo needs its own limits and a periodic reset (§5.4, §6.6).
3. **`EmailStr` rejects reserved TLDs.** I tested it: `demo@filequery.invalid` and `demo@filequery.test` are *rejected*; `demo@example.com` is accepted. `GET /api/auth/me` has `response_model=User` with `EmailStr`, so a demo user with a reserved-TLD email would make `/me` return 500. The demo email must be a syntactically deliverable one; default `demo@example.com`.
4. **`example-docs` is gitignored and exists twice.** `.gitignore` contains the bare pattern `example-docs`, which matches at any depth. See §4 — this is the one item that needs your decision.

---

## 2. Architecture overview

```
Recruiter ── "Try demo" ──► Next.js server action startDemo()
                               │  POST /api/auth/demo   (no body)
                               ▼
                         FastAPI: find user WHERE is_demo = true
                               │  mint JWT (sub=demo email, exp=2h, demo=true)
                               ▼
                         httpOnly access_token cookie  ──►  /dashboard
                                                         (existing pages, unchanged)

Everything after that is the normal app, as the demo user:
  upload → presigned POST → S3 → confirm → SQS/Lambda (prod) → chunks   (unchanged)
  chat   → RAG pipeline                                                  (unchanged)

Seed / reset (separate process, not a web route):
  python -m src.scripts.seed_demo --apply
     reads backend/example-docs/manifest.json
     reuses file_service.create_files / confirm_uploads and enqueue_files / process_files_locally
     runs as a Cloud Run Job on a schedule (default every 6h)
```

**Design principles**

1. **One new endpoint** (`POST /api/auth/demo`) and **one new column** (`users.is_demo`). Everything else reuses existing routes, components, services and the existing pipeline.
2. **Authentication is the existing JWT-in-cookie**, minted for one specific DB row. No new session type.
3. **Authorization is unchanged**: the demo user is an ordinary user who owns only demo projects, so existing ownership checks confine it.
4. **`is_demo` is the only thing that identifies demo data.** No hardcoded IDs anywhere; the demo user's ID is resolved at runtime.
5. **The seed script goes through the real pipeline** (DB rows → S3 → queue → Lambda → chunks). It does not write chunks or embeddings itself.

---

## 3. Data model change

**Column**: `users.is_demo BOOLEAN NOT NULL DEFAULT false`.

**Constraint**: a partial unique index so the database itself guarantees at most one demo user:

```sql
CREATE UNIQUE INDEX uq_users_single_demo ON users (is_demo) WHERE is_demo;
```

Declared on the model via `__table_args__ = (Index("uq_users_single_demo", "is_demo", unique=True, postgresql_where=text("is_demo")),)` so Alembic autogenerate stays in sync.

**Migration** (hand-reviewed, not autogenerated blindly): new revision with `down_revision = "554fd22cf31d"`. `upgrade` adds the column with `server_default=sa.false()` (existing rows become `false`) and creates the index; `downgrade` drops both. Safe to run on a live DB: additive, no table rewrite concerns at this scale.

**No other schema changes.** In particular no hash column on `files`: content-change detection uses S3 object metadata (§6.4).

**Not exposed via the API**: `is_demo` is not added to `UserCreate`, so `/register` cannot set it; the `User` response schema is unchanged.

---

## 4. Example documents (`example-docs`) — decision needed

There are **two** folders called `example-docs`, both currently gitignored (the pattern `example-docs` in the root `.gitignore` matches both):

| Folder | Contents | Fit for a public recruiter demo |
|---|---|---|
| `backend/example-docs/` | `FileQuery_project_details.md`, `Gains_project_details.md`, `TaskFlow_project_details.md`, `TripTrack_project_details.md` (Markdown, 2.5–6 KB each) | **Good.** Portfolio descriptions; exercises the Markdown header-splitter; recruiters can ask "which project uses FastAPI?" |
| `example-docs/` (repo root) | `Akhere-Ihoeghinlan-cv.txt` (your CV incl. email), and six `.txt` files of private family trip planning / gift ideas for a relative's birthday (`trip-plans`, `cruise-plans`, `orlando-plan`, `excursion-plans`, `checklist`, `next-presents`) | **CV: your call. Trip/gift files: I recommend not publishing.** Anyone who opens the demo can view the raw files through the app's presigned URLs, and the repo is public. |

**Recommendation (used throughout this spec):**

- **Canonical folder: `backend/example-docs/`.** It is inside the Docker build context (`backend/`), next to `src/`, so it ships in the image the scheduled job runs from. The root folder is outside the build context.
- Change the root `.gitignore` entry from `example-docs` to `/example-docs` so only the private root scratch folder stays ignored and `backend/example-docs/` is committed.
- **Seed only files listed in an explicit allow-list manifest**, `backend/example-docs/manifest.json`, never "everything in the folder". This prevents a stray `.DS_Store` or private file from being published.

```jsonc
{
  "projects": [
    {
      "name": "Akhere's Portfolio Projects",
      "files": [
        "FileQuery_project_details.md",
        "Gains_project_details.md",
        "TaskFlow_project_details.md",
        "TripTrack_project_details.md"
        // "Akhere-Ihoeghinlan-cv.txt"  ← only if you approve publishing it (copy into backend/example-docs/)
      ]
    }
  ]
}
```

One project (4 files, 5 with the CV) is the v1 default. This leaves 2 of the 3 allowed project slots (`MAX_PROJECTS_PER_USER = 3`) for recruiter-created projects. A second seeded project is possible but would leave only one slot.

MIME type is derived from the extension in the seed service (`.md → text/markdown`, `.txt → text/plain`, plus the other accepted types), and any extension not in `accepted_mime_types` aborts the seed.

---

## 5. Demo authentication, ownership and abuse protection

### 5.1 Entering the demo — `POST /api/auth/demo`

- Added to `user_routes.py` next to `/login`. No request body.
- Returns the same `Token` schema as `/login`, so the frontend reuses the existing `authenticate()` path in `authApi.ts`.
- Behaviour:
  1. If `settings.DEMO_MODE_ENABLED` is false → `404` (the endpoint does not advertise itself).
  2. Look up `User WHERE is_demo = true`. If missing → `503` "Demo is not available right now" (seed has not run).
  3. Mint a JWT with `sub = user.email`, `exp = now + DEMO_TOKEN_EXPIRE_MINUTES` (default **120**), and an extra claim `demo: true`.
- The endpoint takes **no user input**. It cannot be used to impersonate anyone: it only ever mints a token for the single `is_demo` row.

### 5.2 Why this is safe

| Threat | Mitigation |
|---|---|
| Demo token used to reach real users' data | Tokens identify the demo user by `sub`. All routes already require `resource.user_id == user.id`. The demo user owns only demo data. No new access path is added. |
| Someone logs in to the demo account with a password | The demo user's `password_hash` is a bcrypt hash of a random 48-byte secret that is never stored or printed. Additionally `/login` and `/token` explicitly return the generic `401` when the matched user `is_demo`. |
| Someone registers the demo email first | `users.email` is unique. If the seed finds a user with the demo email that is **not** `is_demo`, it **aborts without touching it** (§6.2). |
| Someone sets `is_demo` through the API | `is_demo` is not in any request schema. Only the seed script sets it. |
| The `demo: true` JWT claim is forged/trusted | The claim is **UI-only** (drives the banner). The server never uses it for authorization; `get_current_user` always loads the row and reads `user.is_demo` from the DB. A forged claim has no server effect. |
| Demo needs to be shut off immediately | `get_current_user` gains one check: if `user.is_demo and not settings.DEMO_MODE_ENABLED` → `InvalidCredentialsError`. Flipping `DEMO_MODE_ENABLED=false` and redeploying invalidates all outstanding demo tokens at once. |
| Long-lived stolen token | Demo tokens live 2 h (not 7 days); the cookie `maxAge` is set to match. |
| Reserved email breaks `/me` | Default `DEMO_USER_EMAIL = demo@example.com` (verified to pass `EmailStr`). |

### 5.3 Ownership guarantee for the seed/reset script

Destructive operations are scoped by a single resolved value, never by name or ID literal:

1. `demo_user = SELECT * FROM users WHERE is_demo = true` (expect exactly 0 or 1 row; the partial index guarantees ≤ 1).
2. **Assert `demo_user.is_demo is True` immediately before every delete batch.**
3. All project/file/message queries are `WHERE projects.user_id = demo_user.id`.
4. S3 keys to delete come **only from `files.storage_key` of rows that belong to demo-owned projects**, and each key is additionally asserted to start with `filequery/{ENVIRONMENT}/projects/`. The script never lists or deletes by bucket prefix.
5. It never touches any other `users` row, including for "cleanup".

### 5.4 Abuse and cost caps (DB-backed, because slowapi is unreliable here)

All apply **only when `user.is_demo`** and live in one small module, `features/demo/demo_service.py`, called from two existing routes.

| Cap | Setting (default) | Enforced in |
|---|---|---|
| Messages per window | `DEMO_MAX_MESSAGES` = 60 | `chat_routes.send_chat_messsage`: `limit = DEMO_MAX_MESSAGES if user.is_demo else MAX_MONTHLY_MESSAGES`. Uses the existing `get_messages_this_month` count; because reset deletes messages, the pool refills each reset. |
| Max size per file | `DEMO_MAX_FILE_SIZE` = 5 MB | `file_routes.upload_files` → `demo_service.enforce_upload_limits` |
| Total demo storage | `DEMO_MAX_STORAGE` = 50 MB | same (uses existing `file_service.get_used_storage`) |
| Projects | existing `MAX_PROJECTS_PER_USER` (3) | already enforced |

Errors use the existing `TooManyRequestsError`/`BadRequestError`, with a demo-specific message such as "Demo limit reached. The demo resets every 6 hours." The frontend already displays server error messages.

Also: set an **AWS Budget alert** on Bedrock spend (deployment checklist, §10). Bedrock calls per upload (~2 per chunk) and per message (~4) are the only meaningful cost.

### 5.5 Shared-account trade-off (explicit)

All recruiters share one account. They can see, delete, or rename each other's uploads and chats until the next reset. Mitigations in v1: the banner tells visitors the demo is shared and resets periodically and not to upload private files, and the reset restores the baseline. Per-visitor isolated accounts (cloning the seeded data into a throw-away user per click) would remove this, but cost one full embedding run per visitor or a data-copy routine; it is out of scope and can be added later on top of `is_demo`.

---

## 6. Seed / reset script

### 6.1 Entry point

`backend/src/scripts/seed_demo.py` (thin CLI) → `backend/src/features/demo/demo_seed_service.py` (logic). It lives under `src/` so it is in the Docker image (unlike the existing root-level `backend/*.py` scripts) and can run as a Cloud Run Job. Invoked as `python -m src.scripts.seed_demo`.

| Flag | Behaviour |
|---|---|
| *(default)* | **Dry run.** Prints the target (DB host, bucket, `ENVIRONMENT`) and the plan (users/projects/files to create/keep/purge, S3 keys to delete). Changes nothing. |
| `--apply` | Executes the plan. |
| `--force-rebuild` | Treat every seeded file as unhealthy: purge and re-ingest. |
| `--purge-only` | Delete all demo-owned projects/files/messages and S3 objects, keep the user. Used for teardown/rollback. |
| `--no-starter-chat` | Skip the starter questions (§6.5). |

It refuses to run if `DEMO_USER_EMAIL` resolves to a non-demo user, and prints the DB host and bucket before `--apply`, so a wrong `.env` is visible.

### 6.2 Algorithm (idempotent "converge to manifest")

```
0. Acquire pg_try_advisory_lock(<constant>). If already held → exit 0 ("another run in progress").
   Load + validate manifest: every listed file exists, extension accepted, size < DEMO_MAX_FILE_SIZE.

1. Demo user (create-or-find)
   a. SELECT user WHERE is_demo = true  → use it.
   b. else SELECT user WHERE email = DEMO_USER_EMAIL:
        exists and NOT is_demo → ABORT (never adopt/modify a real user).
   c. else INSERT user(username="Demo User", email=DEMO_USER_EMAIL,
        password_hash=hash(random secret, discarded), is_demo=true).

2. Purge what shouldn't be there (demo-owned only, §5.3)
   - projects whose name is not in the manifest, and duplicate-named projects (keep lowest id)
   - files in manifest projects whose name is not in the manifest (i.e. recruiter uploads)
   - files that are unhealthy (see 6.4) or duplicated
   - ALL messages in demo projects (chat reset; citations cascade)
   Purge order for every project/file: collect storage_keys → delete S3 objects → delete DB rows.
   (S3 first: a crash leaves rows pointing at missing objects, which the next run purges.
    delete_object on a missing key is a no-op, so reruns converge.)

3. Ensure projects exist: for each manifest project, find by exact name among demo-owned
   projects, else create (user_id = demo_user.id). Reset names to the manifest value
   (undoes recruiter renames).

4. Ingest missing files, per project, ONE batch per project:
   a. file_service.create_files(db, demo_user.id, project_id, [FileCreate(name, mime_type, size)])
        → File rows status=pending, key = filequery/{ENV}/projects/{project_id}/files/{uuid}
   b. s3.put_object(Bucket, Key=file.storage_key, Body=bytes, ContentType=mime_type,
        Metadata={"sha256": <hex>, "demo-seed": "1"})        # server-side upload; no presigned POST needed
   c. files = file_service.confirm_uploads(db, demo_user.id, [ConfirmUploadRequest(id=f.id) ...])
        → head_object, size := S3 ContentLength, status=processing
   d. process, WITHOUT letting the last file rename the project:
        ENVIRONMENT == "production": enqueue_files(files, rename_project=False)  → SQS → Lambda
        else:                        process_files_locally(files, rename_project=False)  (synchronous)
   If any step fails for a file: mark it error via the existing error path / delete the row;
   continue with the others; record the failure.

5. Wait for processing: poll the DB until every seeded file is processed or error,
   up to DEMO_SEED_TIMEOUT (default 10 min, 5 s interval).

6. Verify (§6.4 healthy check) for every manifest file. Any failure → exit code 1 with a summary.

7. Starter chat (optional, §6.5), then print summary and release the lock.
```

Re-running changes nothing when everything is healthy (steps 2–4 find nothing to do; the only DB writes are deleting recruiter messages and un-renaming projects). A re-run after a half-finished run repairs only what is missing.

### 6.3 Why the pipeline's DB rows and queue messages are created by reusing the services

Uploading bytes to S3 alone is **not enough** and the script does not rely on it. The pipeline needs:
a `files` row (status/size/mime/key), a `confirm` step (status `processing`, true size), and a queue message (SQS in production) so the Lambda produces chunks. Steps 4a–4d create exactly those by calling the same service functions the routes call, so the seeded state is indistinguishable from a real upload. The only new code in existing files is one optional parameter (§8) to stop the auto-rename.

### 6.4 "Healthy" definition (what makes a seeded file reusable)

A manifest file is kept only if **all** hold, otherwise it is purged and re-ingested:

1. `files.status == processed` and `error is NULL`
2. `COUNT(chunks) > 0` and all chunks have a non-null embedding
3. `head_object(storage_key)` succeeds, `ContentLength == files.size`
4. S3 metadata `sha256` equals the current SHA-256 of the file in the repo (so editing a doc in `example-docs/` triggers re-ingest, with no schema change)

### 6.5 Starter conversation (small, optional, on by default)

After step 6, send two real questions through `chat_service.send_user_message` (e.g. "Which of these projects use FastAPI?" and "What does FileQuery do?"), so a recruiter immediately sees a cited answer. These go through the real RAG path; no answer text is hard-coded. Failure here is logged as a warning and does **not** fail the run (Bedrock hiccups shouldn't leave the demo empty). The questions are constants in the manifest (`"starterQuestions"`).

### 6.6 Scheduling and fixture reset

- Reset is the same command run on a schedule. Default **every 6 hours** (also the interval quoted in the banner and limit errors). Fast path when healthy, so cost is a few DB queries and 4–5 `head_object` calls.
- First run (or after `--force-rebuild`) costs about: 4–5 docs × ~3–5 chunks × 2 Bedrock calls ≈ 30–50 calls.

---

## 7. Failure handling

| Failure | Behaviour |
|---|---|
| Manifest lists a missing file / unaccepted extension / oversize | Abort **before any change**; exit 2. |
| Demo email belongs to a non-demo user | Abort; exit 2; nothing modified. |
| Migration not applied (`is_demo` column missing) | Detect and exit with "run alembic upgrade head". |
| Another seed run in progress | Advisory lock not acquired → exit 0, no-op. |
| S3 `put_object` fails | That file's row is removed (or marked `error`) and reported; other files continue; exit 1. Next run retries it. |
| S3 `delete_object` fails during purge | Logged with key; continue; DB rows still removed only after their S3 delete succeeds (otherwise the row is kept so the next run retries it). |
| `confirm_uploads` returns fewer files than requested (`head_object` miss) | Reported as failed; next run re-ingests. |
| SQS `send_message` fails | Row stays `processing`; reported; next run treats a `processing` row older than `DEMO_SEED_TIMEOUT` as unhealthy and re-ingests. |
| Lambda/Bedrock fails → file `error` | Seen at step 5/6; exit 1 with file name + `files.error`; next run purges and retries. |
| Processing never finishes | Timeout → exit 1; row left as is and re-ingested next run. |
| Seed crashes mid-run | Safe to rerun: every step is derived from current DB/S3 state. |
| Demo endpoint called before first seed | `503` "Demo is not available right now". |
| Demo user hits a cap | Existing error toast with demo-specific text. |
| Bedrock outage during a recruiter's chat | Unchanged existing behaviour (generic 500 → frontend error message). |

Exit codes: `0` ok/no-op, `1` partial failure (some files unhealthy), `2` refused/aborted before changes. Cloud Run Job failure alerting uses the non-zero exit.

---

## 8. Exact files to change

### Backend

| File | Change |
|---|---|
| `backend/src/features/auth/user_model.py` | Add `is_demo: Mapped[bool]` (`default=False`, `server_default=false()`, not null) and the partial unique index. |
| `backend/alembic/versions/<new>_add_is_demo_to_users.py` | **New.** Column + index; `down_revision = "554fd22cf31d"`. |
| `backend/src/settings.py` | Add `DEMO_MODE_ENABLED: bool = False`, `DEMO_USER_EMAIL: str = "demo@example.com"`, `DEMO_TOKEN_EXPIRE_MINUTES: int = 120`, `DEMO_MAX_MESSAGES: int = 60`, `DEMO_MAX_FILE_SIZE: int = 5 MB`, `DEMO_MAX_STORAGE: int = 50 MB`, `DEMO_SEED_TIMEOUT_SECONDS: int = 600`. All have defaults, so existing deployments keep working. |
| `backend/src/features/auth/user_service.py` | Add `get_demo_user(db)`, `get_demo_access_token(user)` (uses existing `create_access_token(data, expires_delta)` with `{"sub": email, "demo": True}`); add the kill-switch check to `get_current_user`. |
| `backend/src/features/auth/user_routes.py` | Add `POST /api/auth/demo`; make `/login` and `/token` reject `is_demo` users with the existing generic 401. |
| `backend/src/features/demo/demo_service.py` | **New.** `enforce_upload_limits(db, user, files_in)` and `message_limit_for(user)`. |
| `backend/src/features/files/file_routes.py` | In `upload_files`: call `demo_service.enforce_upload_limits` when `user.is_demo`. |
| `backend/src/features/chat/chat_routes.py` | Use `demo_service.message_limit_for(user)` in place of `settings.MAX_MONTHLY_MESSAGES`. |
| `backend/src/features/files/file_processing_service.py` | Add keyword param `rename_project: bool = True` to `enqueue_files` and `process_files_locally`; when `False`, send/pass `is_last: False`. Default preserves current behaviour exactly. |
| `backend/src/features/demo/demo_seed_service.py` | **New.** Algorithm in §6. |
| `backend/src/scripts/seed_demo.py` | **New.** CLI wrapper (`argparse`, flags in §6.1). |
| `backend/example-docs/manifest.json` | **New** allow-list (§4). The four existing `.md` files become tracked. |
| `backend/Dockerfile` | Add `COPY example-docs ./example-docs`. |
| `backend/requirements-dev.txt` | **New** (pytest, moto) — keeps test deps out of the production image. |
| `backend/tests/**` | **New**, see §9. |
| `.gitignore` (root) | `example-docs` → `/example-docs`. |
| `README.md` | Short "Public demo" section: env vars and the seed command. |

### Frontend

| File | Change |
|---|---|
| `frontend/features/auth/api/authApi.ts` | Add `startDemo()` server action. Reuse `authenticate()` with path `/api/auth/demo` and no body; make `saveCookie(token, maxAge)` take a `maxAge` (demo: 2 h, others: unchanged 7 days). |
| `frontend/features/auth/components/DemoButton.tsx` | **New** client component: button → `startDemo()` → `router.push("/dashboard")`; shows the returned error message on failure (e.g. "Demo is not available right now"), pending state "Starting demo…". |
| `frontend/app/page.tsx` | Add `<DemoButton />` beside "Get Started" and in the closing CTA card. Hidden when an `access_token` cookie already exists (shows nothing extra) so a real user's session isn't replaced by accident. |
| `frontend/features/auth/components/LoginForm.tsx` | Add a small "Just looking? Try the demo" link/button under the form. |
| `frontend/components/common/DemoBanner.tsx` | **New** server component: reads the cookie, `jwtDecode` (already a dependency), and if `demo === true` shows "You're in the shared demo. Data resets about every 6 hours — don't upload private files." plus a Register link. UI hint only. |
| `frontend/app/layout.tsx` | Render `<DemoBanner />` above `{children}`. |
| `frontend/proxy.ts` | **No change** (the demo cookie behaves like any session; the 2 h `exp` is already honoured). |

### Explicitly *not* changed

`chat_service.py`, `embedding_service.py`, `file_service.py`, `file_extraction_service.py`, `project_*`, the Lambda handler `file_embedding_worker.py`, the dashboard and chat components, and `main.py` (no new router).

---

## 9. Tests

The repo has no test setup, so v1 adds a small one:

- `backend/requirements-dev.txt`: `pytest`, `moto[s3,sqs]`.
- `backend/tests/conftest.py`: sets dummy required env vars **before** importing `src.settings`; uses a throw-away **Postgres with pgvector** (`TEST_DATABASE_URL`, e.g. the pgvector docker image — SQLite can't run `Vector`/`to_tsvector`), runs `alembic upgrade head`, wraps each test in a transaction; moto for S3/SQS; monkeypatches `generate_embedding`, `get_response`, and `rerank_chunks` to deterministic fakes (no Bedrock in tests).

| Test | Asserts |
|---|---|
| `test_demo_auth.py` | `POST /api/auth/demo`: 404 when disabled; 503 when no demo user; 200 returns token whose `sub` is demo email and `exp` ≈ 2 h; token reaches `/api/projects` and sees only demo projects; **cannot** read another user's project/file/messages (403). |
| | Password login for the demo email → 401; `/token` → 401; register with demo email → 409. |
| | Kill-switch: with a valid demo token, set `DEMO_MODE_ENABLED=false` → 401. |
| | Forged JWT claim `demo: true` for a non-demo user grants nothing and changes no limits. |
| `test_demo_limits.py` | Demo user: oversize file → 400; storage cap → error; message cap → 429; the same requests for a normal user are unaffected (regression guard). |
| `test_seed_service.py` | First run creates user (`is_demo`), project(s), files; S3 objects exist at `filequery/{env}/projects/{pid}/files/<uuid>`; File rows `processed` with chunks > 0; project name equals manifest (not renamed by `name_project`). |
| | **Idempotent:** second run makes no S3 puts and no new File rows; row IDs unchanged. |
| | **Reset:** after adding a recruiter upload, a recruiter project, a chat message and renaming the seeded project, a run removes the upload (+ its S3 object), the extra project, the messages, and restores the name — and leaves seeded files untouched. |
| | **Isolation:** with a second, non-demo user owning projects/files/messages/S3 objects, a full reset and `--purge-only` leave every one of those rows and objects byte-identical. |
| | Refusal: demo email owned by a non-demo user → exit 2, no changes. Two concurrent runs → one no-ops. |
| | Self-heal: delete a seeded S3 object / set a file to `error` / change a doc's bytes → next run repairs exactly that file. |
| | Failure paths: S3 put failure and processing error give exit 1, leave other files intact; next run succeeds. |
| | Dry-run (default) changes nothing. |
| `test_processing_flag.py` | `enqueue_files(files, rename_project=False)` sends `is_last: false` on all messages; default still marks the last. |

**Frontend**: there is no test runner. v1 verification = `npm run lint`, `npm run build`, and the manual checklist below. (Adding Playwright is deliberately out of scope.)

**Manual end-to-end checklist (run against staging before production):**
1. Run migration; run `seed_demo` (dry-run → `--apply`); confirm files reach `processed`.
2. Click **Try demo** on `/` while logged out → lands on `/dashboard` with the seeded project, banner visible.
3. Ask a question → cited answer; open a citation / view a file.
4. Upload a small `.txt` → goes `processing` → `processed`; ask about it.
5. Try a >5 MB file → clear error.
6. Log out, register a real account → sees none of the demo data.
7. Re-run `seed_demo --apply` → recruiter upload and chat gone, seeded files unchanged (same IDs).
8. Set `DEMO_MODE_ENABLED=false` → existing demo session is rejected; button shows the friendly error.

---

## 10. Deployment requirements

**Config (backend service *and* the seed job — both need the same `ENVIRONMENT`, DB, bucket, queue):**
`DEMO_MODE_ENABLED=true`, `DEMO_USER_EMAIL` (optional), plus the cap settings if you want non-defaults. The seed job additionally needs the full existing backend env (`DATABASE_URL`, `AWS_*`, `AWS_BUCKET_NAME`, `SQS_QUEUE_URL`, `BEDROCK_CHAT_MODEL_ID`, `SECRET_KEY`, `ALGORITHM`, `REDIS_URI`) because `Settings()` requires them at import. `ENVIRONMENT` must match the service (it determines the S3 key prefix **and** whether processing is local or via SQS).

**IAM**: the seed job's AWS identity needs `s3:PutObject`, `GetObject`, `DeleteObject` on `filequery/<env>/projects/*`, `sqs:SendMessage` on the processing queue, and Bedrock invoke (for the starter chat). The backend service already has most of this (it signs presigned POSTs and calls delete/head). No new bucket, queue, or Lambda.

**Rollout order**
1. Merge; CI builds the images (the existing workflow already rebuilds the Lambda image on `backend/**` changes; behaviour of the Lambda is unchanged because `is_last` is read from the message).
2. `alembic upgrade head` against production (adds `is_demo`; harmless to the running app).
3. Deploy the backend service (demo disabled by default → no behaviour change).
4. Create a **Cloud Run Job** from the backend image: `python -m src.scripts.seed_demo --apply`; run once manually; check the summary and that all files are `processed`.
5. Create a **Cloud Scheduler** trigger for the job (every 6 h) and a job-failure alert.
6. Set `DEMO_MODE_ENABLED=true` on the backend; deploy the frontend.
7. Add an **AWS Budget alert** for Bedrock.

**Rollback / teardown**: set `DEMO_MODE_ENABLED=false` (kills all demo sessions immediately and 404s the endpoint); optionally pause the scheduler and run `seed_demo --purge-only --apply` to remove demo data. The migration is additive and can stay.

**Local development**: with `ENVIRONMENT=development`, `seed_demo --apply` processes files synchronously in-process (needs AWS creds for S3 + Bedrock, as the app already does).

---

## 11. Decisions I need from you before implementing

1. **Which documents are published?** Recommended: the four `backend/example-docs/*.md` project files only. Do you want the CV (`Akhere-Ihoeghinlan-cv.txt`) included? I recommend **not** including the private trip/gift `.txt` files in a public demo + public repo.
2. **Canonical folder:** OK to use `backend/example-docs/` and change `.gitignore` to `/example-docs`? (Alternative: root `example-docs/`, which needs the Docker build context or a `COPY` from outside `backend/`, i.e. a CI/Dockerfile change.)
3. **Shared single demo account** (as specified) vs per-visitor accounts — OK with shared + banner + periodic reset?
4. **Reset cadence** (6 h) and **message cap** (60 per window) — fine?
5. **Starter conversation** (two real, cited Q&As after each reset) — keep or drop?

Out-of-scope issues spotted (separate tickets, not touched by this work): the `@limiter.limit` decorator order, and the swapped `.doc`/`.docx` labels in `file_schema.py`.
