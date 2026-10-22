import logging
import re
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from src import analytics
from src.features.chat.message_model import Citation, Message, MessageOwner
from src.features.files.embedding_service import (
    NO_CONTEXT_RESPONSE,
    generate_embedding,
    get_response,
    rerank_chunks,
    rewrite_query,
    usage_totals,
)
from src.features.files.file_model import Chunk, File, Project
from src.settings import settings

logger = logging.getLogger(__name__)


def get_messages_this_month(db: Session, user_id: int):
    stmt = (
        select(func.count(Message.id))
        .join(Project, Message.project_id == Project.id)
        .where(
            Project.user_id == user_id,
            Message.owner == MessageOwner.user,
            Message.created_at >= func.date_trunc("month", func.now()),
        )
    )

    return db.execute(stmt).scalar_one()


def get_messages(
    db: Session,
    project_id: int,
    before_id: int | None = None,
    limit: int | None = 30,
):
    limit = max(1, min(limit if limit is not None else 30, 30))
    stmt = (
        select(Message)
        .options(selectinload(Message.chunks).options(selectinload(Chunk.file)))
        .where(Message.project_id == project_id)
        .order_by(Message.id.desc())
        .limit(limit + 1)
    )

    if before_id is not None:
        stmt = stmt.where(Message.id < before_id)

    messages = db.execute(stmt).scalars().all()

    has_more = len(messages) > limit

    messages = messages[:limit]

    return {
        "messages": list(reversed(messages)),
        "has_more": has_more,
        "next_cursor": messages[-1].id if has_more and messages else None,
    }


def get_recent_conversation(
    db: Session,
    project_id: int,
    limit: int = 10,
) -> str:
    stmt = (
        select(Message)
        .where(Message.project_id == project_id)
        .order_by(Message.id.desc())
        .limit(limit)
    )

    messages = db.scalars(stmt).all()

    messages = list(messages)

    messages.reverse()

    return "\n".join(
        f"{message.owner.value}: {message.content}" for message in messages
    )


def answer_question(
    db: Session,
    user_id: int,
    project_id: int,
    content: str,
    is_demo: bool = False,
    track: bool = True,
    use_history: bool = True,
) -> tuple[str, list[Chunk]]:
    """Run the RAG pipeline and return the answer with its citations. Nothing is saved."""
    started_at = time.monotonic()
    stage = "history"
    usage = {"input_tokens": 0, "output_tokens": 0}
    usage_token = usage_totals.set(usage)
    retrieval_counts: dict[str, int] = {}

    try:
        conversation = get_recent_conversation(db, project_id) if use_history else ""
        if track and use_history and not conversation:
            analytics.capture("conversation_created", user_id, is_demo)

        stage = "rewrite"
        # With no earlier turns there is nothing to resolve, so skip the extra LLM call.
        search_query = rewrite_query(content, conversation) if conversation else content
        stage = "retrieval"
        chunks = get_relevant_chunks(
            db, project_id, search_query, stats=retrieval_counts
        )
        stage = "generation"
        if not chunks:
            response = (
                "Sorry, I could not answer your question with the context provided."
            )
            citations = []
        else:
            response = get_ai_response(content, chunks)
            response = response or NO_CONTEXT_RESPONSE
            citations = (
                [] if NO_CONTEXT_RESPONSE.lower() in response.lower() else chunks
            )
    except Exception as err:
        if track:
            analytics.capture(
                "chat_response_failed",
                user_id,
                is_demo,
                stage=stage,
                error_type=type(err).__name__,
            )
        raise
    finally:
        usage_totals.reset(usage_token)

    if track:
        analytics.capture(
            "chat_response_received",
            user_id,
            is_demo,
            latency_ms=round((time.monotonic() - started_at) * 1000),
            outcome="answered" if citations else "no_context",
            citation_count=len(citations),
            retrieved_semantic=retrieval_counts.get("semantic", 0),
            retrieved_keyword=retrieval_counts.get("keyword", 0),
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        )
    return response, citations


def send_user_message(
    db: Session,
    user_id: int,
    project_id: int,
    content: str,
    is_demo: bool = False,
    track: bool = True,
):
    """Answer a question, then save the question and answer together.

    Saving only after the answer exists means a failed Bedrock call leaves no orphaned
    question behind and does not use up the user's monthly allowance.
    """
    response, citations = answer_question(
        db, user_id, project_id, content, is_demo=is_demo, track=track
    )
    return create_message_pair(db, project_id, content, response, citations)


def create_message_pair(
    db: Session,
    project_id: int,
    question: str,
    answer: str,
    chunks: list[Chunk] | None = None,
) -> Message:
    try:
        user_message = Message(
            content=question, owner=MessageOwner.user, project_id=project_id
        )
        db.add(user_message)
        db.flush()  # the question gets the lower id

        ai_message = Message(
            content=answer, owner=MessageOwner.assistant, project_id=project_id
        )
        if chunks:
            ai_message.chunks = chunks
        db.add(ai_message)
        db.commit()
        # Load citations and their files in two queries instead of one per citation.
        return db.scalars(
            select(Message)
            .options(selectinload(Message.chunks).selectinload(Chunk.file))
            .where(Message.id == ai_message.id)
        ).one()
    except Exception:
        db.rollback()
        raise


def get_relevant_chunks(
    db: Session,
    project_id: int,
    message: str,
    candidate_limit: int = settings.RAG_TOP_K,
    limit: int = settings.RAG_RERANK_K,
    stats: dict[str, int] | None = None,
):

    semantic_chunks = get_relevant_chunks_by_semantics(
        db, project_id, message, candidate_limit
    )
    keyword_chunks = get_relevant_chunks_by_keywords(
        db, project_id, message, candidate_limit
    )

    if stats is not None:
        stats["semantic"] = len(semantic_chunks)
        stats["keyword"] = len(keyword_chunks)

    k = 60
    scores: dict[int, float] = {}
    chunks: dict[int, Chunk] = {}

    for rank, chunk in enumerate(semantic_chunks, start=1):
        scores[chunk.id] = scores.get(chunk.id, 0) + 1 / (k + rank)
        chunks[chunk.id] = chunk

    for rank, chunk in enumerate(keyword_chunks, start=1):
        scores[chunk.id] = scores.get(chunk.id, 0) + 1 / (k + rank)
        chunks[chunk.id] = chunk

    ranked_chunk_ids = sorted(
        scores, key=lambda chunk_id: scores[chunk_id], reverse=True
    )

    candidates = [chunks[chunk_id] for chunk_id in ranked_chunk_ids[:candidate_limit]]

    return rerank_chunks(message, candidates, limit=limit)


def get_relevant_chunks_by_semantics(
    db: Session, project_id: int, message: str, limit: int = settings.RAG_TOP_K
) -> list[Chunk]:
    query_embedding = generate_embedding(message)
    distance = Chunk.embedding.cosine_distance(query_embedding)
    similarity = (1 - distance).label("similarity")

    stmt = (
        select(Chunk)
        .join(File, Chunk.file_id == File.id)
        .where(
            File.project_id == project_id,
            similarity >= settings.RAG_SIMILARITY_THRESHOLD,
        )
        .order_by(distance)
        .limit(limit)
    )
    results = db.execute(stmt).scalars().all()

    return list(results)


def get_relevant_chunks_by_keywords(
    db: Session, project_id: int, message: str, limit: int = settings.RAG_TOP_K
) -> list[Chunk]:
    search_vector = func.to_tsvector("english", Chunk.content)
    terms = re.findall(r"\w+", message.lower())

    if not terms:
        return []

    search_query = func.to_tsquery("english", " | ".join(terms))

    stmt = (
        select(Chunk)
        .join(File, Chunk.file_id == File.id)
        .where(
            File.project_id == project_id,
            search_vector.op("@@")(search_query),
        )
        .order_by(func.ts_rank(search_vector, search_query).desc())
        .limit(limit)
    )
    results = db.execute(stmt).scalars().all()

    return list(results)


def get_ai_response(content: str, chunks: list[Chunk]):
    context = "\n\n".join(
        [f"[Source {i + 1}]\n {chunk.content}" for i, chunk in enumerate(chunks)]
    )

    prompt = f"""
You are a helpful assistant that answers questions using the user's documents.

Answer the user's question directly, naturally, and conversationally, as if speaking to the user.

STRICT RULES:
1. Use ONLY information explicitly supported by the provided context. Do not use general knowledge or invent facts.
2. First determine whether the context contains sufficient information to answer the question.
3. If sufficient information exists, answer the specific question concisely and directly.
4. If the context does not contain sufficient information, respond with exactly:
   {NO_CONTEXT_RESPONSE}
5. Never provide a partial answer, speculation, or suggestions unsupported by the context.
6. Never include the fallback response alongside an answer.
7. Do not assume a question is answerable merely because related keywords appear in the context.
8. Do not describe, summarise, or introduce the context. Use it to answer the question, not as the subject of your response.
9. Avoid phrases such as "The context provides information...", "Based on the provided context...", "According to the documents..." or "These suggestions are directly based on the information given".
10. Do not repeat the question or explain your reasoning.
11. Use a natural tone and everyday language. Avoid unnecessarily formal wording, repetitive introductions, and generic conclusions.
12. Use bullet points only when they make the answer easier to read. Otherwise, prefer short paragraphs.
13. Include relevant details from the context without listing every available detail when a shorter answer is sufficient.

User question:
{content}

Context:
{context}

Answer:
"""

    response = get_response(prompt)

    if not response:
        return NO_CONTEXT_RESPONSE

    response = response.strip()

    if NO_CONTEXT_RESPONSE.casefold() in response.casefold():
        return NO_CONTEXT_RESPONSE

    return response
