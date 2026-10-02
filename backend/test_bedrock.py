from src.database import SessionLocal
from src.features.auth.user_model import User
from src.features.chat.chat_service import send_user_message
from src.features.chat.message_model import Citation, Message, MessageOwner
from src.features.files.file_model import Chunk, File, FileStatus, Project


def main():
    project_id = 1
    user_id = 1

    print("FileQuery CLI")
    print("Project:", project_id)
    print("User:", user_id)
    print("Type 'exit' to quit.\n")

    db = SessionLocal()

    try:
        while True:
            content = input("You: ").strip()

            if content.lower() == "exit":
                break

            if not content:
                continue

            try:
                message = send_user_message(
                    db=db,
                    user_id=user_id,
                    project_id=project_id,
                    content=content,
                )

                print(f"\nAI: {message.content}")

                if message.chunks:
                    print("\nSources:")
                    for chunk in message.chunks:
                        print(f"- Chunk {chunk.id}: {chunk.content[:100]}...")

                print()

            except Exception as e:
                db.rollback()
                print(f"\nError: {e}\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
