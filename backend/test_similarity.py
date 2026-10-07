"""
Find a sensible RAG_SIMILARITY_THRESHOLD.

For every test query this script:
  1. fetches the top-N chunks by cosine similarity WITHOUT any threshold,
  2. labels each chunk relevant / not relevant using hand-written gold labels,
  3. sweeps thresholds and reports what each one does to the semantic leg and to
     the full hybrid (semantic + keyword, fused with RRF exactly like production),
  4. checks whether top-1 similarity can separate answerable from unanswerable
     questions (the abstain use case).

Run from the project root, next to your test-retrieval script:

    python -m tune_similarity_threshold --project-id 1
    python -m tune_similarity_threshold --project-id 1 --rewrite   # also rewrite queries

Outputs (in --out-dir): similarity_scores.csv, threshold_sweep.csv, threshold_sweep.png
"""

import argparse
import csv
from pathlib import Path

from sqlalchemy import select
from src.database import SessionLocal
from src.features.auth.user_model import User
from src.features.chat.chat_service import (
    get_relevant_chunks,
    get_relevant_chunks_by_keywords,
    get_relevant_chunks_by_semantics,
)
from src.features.chat.message_model import Message, MessageOwner
from src.features.files.embedding_service import generate_embedding, rewrite_query
from src.features.files.file_model import Chunk, File, FileStatus, Project
from src.settings import settings

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


# Adjust this import to your test script's module name.


# ---------------------------------------------------------------------------
# Gold labels: 1-based position in TEST_QUERIES -> chunk ids that contain the
# answer. Queries 57-62 are NOT answerable from the document (empty set).
# NOTE: chunk ids must match your current database. If you re-ingested the
# documents, the ids changed and these labels need remapping.
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
# Data collection (needs the database)
# ---------------------------------------------------------------------------
def fetch_similarities(db, project_id: int, query: str, top_n: int):
    """Top-N (chunk_id, similarity) with no threshold applied."""
    distance = Chunk.embedding.cosine_distance(generate_embedding(query))
    stmt = (
        select(Chunk.id, distance.label("distance"))
        .join(File, Chunk.file_id == File.id)
        .where(File.project_id == project_id)
        .order_by(distance)
        .limit(top_n)
    )
    return [(cid, 1.0 - float(d)) for cid, d in db.execute(stmt).all()]


def collect(db, project_id: int, top_n: int, top_k: int, rewrite: bool):
    if len(TEST_QUERIES) != 62:
        print(
            f"WARNING: expected 62 test queries, found {len(TEST_QUERIES)}. "
            "Gold labels are keyed by position, so check they still line up."
        )
    data = []
    for i, query in enumerate(TEST_QUERIES, start=1):
        search_query = rewrite_query(query, "") if rewrite else query
        sims = fetch_similarities(db, project_id, search_query, top_n)
        keyword_ids = [
            c.id
            for c in get_relevant_chunks_by_keywords(
                db, project_id, search_query, top_k
            )
        ]
        data.append(
            {
                "idx": i,
                "query": query,
                "search_query": search_query,
                "gold": GOLD_BY_INDEX.get(i, set()),
                "answerable": i in GOLD_BY_INDEX,
                "sims": sims,  # [(chunk_id, similarity)] best first
                "keyword_ids": keyword_ids,
            }
        )
        print(f"[{i}/{len(TEST_QUERIES)}] top sim={sims[0][1]:.3f}  {query}")
    return data


# ---------------------------------------------------------------------------
# Analysis (pure functions, no database)
# ---------------------------------------------------------------------------
def rrf(semantic_ids, keyword_ids, limit, k=60):
    """Same fusion as chat_service.get_relevant_chunks."""
    scores: dict[int, float] = {}
    for ids in (semantic_ids, keyword_ids):
        for rank, cid in enumerate(ids, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda c: scores[c], reverse=True)[:limit]


def rank_metrics(ids, gold):
    hits = [c in gold for c in ids]
    return {
        "hit": any(hits),
        "hit1": bool(hits and hits[0]),
        "rr": next((1 / (i + 1) for i, h in enumerate(hits) if h), 0.0),
        "recall": sum(hits) / len(gold),
        "precision": (sum(hits) / len(ids)) if ids else None,
    }


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else float("nan")


def evaluate(threshold: float, data, top_k: int):
    ans = [d for d in data if d["answerable"]]
    unans = [d for d in data if not d["answerable"]]

    sem_rows, hyb_rows, sem_counts = [], [], []
    for d in ans:
        sem_ids = [c for c, s in d["sims"] if s >= threshold][:top_k]
        sem_counts.append(len(sem_ids))
        sem_rows.append(rank_metrics(sem_ids, d["gold"]))
        hyb_rows.append(rank_metrics(rrf(sem_ids, d["keyword_ids"], top_k), d["gold"]))

    unans_empty = sum(
        1 for d in unans if not [c for c, s in d["sims"] if s >= threshold][:top_k]
    )
    return {
        "threshold": round(threshold, 4),
        "sem_avg_returned": mean(sem_counts),
        "sem_empty_answerable": sum(1 for n in sem_counts if n == 0),
        "sem_hit": mean(r["hit"] for r in sem_rows),
        "sem_recall": mean(r["recall"] for r in sem_rows),
        "sem_precision": mean(r["precision"] for r in sem_rows),
        "unans_abstained": unans_empty,
        "unans_total": len(unans),
        "hyb_hit": mean(r["hit"] for r in hyb_rows),
        "hyb_hit1": mean(r["hit1"] for r in hyb_rows),
        "hyb_mrr": mean(r["rr"] for r in hyb_rows),
        "hyb_recall": mean(r["recall"] for r in hyb_rows),
    }


def percentile(values, p):
    values = sorted(values)
    if not values:
        return float("nan")
    pos = (len(values) - 1) * p
    lo, hi = int(pos), min(int(pos) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def describe(name, values):
    print(
        f"  {name:<32} n={len(values):<4} min={min(values):.3f}  "
        f"p10={percentile(values, 0.1):.3f}  median={percentile(values, 0.5):.3f}  "
        f"p90={percentile(values, 0.9):.3f}  max={max(values):.3f}"
    )


def gate_analysis(data):
    """Can top-1 similarity separate answerable from unanswerable questions?"""
    ans_top = [d["sims"][0][1] for d in data if d["answerable"]]
    unans_top = [d["sims"][0][1] for d in data if not d["answerable"]]

    print("\nTop-1 similarity per query (for an abstain gate):")
    describe("answerable queries", ans_top)
    describe("unanswerable queries", unans_top)

    candidates = sorted(set(ans_top + unans_top))
    best = None
    for t in candidates:
        kept = sum(s >= t for s in ans_top) / len(ans_top)
        abstained = sum(s < t for s in unans_top) / len(unans_top)
        balanced = (kept + abstained) / 2
        if best is None or balanced > best[0]:
            best = (balanced, t, kept, abstained)
    balanced, t, kept, abstained = best
    print(
        f"  Best gate on top-1 similarity: abstain if < {t:.3f}  "
        f"-> answers {kept:.0%} of answerable, abstains on {abstained:.0%} of unanswerable"
    )

    if min(ans_top) > max(unans_top):
        mid = (min(ans_top) + max(unans_top)) / 2
        print(
            f"  Clean separation: any gate between {max(unans_top):.3f} and "
            f"{min(ans_top):.3f} works (midpoint {mid:.3f})."
        )
    else:
        print(
            "  The two groups OVERLAP, so similarity alone cannot cleanly separate them. "
            "Use a reranker score or an LLM check for abstaining."
        )


def print_sweep(rows):
    cols = [
        ("thr", "threshold", "{:.2f}"),
        ("avg_n", "sem_avg_returned", "{:.1f}"),
        ("empty", "sem_empty_answerable", "{:d}"),
        ("s_hit", "sem_hit", "{:.0%}"),
        ("s_rec", "sem_recall", "{:.0%}"),
        ("s_prec", "sem_precision", "{:.0%}"),
        ("abst", None, None),
        ("h_hit", "hyb_hit", "{:.0%}"),
        ("h_hit1", "hyb_hit1", "{:.0%}"),
        ("h_mrr", "hyb_mrr", "{:.3f}"),
        ("h_rec", "hyb_recall", "{:.0%}"),
    ]
    print("\n" + "  ".join(f"{h:>7}" for h, _, _ in cols))
    previous = None
    for r in rows:
        signature = tuple(
            round(r[k], 4) if isinstance(r[k], float) else r[k]
            for k in r
            if k != "threshold"
        )
        if signature == previous:
            continue  # only print rows where something changed
        previous = signature
        cells = []
        for h, key, fmt in cols:
            if h == "abst":
                cells.append(f"{r['unans_abstained']}/{r['unans_total']}".rjust(7))
            elif r[key] != r[key]:  # NaN: nothing returned at this threshold
                cells.append("-".rjust(7))
            else:
                cells.append(fmt.format(r[key]).rjust(7))
        print("  ".join(cells))
    print(
        "\nLegend: avg_n/empty/s_* = semantic leg alone (empty = answerable queries that "
        "got zero chunks); abst = unanswerable queries that got zero semantic chunks; "
        "h_* = full hybrid with the keyword leg."
    )


def recommend(rows, tolerance: float):
    baseline = rows[0]
    ok = [
        r
        for r in rows
        if r["sem_hit"] >= baseline["sem_hit"] - tolerance
        and r["sem_empty_answerable"] <= baseline["sem_empty_answerable"]
    ]
    floor = max(ok, key=lambda r: r["threshold"])
    print("\nRecommendation")
    print(
        f"  Highest threshold that loses no answerable query from the semantic leg: "
        f"{floor['threshold']:.2f}"
    )
    print(
        f"    semantic precision {baseline['sem_precision']:.0%} -> {floor['sem_precision']:.0%}, "
        f"avg chunks {baseline['sem_avg_returned']:.1f} -> {floor['sem_avg_returned']:.1f}, "
        f"unanswerable abstained {floor['unans_abstained']}/{floor['unans_total']}"
    )
    print(
        "  Treat this as a noise floor (drop clearly irrelevant chunks). Set it a little "
        "below this value to leave margin, because 56 queries is a small sample."
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_scores(data, path: Path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "query_idx",
                "query",
                "answerable",
                "rank",
                "chunk_id",
                "similarity",
                "relevant",
            ]
        )
        for d in data:
            for rank, (cid, sim) in enumerate(d["sims"], start=1):
                w.writerow(
                    [
                        d["idx"],
                        d["query"],
                        d["answerable"],
                        rank,
                        cid,
                        f"{sim:.4f}",
                        cid in d["gold"],
                    ]
                )


def write_sweep(rows, path: Path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def plot(data, rows, path: Path):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed, skipping plot (pip install matplotlib).")
        return

    relevant, irrelevant = [], []
    for d in data:
        if d["answerable"]:
            for cid, s in d["sims"]:
                (relevant if cid in d["gold"] else irrelevant).append(s)
    ans_top = [d["sims"][0][1] for d in data if d["answerable"]]
    unans_top = [d["sims"][0][1] for d in data if not d["answerable"]]

    fig, axes = plt.subplots(1, 3, figsize=(17, 4.5))
    bins = 30
    axes[0].hist(
        [irrelevant, relevant],
        bins=bins,
        label=["not relevant", "relevant"],
        color=["#c9c9c9", "#2b7bba"],
        stacked=True,
    )
    axes[0].set(
        title="Chunk similarity: relevant vs not", xlabel="similarity", ylabel="chunks"
    )
    axes[0].legend()

    axes[1].hist(
        [unans_top, ans_top],
        bins=15,
        label=["unanswerable", "answerable"],
        color=["#d9534f", "#2b7bba"],
        alpha=0.8,
    )
    axes[1].set(
        title="Top-1 similarity per query", xlabel="similarity", ylabel="queries"
    )
    axes[1].legend()

    xs = [r["threshold"] for r in rows]
    axes[2].plot(xs, [r["sem_hit"] for r in rows], label="semantic hit@k")
    axes[2].plot(xs, [r["hyb_hit"] for r in rows], label="hybrid hit@k")
    axes[2].plot(xs, [r["sem_precision"] for r in rows], label="semantic precision")
    axes[2].plot(
        xs,
        [r["unans_abstained"] / r["unans_total"] for r in rows],
        label="unanswerable abstained",
        linestyle="--",
    )
    axes[2].set(title="Threshold sweep", xlabel="threshold", ylim=(0, 1.02))
    axes[2].legend()

    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"Saved plot to {path}")


# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--project-id", type=int, default=None)
    parser.add_argument(
        "--top-n",
        type=int,
        default=30,
        help="chunks fetched per query before thresholding (>= corpus size)",
    )
    parser.add_argument("--top-k", type=int, default=settings.RAG_TOP_K)
    parser.add_argument("--min-threshold", type=float, default=0.0)
    parser.add_argument("--max-threshold", type=float, default=0.9)
    parser.add_argument("--step", type=float, default=0.01)
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.0,
        help="allowed drop in semantic hit rate for the recommendation",
    )
    parser.add_argument(
        "--rewrite",
        action="store_true",
        help="run queries through rewrite_query first (extra LLM calls)",
    )
    parser.add_argument("--out-dir", default=".")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        project_id = args.project_id or get_project_id(db)
        data = collect(db, project_id, args.top_n, args.top_k, args.rewrite)
    finally:
        db.close()

    steps = int(round((args.max_threshold - args.min_threshold) / args.step)) + 1
    thresholds = [args.min_threshold + i * args.step for i in range(steps)]
    rows = [evaluate(t, data, args.top_k) for t in thresholds]

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_scores(data, out / "similarity_scores.csv")
    write_sweep(rows, out / "threshold_sweep.csv")

    relevant = [
        s for d in data if d["answerable"] for c, s in d["sims"] if c in d["gold"]
    ]
    irrelevant = [
        s for d in data if d["answerable"] for c, s in d["sims"] if c not in d["gold"]
    ]
    print("\nChunk similarity distributions (answerable queries):")
    describe("relevant chunks", relevant)
    describe("not-relevant chunks", irrelevant)
    print(
        f"  Lowest relevant chunk: {min(relevant):.3f}; "
        f"{sum(s >= min(relevant) for s in irrelevant)} not-relevant chunks score at or above it."
    )

    gate_analysis(data)
    print_sweep(rows)
    recommend(rows, args.tolerance)
    plot(data, rows, out / "threshold_sweep.png")
    print(f"\nSaved similarity_scores.csv and threshold_sweep.csv to {out.resolve()}")


if __name__ == "__main__":
    main()
