import logging
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from src.features.chat.message_model import Citation, Message, MessageOwner
from src.features.files.embedding_service import (
    generate_embedding,
    get_response,
    rerank_chunks,
    rewrite_query,
)
from src.features.files.file_model import Chunk, File, Project
from src.settings import settings

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
    limit = max(0, min(limit or 30, 30))
    stmt = (
        select(Message)
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
        "next_cursor": messages[-1].id if has_more else None,
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


def send_user_message(db: Session, user_id: int, project_id: int, content: str):
    conversation = get_recent_conversation(db, project_id)
    create_message(db, project_id, MessageOwner.user, content)

    search_query = rewrite_query(
        content,
        conversation,
    )
    chunks = get_relevant_chunks(db, project_id, search_query)
    if not chunks:
        response = "Sorry, I could not answer your question with the context provided."
        ai_message = create_message(
            db, project_id, MessageOwner.assistant, response, chunks
        )
        return ai_message
    else:
        response = get_ai_response(content, chunks)
        response = response or "Sorry, I could not answer your question."
        ai_message = create_message(
            db, project_id, MessageOwner.assistant, response, chunks
        )
        return ai_message


def create_message(
    db: Session,
    project_id: int,
    owner: MessageOwner,
    content: str,
    chunks: None | list[Chunk] = None,
):
    try:
        message = Message(
            content=content,
            owner=owner,
            project_id=project_id,
        )
        db.add(message)
        if chunks:
            message.chunks = chunks

        db.add(message)
        db.commit()
        return message
    except:
        db.rollback()
        raise


def get_relevant_chunks(
    db: Session,
    project_id: int,
    message: str,
    candidate_limit: int = settings.RAG_TOP_K,
    limit: int = settings.RAG_RERANK_K,
):

    semantic_chunks = get_relevant_chunks_by_semantics(
        db, project_id, message, candidate_limit
    )
    keyword_chunks = get_relevant_chunks_by_keywords(
        db, project_id, message, candidate_limit
    )

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
      You are a document question-answering assistant.

      Your job is to answer the user's question using ONLY the information
      contained in the provided context.

      STRICT RULES:
      1. Do not use your general knowledge.
      2. Do not add information that is not explicitly stated in the context.
      3. Do not make assumptions or suggestions based on information outside
        the context.
      4. If the context does not contain the answer, say:
        "I don't have enough information in the provided documents to answer that."
      5. Keep the answer concise and directly relevant to the question.

      User question:
      {content}

      Context:
      {context}

      Answer:
    """

    return get_response(prompt)
