from sqlalchemy import select
from src.database import SessionLocal
from src.features.auth.user_model import User
from src.features.chat.message_model import Citation, Message
from src.features.files.embedding_service import get_response
from src.features.files.file_model import Chunk, File, FileStatus, Project


def main() -> None:
    with SessionLocal() as db:
        chunks = db.scalars(select(Chunk)).all()

        try:
            for chunk in chunks:
                chunk.title = get_response(
                    f"Create a title for this chunk based on its content. Just return the title with no quotes and no markdown and make sure it is one sentence, less than 100 characters. Content = {chunk.content}"
                )

                print(f"Add title {chunk.id} {chunk.title}")
            db.commit()
        except Exception as error:
            print(f"Failed to make title file {error}")
            db.rollback()
            raise


if __name__ == "__main__":
    main()
