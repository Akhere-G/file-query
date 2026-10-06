from sqlalchemy import func, select
from sqlalchemy.orm import Session
from src.features.chat.message_model import Citation, Message, MessageOwner
from src.features.files.embedding_service import generate_embedding, get_response
from src.features.files.file_model import Chunk, File, Project
from src.settings import settings


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


def send_user_message(db: Session, user_id: int, project_id: int, content: str):
    create_message(db, project_id, MessageOwner.user, content)
    chunks = get_relevant_chunks(db, project_id, content)
    response = get_ai_response(content, chunks)
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


def get_relevant_chunks(db: Session, project_id: int, message: str, limit: int = 5):
    query_embedding = generate_embedding(message)
    stmt = (
        select(Chunk)
        .join(File, Chunk.file_id == File.id)
        .where(File.project_id == project_id)
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(settings.RAG_TOP_K)
    )
    chunks = db.execute(stmt).scalars().all()

    return list(chunks)


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
