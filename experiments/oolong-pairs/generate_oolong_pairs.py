#!/usr/bin/env python3
"""
Generate OOLONG-Pairs benchmark from TREC-QC dataset.

This reproduces the methodology from the RLM paper (arXiv:2512.24601):
1. Take TREC question classification data (5,452 questions with 6 coarse labels)
2. Assign synthetic user IDs and timestamps
3. Scale to different context lengths (8k to 1M tokens)
4. Apply the 20 OOLONG-Pairs queries that require pairwise reasoning

Data format matches OOLONG:
  "Date: Dec 12, 2022 || User: 63685 || Instance: How many years old is Benny Carter?"

The key insight: vanilla LLMs fail because they can't:
- Classify thousands of questions semantically
- Then compute O(n^2) pairwise relationships
- While tracking temporal and label constraints
"""

import json
import random
import argparse
from datetime import datetime, timedelta
from datasets import load_dataset
from collections import defaultdict
import tiktoken

# The 6 coarse labels from TREC
COARSE_LABELS = {
    0: "DESC",   # description and abstract concepts
    1: "ENTY",   # entities
    2: "HUM",    # human beings
    3: "NUM",    # numeric values
    4: "LOC",    # locations
    5: "ABBR",   # abbreviations
}

LABEL_FULL_NAMES = {
    "DESC": "description and abstract concept",
    "ENTY": "entity",
    "HUM": "human being",
    "NUM": "numeric value",
    "LOC": "location",
    "ABBR": "abbreviation",
}

# The 20 OOLONG-Pairs tasks from Appendix E.1 of the RLM paper
# IMPORTANT: These are copied EXACTLY from the paper
OOLONG_PAIRS_TASKS = [
    # Task 1
    {
        "id": 1,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with a numeric value or location.",
        "type": "both_have_any",
        "categories": ["NUM", "LOC"],
    },
    # Task 2
    {
        "id": 2,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with an entity or human being.",
        "type": "both_have_any",
        "categories": ["ENTY", "HUM"],
    },
    # Task 3
    {
        "id": 3,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with a description and abstract concept or abbreviation.",
        "type": "both_have_any",
        "categories": ["DESC", "ABBR"],
    },
    # Task 4
    {
        "id": 4,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with a human being or location, and all instances that are a human being for both users must be after January 6, 2023.",
        "type": "both_have_any_with_date",
        "categories": ["HUM", "LOC"],
        "date_constraint": {"category": "HUM", "after": "2023-01-06"},
    },
    # Task 5
    {
        "id": 5,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with an entity or numeric value, and all instances that are an entity for both users must be before March 15, 2023.",
        "type": "both_have_any_with_date",
        "categories": ["ENTY", "NUM"],
        "date_constraint": {"category": "ENTY", "before": "2023-03-15"},
    },
    # Task 6
    {
        "id": 6,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with a location or abbreviation.",
        "type": "both_have_any",
        "categories": ["LOC", "ABBR"],
    },
    # Task 7
    {
        "id": 7,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with a description and abstract concept or numeric value, and all instances that are a numeric value for both users must be after February 1, 2023.",
        "type": "both_have_any_with_date",
        "categories": ["DESC", "NUM"],
        "date_constraint": {"category": "NUM", "after": "2023-02-01"},
    },
    # Task 8
    {
        "id": 8,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with a human being or description and abstract concept.",
        "type": "both_have_any",
        "categories": ["HUM", "DESC"],
    },
    # Task 9
    {
        "id": 9,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with an entity or location, and all instances that are a location for both users must be after April 10, 2023.",
        "type": "both_have_any_with_date",
        "categories": ["ENTY", "LOC"],
        "date_constraint": {"category": "LOC", "after": "2023-04-10"},
    },
    # Task 10
    {
        "id": 10,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with a numeric value or abbreviation, and all instances that are an abbreviation for both users must be before May 20, 2023.",
        "type": "both_have_any_with_date",
        "categories": ["NUM", "ABBR"],
        "date_constraint": {"category": "ABBR", "before": "2023-05-20"},
    },
    # Task 11 - Asymmetric
    {
        "id": 11,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) such that one user has at least one instance with entity and one with abbreviation, and the other user has exactly one instance with entity.",
        "type": "asymmetric",
        "user_a": {"has_all": ["ENTY", "ABBR"]},
        "user_b": {"exactly": {"ENTY": 1}},
    },
    # Task 12 - Asymmetric
    {
        "id": 12,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) such that one user has at least two instances with numeric value, and the other user has at least one instance with location and at least one instance with human being.",
        "type": "asymmetric",
        "user_a": {"at_least": {"NUM": 2}},
        "user_b": {"has_all": ["LOC", "HUM"]},
    },
    # Task 13 - Asymmetric
    {
        "id": 13,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) such that one user has exactly one instance with description and abstract concept, and the other user has at least one instance with abbreviation and at least one instance with entity.",
        "type": "asymmetric",
        "user_a": {"exactly": {"DESC": 1}},
        "user_b": {"has_all": ["ABBR", "ENTY"]},
    },
    # Task 14 - Asymmetric
    {
        "id": 14,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) such that one user has at least one instance with human being and at least one instance with numeric value, and the other user has exactly two instances with location.",
        "type": "asymmetric",
        "user_a": {"has_all": ["HUM", "NUM"]},
        "user_b": {"exactly": {"LOC": 2}},
    },
    # Task 15 - Asymmetric
    {
        "id": 15,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) such that one user has at least one instance with entity, at least one instance with location, and at least one instance with abbreviation, and the other user has exactly one instance with numeric value.",
        "type": "asymmetric",
        "user_a": {"has_all": ["ENTY", "LOC", "ABBR"]},
        "user_b": {"exactly": {"NUM": 1}},
    },
    # Task 16 - Asymmetric
    {
        "id": 16,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) such that one user has at least one instance with description and abstract concept and at least one instance with human being, and the other user has at least two instances with entity and exactly one instance with abbreviation.",
        "type": "asymmetric",
        "user_a": {"has_all": ["DESC", "HUM"]},
        "user_b": {"at_least": {"ENTY": 2}, "exactly": {"ABBR": 1}},
    },
    # Task 17 - Asymmetric
    {
        "id": 17,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) such that one user has exactly one instance with numeric value, and the other user has at least one instance with location and at least one instance with description and abstract concept.",
        "type": "asymmetric",
        "user_a": {"exactly": {"NUM": 1}},
        "user_b": {"has_all": ["LOC", "DESC"]},
    },
    # Task 18 - Asymmetric
    {
        "id": 18,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) such that one user has at least one instance with abbreviation and exactly one instance with human being, and the other user has at least one instance with entity and at least one instance with numeric value.",
        "type": "asymmetric",
        "user_a": {"has_all": ["ABBR"], "exactly": {"HUM": 1}},
        "user_b": {"has_all": ["ENTY", "NUM"]},
    },
    # Task 19 - Asymmetric
    {
        "id": 19,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) such that one user has at least two instances with location and at least one instance with entity, and the other user has exactly one instance with description and abstract concept and exactly one instance with abbreviation.",
        "type": "asymmetric",
        "user_a": {"at_least": {"LOC": 2}, "has_all": ["ENTY"]},
        "user_b": {"exactly": {"DESC": 1, "ABBR": 1}},
    },
    # Task 20 - Asymmetric
    {
        "id": 20,
        "query": "In the above data, list all pairs of user IDs (no duplicate pairs, list lower ID first) such that one user has at least one instance with numeric value and at least one instance with human being, and the other user has at least one instance with location, at least one instance with entity, and exactly one instance with abbreviation.",
        "type": "asymmetric",
        "user_a": {"has_all": ["NUM", "HUM"]},
        "user_b": {"has_all": ["LOC", "ENTY"], "exactly": {"ABBR": 1}},
    },
]

# Standard query suffix from the paper
QUERY_SUFFIX = """Each of the questions can be labelled as one of the labels (the data does not provide the labels, you need to figure out the label from the semantics of the question): description and abstract concept, entity, human being, numeric value, location, abbreviation. In your answer, list all pairs in the format (user id 1, user id 2), separated by newlines."""


def generate_user_id() -> int:
    """Generate a 5-digit user ID like the paper uses."""
    return random.randint(10000, 99999)


def generate_timestamp(start_date: datetime, end_date: datetime) -> str:
    """Generate a random timestamp in OOLONG format (e.g., 'Dec 12, 2022')."""
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    dt = start_date + timedelta(days=random_days)
    return dt.strftime("%b %d, %Y")


def parse_date(date_str: str) -> datetime:
    """Parse date from either our format or constraint format."""
    try:
        return datetime.strptime(date_str, "%b %d, %Y")
    except:
        return datetime.strptime(date_str, "%Y-%m-%d")


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens in text using tiktoken."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def generate_dataset(
    target_tokens: int,
    num_users: int = 500,  # More users for sparse constraints
    seed: int = 42,
) -> tuple[list[dict], dict]:
    """
    Generate OOLONG-Pairs style dataset at specified token count.
    
    Returns:
        entries: List of {user_id, timestamp, question, label} dicts
        user_labels: Dict mapping user_id to list of {label, timestamp}
    """
    random.seed(seed)
    
    # Load TREC dataset
    print("Loading TREC-QC dataset...")
    trec = load_dataset("SetFit/TREC-QC", split="train")
    
    # Date range matching paper examples
    start_date = datetime.strptime("2022-10-01", "%Y-%m-%d")
    end_date = datetime.strptime("2023-06-30", "%Y-%m-%d")
    
    # Generate user pool
    user_pool = [generate_user_id() for _ in range(num_users)]
    
    entries = []
    user_labels = defaultdict(list)
    
    # Header text that will be prepended
    header = """The following lines contain question data. Each line has:
Date || User || Instance (question)

"""
    current_tokens = count_tokens(header)
    
    # Keep adding entries until we hit target token count
    question_idx = 0
    
    while current_tokens < target_tokens:
        # Cycle through TREC questions
        trec_entry = trec[question_idx % len(trec)]
        
        user_id = random.choice(user_pool)
        timestamp = generate_timestamp(start_date, end_date)
        label = COARSE_LABELS[trec_entry['label_coarse']]
        question = trec_entry['text']
        
        entry = {
            "user_id": user_id,
            "timestamp": timestamp,
            "question": question,
            "label": label,  # Ground truth, not shown to model
        }
        entries.append(entry)
        
        user_labels[user_id].append({
            "label": label,
            "timestamp": timestamp,
        })
        
        # Estimate tokens for this line (OOLONG format)
        line = f"Date: {timestamp} || User: {user_id} || Instance: {question}\n"
        current_tokens += count_tokens(line)
        question_idx += 1
        
        # Safety check
        if question_idx > len(trec) * 20:
            print(f"Warning: Exhausted TREC questions ({question_idx} entries)")
            break
    
    return entries, dict(user_labels)


def format_context(entries: list[dict]) -> str:
    """Format entries as context string (without labels) in OOLONG format."""
    header = """The following lines contain question data. Each line has:
Date || User || Instance (question)

"""
    lines = [header]
    for e in entries:
        lines.append(f"Date: {e['timestamp']} || User: {e['user_id']} || Instance: {e['question']}")
    
    return "\n".join(lines)


def check_user_constraint(user_entries: list[dict], constraint: dict) -> bool:
    """Check if a user's entries satisfy a constraint."""
    label_counts = defaultdict(int)
    for e in user_entries:
        label_counts[e['label']] += 1
    
    # Check "has_all" - must have at least one of each
    if "has_all" in constraint:
        for cat in constraint["has_all"]:
            if label_counts.get(cat, 0) < 1:
                return False
    
    # Check "at_least" - must have at least N of each
    if "at_least" in constraint:
        for cat, min_count in constraint["at_least"].items():
            if label_counts.get(cat, 0) < min_count:
                return False
    
    # Check "exactly" - must have exactly N of each
    if "exactly" in constraint:
        for cat, exact_count in constraint["exactly"].items():
            if label_counts.get(cat, 0) != exact_count:
                return False
    
    return True


def compute_ground_truth(user_labels: dict, task: dict) -> list[tuple[int, int]]:
    """Compute ground truth pairs for a task."""
    user_ids = sorted(user_labels.keys())
    pairs = []
    
    if task["type"] == "both_have_any":
        target_cats = set(task["categories"])
        for i, uid1 in enumerate(user_ids):
            for uid2 in user_ids[i+1:]:
                cats1 = set(e["label"] for e in user_labels[uid1])
                cats2 = set(e["label"] for e in user_labels[uid2])
                if (cats1 & target_cats) and (cats2 & target_cats):
                    pairs.append((uid1, uid2))
    
    elif task["type"] == "both_have_any_with_date":
        target_cats = set(task["categories"])
        date_cat = task["date_constraint"]["category"]
        
        if "before" in task["date_constraint"]:
            cutoff = parse_date(task["date_constraint"]["before"])
            date_check = lambda ts: parse_date(ts) < cutoff
        else:
            cutoff = parse_date(task["date_constraint"]["after"])
            date_check = lambda ts: parse_date(ts) > cutoff
        
        for i, uid1 in enumerate(user_ids):
            for uid2 in user_ids[i+1:]:
                entries1 = user_labels[uid1]
                entries2 = user_labels[uid2]
                
                cats1 = set(e["label"] for e in entries1)
                cats2 = set(e["label"] for e in entries2)
                
                if not ((cats1 & target_cats) and (cats2 & target_cats)):
                    continue
                
                # Check date constraint: ALL instances of the constrained category
                # must satisfy the date condition
                def user_passes_date(entries):
                    for e in entries:
                        if e["label"] == date_cat:
                            if not date_check(e["timestamp"]):
                                return False
                    return True
                
                if user_passes_date(entries1) and user_passes_date(entries2):
                    pairs.append((uid1, uid2))
    
    elif task["type"] == "asymmetric":
        user_a_req = task["user_a"]
        user_b_req = task["user_b"]
        
        for i, uid1 in enumerate(user_ids):
            for uid2 in user_ids[i+1:]:
                entries1 = user_labels[uid1]
                entries2 = user_labels[uid2]
                
                # Check both orderings (asymmetric means one user is A, other is B)
                if (check_user_constraint(entries1, user_a_req) and 
                    check_user_constraint(entries2, user_b_req)):
                    pairs.append((uid1, uid2))
                elif (check_user_constraint(entries2, user_a_req) and 
                      check_user_constraint(entries1, user_b_req)):
                    pairs.append((uid1, uid2))
    
    return pairs


def main():
    parser = argparse.ArgumentParser(description="Generate OOLONG-Pairs benchmark")
    parser.add_argument("--target_tokens", type=int, default=32000, 
                        help="Target context size in tokens (default: 32k)")
    parser.add_argument("--num_users", type=int, default=500,
                        help="Number of unique users (default: 500)")
    parser.add_argument("--task_id", type=int, default=1,
                        help="Which of the 20 OOLONG-Pairs tasks to use (1-20)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output_dir", type=str, default=".")
    args = parser.parse_args()
    
    print(f"Generating OOLONG-Pairs dataset...")
    print(f"  Target tokens: {args.target_tokens:,}")
    print(f"  Num users: {args.num_users}")
    print(f"  Task ID: {args.task_id}")
    
    # Generate dataset
    entries, user_labels = generate_dataset(
        target_tokens=args.target_tokens,
        num_users=args.num_users,
        seed=args.seed,
    )
    
    # Format context
    context = format_context(entries)
    actual_tokens = count_tokens(context)
    
    # Get task
    task = OOLONG_PAIRS_TASKS[args.task_id - 1]
    
    # Compute ground truth
    correct_pairs = compute_ground_truth(user_labels, task)
    
    # Build full prompt (task query + suffix)
    full_query = task["query"] + " " + QUERY_SUFFIX
    prompt = context + "\n\n" + full_query
    
    # Save outputs
    output = {
        "metadata": {
            "target_tokens": args.target_tokens,
            "actual_tokens": actual_tokens,
            "num_entries": len(entries),
            "num_users": len(user_labels),
            "task_id": args.task_id,
            "seed": args.seed,
        },
        "task": task,
        "full_query": full_query,
        "correct_pairs": [list(p) for p in correct_pairs],
        "num_correct_pairs": len(correct_pairs),
    }
    
    # Abbreviated filename
    token_suffix = f"{args.target_tokens // 1000}k" if args.target_tokens < 1000000 else f"{args.target_tokens // 1000000}M"
    
    with open(f"{args.output_dir}/dataset_task{args.task_id}_{token_suffix}.json", "w") as f:
        json.dump(output, f, indent=2)
    
    with open(f"{args.output_dir}/input_task{args.task_id}_{token_suffix}.txt", "w") as f:
        f.write(prompt)
    
    print(f"\nGenerated:")
    print(f"  Entries: {len(entries)}")
    print(f"  Unique users: {len(user_labels)}")
    print(f"  Actual tokens: {actual_tokens:,}")
    print(f"  Correct pairs: {len(correct_pairs)}")
    print(f"  Output: {args.output_dir}/dataset_task{args.task_id}_{token_suffix}.json")
    
    # Show some statistics about user distributions
    label_counts = defaultdict(int)
    for uid, entries in user_labels.items():
        for e in entries:
            label_counts[e['label']] += 1
    print(f"\nLabel distribution:")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")


if __name__ == "__main__":
    main()
