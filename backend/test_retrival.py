import csv

from sqlalchemy import select
from src.database import SessionLocal
from src.features.auth.user_model import User
from src.features.chat.chat_service import (
    get_relevant_chunks,
    get_relevant_chunks_by_keywords,
    get_relevant_chunks_by_semantics,
)
from src.features.chat.message_model import Message, MessageOwner
from src.features.files.file_model import Chunk, File, FileStatus, Project

TEST_QUERIES = [
    # Budget
    "What are the main costs that should be included in the holiday budget?",
    "What expenses should we consider when planning the overall trip budget?",
    "How should we compare the cost of different flights from the UK to Orlando?",
    "What additional hotel costs should be included besides the nightly rate?",
    "What extra costs might be charged on the cruise?",
    # Flights and accommodation
    "What should we consider when choosing flights to Orlando?",
    "Why should baggage allowances be considered when comparing flights?",
    "What factors should we consider when choosing an Orlando hotel?",
    "Why might staying closer to the theme parks be beneficial?",
    "What hotel facilities would be useful for the family?",
    # Theme parks
    "Which Disney parks are mentioned in the document?",
    "What Disney park would provide the most traditional Disney experience?",
    "What should we consider when deciding which theme parks to visit?",
    "How can we avoid wasting money on theme park tickets?",
    "What additional costs might apply at Universal or Disney?",
    "What should we consider when deciding whether to buy an express pass?",
    # Transport
    "What transport options are suggested for getting around Orlando?",
    "What costs need to be considered if we rent a car?",
    "What are the advantages and disadvantages of using ride-sharing services?",
    "How should we get from Orlando to the cruise port?",
    # Cruise
    "What types of food and dining options might be available on the cruise?",
    "Which cruise activities might cost extra?",
    "What should everyone do after boarding the cruise ship?",
    "Why is the cruise the centrepiece of the holiday?",
    "What should we check before boarding the cruise?",
    # Birthday
    "How should we celebrate Mum's 60th birthday?",
    "What birthday services might the cruise company offer?",
    "What could be included in Mum's birthday celebration?",
    "What types of gifts would Mum appreciate?",
    "What are some experiences that could be given to Mum instead of a physical gift?",
    "What should the family decide about sharing the cost of Mum's birthday?",
    # Mexico
    "What type of activities are suggested for the Mexico stop?",
    "Why might we choose an organised excursion in Mexico?",
    "What are the risks of arranging an independent excursion?",
    "What type of food does the family want to try in Mexico?",
    "What should we consider if we decide to visit a beach in Mexico?",
    # Bahamas
    "What activities are suggested for the Bahamas?",
    "Why is the Bahamas stop intended to be more relaxed?",
    "What water activities could the family do in the Bahamas?",
    "What could we do in the Bahamas besides going to the beach?",
    # Safety and planning
    "Why is it important to leave plenty of time before the ship departs?",
    "What information should everyone have when going ashore?",
    "What should the family do if bad weather affects an excursion?",
    "What information should be included in the plan for each cruise port?",
    "What documents should everyone check before leaving the UK?",
    "What should be included in the shared packing checklist?",
    # Itinerary
    "How many days are we planning to spend in Orlando?",
    "What is the suggested structure for the Orlando itinerary?",
    "What should happen on the first evening in Orlando?",
    "Why should the first day in Orlando not be overloaded with activities?",
    "What should be checked during the final two weeks before the trip?",
    # Questions requiring combining information
    "How could we balance visiting Disney and Universal with having enough time to rest?",
    "How should we decide between a cruise excursion and an independent excursion?",
    "How can we make Mum's birthday feel special without making the itinerary too complicated?",
    "What should we consider when planning transport from the UK through Orlando and onto the cruise?",
    "How should Mexico and the Bahamas differ as part of the holiday?",
    # Information NOT contained in the document
    "How much will the entire holiday cost?",
    "Which cruise ship are we taking?",
    "What exact dates are we travelling?",
    "Which airline should we book?",
    "Which Orlando hotel should we stay at?",
    "What is the name of the cruise port?",
]


def get_project_id(db):
    projects = db.scalars(select(Project)).all()

    if not projects:
        raise RuntimeError("No projects found in the database.")

    print("Available projects:")

    for project in projects:
        print(f"  {project.id}: {project.id}")

    return int(input("\nEnter project ID: "))


def add_results(
    results: list[dict],
    query: str,
    method: str,
    chunks,
):
    for rank, chunk in enumerate(chunks, start=1):
        results.append(
            {
                "query": query,
                "method": method,
                "rank": rank,
                "chunk_id": chunk.id,
                "content": " ".join(chunk.content.split()),
            }
        )


def main():
    db = SessionLocal()

    try:
        project_id = get_project_id(db)

        results = []

        for query_number, query in enumerate(TEST_QUERIES, start=1):
            print(f"\n[{query_number}/{len(TEST_QUERIES)}] {query}")

            semantic_chunks = get_relevant_chunks_by_semantics(
                db,
                project_id,
                query,
                limit=5,
            )

            keyword_chunks = get_relevant_chunks_by_keywords(
                db,
                project_id,
                query,
                limit=5,
            )

            hybrid_chunks = get_relevant_chunks(
                db,
                project_id,
                query,
                candidate_limit=5,
            )

            add_results(
                results,
                query,
                "semantic",
                semantic_chunks,
            )

            add_results(
                results,
                query,
                "keyword",
                keyword_chunks,
            )

            add_results(
                results,
                query,
                "hybrid",
                hybrid_chunks,
            )

        output_file = "retrieval_results.csv"

        with open(
            output_file,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "query",
                    "method",
                    "rank",
                    "chunk_id",
                    "content",
                ],
            )

            writer.writeheader()
            writer.writerows(results)

        print(f"\nSaved {len(results)} results to {output_file}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
