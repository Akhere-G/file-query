import csv

from sqlalchemy import select

from src.database import SessionLocal
from src.features.auth.user_model import User
from src.features.files.file_model import Project, File, Chunk
from src.features.chat.message_model import Message, MessageOwner


def get_project_id(db):
    projects = db.scalars(select(Project)).all()

    if not projects:
        raise RuntimeError("No projects found in the database.")

    print("Available projects:")
    for project in projects:
        print(f"  {project.id}")

    return int(input("\nEnter project ID: "))


def main():
    db = SessionLocal()

    try:
        project_id = get_project_id(db)

        stmt = (
            select(Chunk)
            .join(File, Chunk.file_id == File.id)
            .where(File.project_id == project_id)
            .order_by(Chunk.id)
        )

        chunks = db.scalars(stmt).all()

        if not chunks:
            print("No chunks found for this project.")
            return

        output_file = "chunks.csv"

        with open(output_file, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "chunk_id",
                    "file_id",
                    "content",
                ],
            )

            writer.writeheader()

            for chunk in chunks:
                writer.writerow(
                    {
                        "chunk_id": chunk.id,
                        "file_id": chunk.file_id,
                        "content": " ".join(chunk.content.split()),
                    }
                )

        print(f"\nSaved {len(chunks)} chunks to {output_file}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
