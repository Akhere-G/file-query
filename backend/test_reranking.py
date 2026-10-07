"""
Evaluate whether Bedrock reranking improves the existing hybrid RRF retrieval.

For every test query this script:
  1. retrieves semantic candidates,
  2. retrieves keyword candidates,
  3. combines them using the same RRF implementation as production,
  4. sends the RRF candidates to the Bedrock reranker,
  5. labels results using the existing gold chunk labels,
  6. compares RRF vs reranked results,
  7. writes detailed results and summary metrics to CSV.

Run from the project root:

    python -m test_reranking --project-id 1

With query rewriting:

    python -m test_reranking --project-id 1 --rewrite

Outputs:

    reranking_results.csv
    reranking_summary.csv
"""

RRF_CANDIDATES = 10
import argparse
import csv
import random
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from sqlalchemy import select
from src.database import SessionLocal
from src.features.auth.user_model import User
from src.features.chat.chat_service import (
    get_relevant_chunks_by_keywords,
    get_relevant_chunks_by_semantics,
)
from src.features.chat.message_model import Message, MessageOwner
from src.features.files.embedding_service import rewrite_query
from src.features.files.file_model import Chunk, File, FileStatus, Project
from src.settings import settings

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RRF_K = 60

# Number of candidates retrieved from each retrieval leg.
SEMANTIC_TOP_K = 10
KEYWORD_TOP_K = 10

# Number of chunks passed into the reranker.
RERANK_CANDIDATES = 10

# Number of chunks returned by the reranker.
RERANK_TOP_K = 5

RERANK_REGION = "eu-central-1"

RERANK_MODEL_ARN = "arn:aws:bedrock:eu-central-1::foundation-model/cohere.rerank-v3-5:0"


# ---------------------------------------------------------------------------
# Test queries
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Gold labels
# ---------------------------------------------------------------------------

GOLD_BY_INDEX: dict[int, set[int]] = {
    1: {2, 27},
    2: {2, 27},
    3: {2},
    4: {3},
    5: {4, 8, 9, 25, 27},
    6: {2},
    7: {2},
    8: {3, 18},
    9: {3},
    10: {3},
    11: {19},
    12: {19},
    13: {3, 19, 20},
    14: {3},
    15: {3, 20},
    16: {3, 20},
    17: {4, 18, 24},
    18: {3, 4, 18},
    19: {4},
    20: {22, 26},
    21: {8, 9, 25},
    22: {4, 8, 25},
    23: {8},
    24: {8, 12, 25},
    25: {8, 22},
    26: {5, 9, 12, 17, 25},
    27: {9, 25},
    28: {5, 9, 25, 27},
    29: {17},
    30: {17},
    31: {5, 27},
    32: {13, 14, 16, 26},
    33: {13, 15},
    34: {11, 13, 15},
    35: {14},
    36: {14},
    37: {14, 15, 16, 26},
    38: {14, 16, 26},
    39: {14, 26},
    40: {15, 26},
    41: {11, 13, 14, 15, 26},
    42: {15, 16},
    43: {11, 16},
    44: {16},
    45: {5},
    46: {6},
    47: {18, 24},
    48: {22},
    49: {19},
    50: {18},
    51: {6},
    52: {19, 21, 22, 24},
    53: {4, 13, 15},
    54: {9, 25},
    55: {4, 18, 22, 26},
    56: {13, 14, 16, 26},
}


# ---------------------------------------------------------------------------
# RRF
# ---------------------------------------------------------------------------


def rrf(
    semantic_chunks: list[Chunk],
    keyword_chunks: list[Chunk],
    limit: int,
    k: int = RRF_K,
):
    """
    Same RRF algorithm used in production.
    """

    scores: dict[int, float] = {}
    chunks: dict[int, Chunk] = {}

    for chunk_list in (semantic_chunks, keyword_chunks):
        for rank, chunk in enumerate(chunk_list, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
            chunks[chunk.id] = chunk

    ranked_ids = sorted(
        scores,
        key=lambda chunk_id: scores[chunk_id],
        reverse=True,
    )

    return [
        {
            "chunk": chunks[chunk_id],
            "rrf_rank": rank,
            "rrf_score": scores[chunk_id],
        }
        for rank, chunk_id in enumerate(
            ranked_ids[:limit],
            start=1,
        )
    ]


# ---------------------------------------------------------------------------
# Bedrock reranker
# ---------------------------------------------------------------------------


def get_rerank_client():
    return boto3.client(
        "bedrock-agent-runtime",
        region_name=RERANK_REGION,
    )


def rerank(
    client,
    query: str,
    candidates: list[dict],
):
    """
    Rerank the RRF candidates using Amazon Bedrock.

    Bedrock returns the zero-based index of the original source,
    allowing us to map the reranked result back to the Chunk.
    """
    for attempt in range(6):
        try:
            response = client.rerank(
                queries=[
                    {
                        "type": "TEXT",
                        "textQuery": {
                            "text": query,
                        },
                    }
                ],
                sources=[
                    {
                        "type": "INLINE",
                        "inlineDocumentSource": {
                            "type": "TEXT",
                            "textDocument": {
                                "text": item["chunk"].content,
                            },
                        },
                    }
                    for item in candidates
                ],
                rerankingConfiguration={
                    "type": "BEDROCK_RERANKING_MODEL",
                    "bedrockRerankingConfiguration": {
                        "modelConfiguration": {
                            "modelArn": RERANK_MODEL_ARN,
                        },
                        "numberOfResults": RERANK_TOP_K,
                    },
                },
            )
            time.sleep(1)
            break
        except ClientError as e:
            if e.response["Error"]["Code"] != "ThrottlingException":
                raise

            if attempt == 5:
                raise

            delay = (2**attempt) + random.uniform(0, 0.5)
            print(f"Bedrock throttled, retrying in {delay:.1f}s...")
            time.sleep(delay)

    results = []

    for rerank_rank, result in enumerate(
        response["results"],
        start=1,
    ):
        original_index = result["index"]

        candidate = candidates[original_index]

        results.append(
            {
                **candidate,
                "rerank_rank": rerank_rank,
                "rerank_score": float(result["relevanceScore"]),
            }
        )

    return results


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def reciprocal_rank(ids: list[int], gold: set[int]):
    for rank, chunk_id in enumerate(ids, start=1):
        if chunk_id in gold:
            return 1.0 / rank

    return 0.0


def hit_at_k(
    ids: list[int],
    gold: set[int],
    k: int,
):
    return any(chunk_id in gold for chunk_id in ids[:k])


def recall_at_k(
    ids: list[int],
    gold: set[int],
    k: int,
):
    if not gold:
        return None

    return sum(chunk_id in gold for chunk_id in ids[:k]) / len(gold)


def precision_at_k(
    ids: list[int],
    gold: set[int],
    k: int,
):
    selected = ids[:k]

    if not selected:
        return None

    return sum(chunk_id in gold for chunk_id in selected) / len(selected)


def mean(values):
    values = [value for value in values if value is not None]

    return sum(values) / len(values) if values else float("nan")


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def collect(
    db,
    project_id: int,
    rerank_client,
    rewrite: bool,
):
    rows = []

    for query_idx, query in enumerate(
        TEST_QUERIES,
        start=1,
    ):
        search_query = rewrite_query(query, "") if rewrite else query

        semantic_chunks = get_relevant_chunks_by_semantics(
            db,
            project_id,
            search_query,
            SEMANTIC_TOP_K,
        )

        keyword_chunks = get_relevant_chunks_by_keywords(
            db,
            project_id,
            search_query,
            KEYWORD_TOP_K,
        )

        candidates = rrf(
            semantic_chunks,
            keyword_chunks,
            RRF_CANDIDATES,
        )

        reranked = rerank(
            rerank_client,
            search_query,
            candidates,
        )

        gold = GOLD_BY_INDEX.get(
            query_idx,
            set(),
        )

        answerable = bool(gold)

        # RRF ordering
        rrf_ids = [item["chunk"].id for item in candidates]

        # Reranked ordering
        rerank_ids = [item["chunk"].id for item in reranked]

        for item in candidates:
            chunk = item["chunk"]

            reranked_item = next(
                (result for result in reranked if result["chunk"].id == chunk.id),
                None,
            )

            rows.append(
                {
                    "query_idx": query_idx,
                    "query": query,
                    "search_query": search_query,
                    "answerable": answerable,
                    "chunk_id": chunk.id,
                    "rrf_rank": item["rrf_rank"],
                    "rrf_score": item["rrf_score"],
                    "rerank_rank": (
                        reranked_item["rerank_rank"] if reranked_item else None
                    ),
                    "rerank_score": (
                        reranked_item["rerank_score"] if reranked_item else None
                    ),
                    "relevant": chunk.id in gold,
                    "content": chunk.content,
                }
            )

        print(
            f"[{query_idx}/{len(TEST_QUERIES)}] "
            f"RRF top-1={rrf_ids[0] if rrf_ids else None} "
            f"Rerank top-1={rerank_ids[0] if rerank_ids else None} "
            f"{query}"
        )

    return rows


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def analyse(rows):
    summary = []

    queries = sorted(set(row["query_idx"] for row in rows))

    for query_idx in queries:
        query_rows = [row for row in rows if row["query_idx"] == query_idx]

        gold = {row["chunk_id"] for row in query_rows if row["relevant"]}

        rrf_rows = sorted(
            query_rows,
            key=lambda row: row["rrf_rank"],
        )

        rerank_rows = sorted(
            [row for row in query_rows if row["rerank_rank"] is not None],
            key=lambda row: row["rerank_rank"],
        )

        rrf_ids = [row["chunk_id"] for row in rrf_rows]

        rerank_ids = [row["chunk_id"] for row in rerank_rows]

        summary.append(
            {
                "query_idx": query_idx,
                "query": query_rows[0]["query"],
                "answerable": bool(gold),
                # RRF
                "rrf_hit1": hit_at_k(
                    rrf_ids,
                    gold,
                    1,
                ),
                "rrf_hit3": hit_at_k(
                    rrf_ids,
                    gold,
                    3,
                ),
                "rrf_hit5": hit_at_k(
                    rrf_ids,
                    gold,
                    5,
                ),
                "rrf_mrr": reciprocal_rank(
                    rrf_ids,
                    gold,
                ),
                "rrf_recall5": recall_at_k(
                    rrf_ids,
                    gold,
                    5,
                ),
                "rrf_precision5": precision_at_k(
                    rrf_ids,
                    gold,
                    5,
                ),
                # Reranked
                "rerank_hit1": hit_at_k(
                    rerank_ids,
                    gold,
                    1,
                ),
                "rerank_hit3": hit_at_k(
                    rerank_ids,
                    gold,
                    3,
                ),
                "rerank_hit5": hit_at_k(
                    rerank_ids,
                    gold,
                    5,
                ),
                "rerank_mrr": reciprocal_rank(
                    rerank_ids,
                    gold,
                ),
                "rerank_recall5": recall_at_k(
                    rerank_ids,
                    gold,
                    5,
                ),
                "rerank_precision5": precision_at_k(
                    rerank_ids,
                    gold,
                    5,
                ),
            }
        )

    return summary


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def summarise(summary):
    answerable = [row for row in summary if row["answerable"]]

    def avg(field):
        return mean([row[field] for row in answerable])

    print("\n" + "=" * 80)
    print("RERANKING EVALUATION")
    print("=" * 80)

    print(f"\nAnswerable queries: {len(answerable)}")

    print("\nMetric                  RRF       Reranked    Change")
    print("-" * 60)

    metrics = [
        ("Hit@1", "rrf_hit1", "rerank_hit1"),
        ("Hit@3", "rrf_hit3", "rerank_hit3"),
        ("Hit@5", "rrf_hit5", "rerank_hit5"),
        ("MRR", "rrf_mrr", "rerank_mrr"),
        ("Recall@5", "rrf_recall5", "rerank_recall5"),
        ("Precision@5", "rrf_precision5", "rerank_precision5"),
    ]

    for name, rrf_field, rerank_field in metrics:
        rrf_value = avg(rrf_field)
        rerank_value = avg(rerank_field)

        change = rerank_value - rrf_value

        print(f"{name:<22}{rrf_value:>8.3f}{rerank_value:>12.3f}{change:>12.3f}")

    # Number of queries improved / unchanged / worse
    improved = 0
    unchanged = 0
    worse = 0

    for row in answerable:
        if row["rerank_mrr"] > row["rrf_mrr"]:
            improved += 1
        elif row["rerank_mrr"] < row["rrf_mrr"]:
            worse += 1
        else:
            unchanged += 1

    print("\nMRR per-query change:")
    print(f"  Improved:   {improved}")
    print(f"  Unchanged:  {unchanged}")
    print(f"  Worse:      {worse}")

    # Top-1 changes
    top1_improved = 0
    top1_worse = 0
    top1_unchanged = 0

    for row in answerable:
        rrf = row["rrf_hit1"]
        rerank = row["rerank_hit1"]

        if not rrf and rerank:
            top1_improved += 1
        elif rrf and not rerank:
            top1_worse += 1
        else:
            top1_unchanged += 1

    print("\nHit@1 changes:")
    print(f"  Improved:   {top1_improved}")
    print(f"  Unchanged:  {top1_unchanged}")
    print(f"  Worse:      {top1_worse}")

    # Unanswerable behaviour
    unanswerable = [row for row in summary if not row["answerable"]]

    rrf_empty = 0
    rerank_empty = 0

    for row in unanswerable:
        query_rows = [
            result for result in summary if result["query_idx"] == row["query_idx"]
        ]

        # There are candidates even for unanswerable queries.
        # This is intentionally reported as "top-1 relevance" rather
        # than claiming the reranker can abstain by itself.
        del query_rows

    print(
        "\nUnanswerable queries:",
        len(unanswerable),
    )

    print(
        "  Note: reranking does not automatically abstain. "
        "Use reranker scores as a candidate signal for a later "
        "abstention experiment."
    )


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------


def write_results(rows, path: Path):
    fields = [
        "query_idx",
        "query",
        "search_query",
        "answerable",
        "chunk_id",
        "rrf_rank",
        "rrf_score",
        "rerank_rank",
        "rerank_score",
        "relevant",
        "content",
    ]

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(rows)


def write_summary(summary, path: Path):
    if not summary:
        return

    fields = list(summary[0].keys())

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(summary)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--project-id",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--rewrite",
        action="store_true",
        help="rewrite queries before retrieval",
    )

    parser.add_argument(
        "--out-dir",
        default=".",
    )

    args = parser.parse_args()

    out = Path(args.out_dir)
    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    db = SessionLocal()

    try:
        rerank_client = get_rerank_client()

        rows = collect(
            db,
            args.project_id,
            rerank_client,
            args.rewrite,
        )

    finally:
        db.close()

    summary = analyse(rows)

    summarise(summary)

    write_results(
        rows,
        out / "reranking_results.csv",
    )

    write_summary(
        summary,
        out / "reranking_summary.csv",
    )

    print(f"\nSaved detailed results to {out / 'reranking_results.csv'}")

    print(f"Saved summary to {out / 'reranking_summary.csv'}")


if __name__ == "__main__":
    main()
