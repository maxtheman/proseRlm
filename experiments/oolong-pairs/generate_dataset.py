#!/usr/bin/env python3
"""
Generate a synthetic OOLONG-Pairs dataset.

Based on the TREC question classification task from the RLM paper.
Each entry has:
- user_id: Which user asked the question
- timestamp: When the question was asked
- question: The question text (to be semantically classified)

The semantic categories are:
- DESC: Description and abstract concept
- ENTY: Entity
- HUM: Human being
- NUM: Numeric value
- LOC: Location
- ABBR: Abbreviation
"""

import json
import random
import argparse
from datetime import datetime, timedelta

# Sample questions by category (based on TREC coarse categories)
QUESTIONS_BY_CATEGORY = {
    "DESC": [
        "What is the meaning of life?",
        "How does photosynthesis work?",
        "Why do leaves change color in fall?",
        "What causes earthquakes?",
        "How are rainbows formed?",
        "What is the theory of relativity?",
        "Why is the sky blue?",
        "How do computers work?",
        "What is democracy?",
        "Why do we dream?",
        "What is artificial intelligence?",
        "How does the internet work?",
        "What causes inflation?",
        "Why do birds migrate?",
        "How do vaccines work?",
    ],
    "ENTY": [
        "What is the largest mammal?",
        "What planet is known as the Red Planet?",
        "What is the tallest building in the world?",
        "What is the national flower of Japan?",
        "What car company makes the Mustang?",
        "What is the largest ocean?",
        "What fruit is known as the king of fruits?",
        "What metal is liquid at room temperature?",
        "What is the smallest country in the world?",
        "What bird can fly backwards?",
        "What gemstone is red?",
        "What instrument has 88 keys?",
        "What animal is the symbol of peace?",
        "What tree produces acorns?",
        "What is the hardest natural substance?",
    ],
    "HUM": [
        "Who invented the telephone?",
        "Who wrote Romeo and Juliet?",
        "Who was the first president of the United States?",
        "Who discovered penicillin?",
        "Who painted the Mona Lisa?",
        "Who founded Microsoft?",
        "Who was the first person on the moon?",
        "Who wrote the theory of evolution?",
        "Who invented the light bulb?",
        "Who discovered America?",
        "Who is the CEO of Tesla?",
        "Who composed the Ninth Symphony?",
        "Who discovered gravity?",
        "Who wrote 1984?",
        "Who founded Apple?",
    ],
    "NUM": [
        "How many planets are in the solar system?",
        "What is the population of China?",
        "How tall is Mount Everest?",
        "What year did World War II end?",
        "How many bones are in the human body?",
        "What is the speed of light?",
        "How many states are in the USA?",
        "What is the boiling point of water?",
        "How old is the Earth?",
        "What is the distance to the Moon?",
        "How many continents are there?",
        "What year was the internet invented?",
        "How many teeth do adults have?",
        "What is the freezing point of water in Fahrenheit?",
        "How long is a marathon?",
    ],
    "LOC": [
        "Where is the Eiffel Tower located?",
        "Where is the Amazon River?",
        "What country is the Great Wall in?",
        "Where is Silicon Valley?",
        "What city is the Colosseum in?",
        "Where are the Pyramids of Giza?",
        "What continent is Egypt in?",
        "Where is the Taj Mahal?",
        "What country is Mount Fuji in?",
        "Where is the Grand Canyon?",
        "What city is the Statue of Liberty in?",
        "Where is Machu Picchu?",
        "What country is the Outback in?",
        "Where is the Louvre Museum?",
        "What city is Big Ben in?",
    ],
    "ABBR": [
        "What does NASA stand for?",
        "What does CEO mean?",
        "What is the full form of USA?",
        "What does HTTP stand for?",
        "What does DNA stand for?",
        "What is FBI short for?",
        "What does UNESCO mean?",
        "What is the abbreviation for California?",
        "What does ASAP stand for?",
        "What is PhD short for?",
        "What does NATO stand for?",
        "What is the full form of WHO?",
        "What does RAM stand for?",
        "What is the abbreviation for Doctor?",
        "What does RSVP mean?",
    ],
}

# Full category names for prompts
CATEGORY_FULL_NAMES = {
    "DESC": "description and abstract concept",
    "ENTY": "entity",
    "HUM": "human being",
    "NUM": "numeric value",
    "LOC": "location",
    "ABBR": "abbreviation",
}


def generate_timestamp(start_date: datetime, end_date: datetime) -> str:
    """Generate a random timestamp between start and end dates."""
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86400)
    dt = start_date + timedelta(days=random_days, seconds=random_seconds)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def generate_dataset(
    num_users: int = 50,
    min_questions_per_user: int = 3,
    max_questions_per_user: int = 10,
    start_date: str = "2023-01-01",
    end_date: str = "2023-06-30",
    seed: int = 42,
) -> tuple[list[dict], dict[str, list]]:
    """
    Generate a synthetic OOLONG-Pairs dataset.
    
    Returns:
        entries: List of {user_id, timestamp, question} dicts
        ground_truth: Dict mapping user_id to list of {category, timestamp, question}
    """
    random.seed(seed)
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    entries = []
    ground_truth = {}
    
    for user_id in range(1, num_users + 1):
        num_questions = random.randint(min_questions_per_user, max_questions_per_user)
        user_entries = []
        
        for _ in range(num_questions):
            # Pick a random category and question
            category = random.choice(list(QUESTIONS_BY_CATEGORY.keys()))
            question = random.choice(QUESTIONS_BY_CATEGORY[category])
            timestamp = generate_timestamp(start_dt, end_dt)
            
            entry = {
                "user_id": user_id,
                "timestamp": timestamp,
                "question": question,
            }
            entries.append(entry)
            
            user_entries.append({
                "category": category,
                "timestamp": timestamp,
                "question": question,
            })
        
        ground_truth[str(user_id)] = user_entries
    
    # Shuffle entries to simulate real-world disorder
    random.shuffle(entries)
    
    return entries, ground_truth


def generate_task(task_num: int) -> dict:
    """Generate a task specification based on the paper's examples."""
    
    tasks = [
        {
            "id": 1,
            "query": "List all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with an entity or location.",
            "criteria": {
                "type": "both_have_any",
                "categories": ["ENTY", "LOC"],
            },
        },
        {
            "id": 2,
            "query": "List all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with a description and abstract concept or human being.",
            "criteria": {
                "type": "both_have_any",
                "categories": ["DESC", "HUM"],
            },
        },
        {
            "id": 3,
            "query": "List all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with a numeric value or abbreviation.",
            "criteria": {
                "type": "both_have_any",
                "categories": ["NUM", "ABBR"],
            },
        },
        {
            "id": 4,
            "query": "List all pairs of user IDs (no duplicate pairs, list lower ID first) where both users have at least one instance with an entity or numeric value, and all instances that are an entity for both users must be before March 15, 2023.",
            "criteria": {
                "type": "both_have_any_with_date",
                "categories": ["ENTY", "NUM"],
                "date_constraint": {
                    "category": "ENTY",
                    "before": "2023-03-15",
                },
            },
        },
        {
            "id": 5,
            "query": "List all pairs of user IDs (no duplicate pairs, list lower ID first) such that one user has at least one instance with entity and one with abbreviation, and the other user has exactly one instance with entity.",
            "criteria": {
                "type": "asymmetric",
                "user_a": {"has_all": ["ENTY", "ABBR"]},
                "user_b": {"exactly": {"ENTY": 1}},
            },
        },
    ]
    
    if task_num <= len(tasks):
        return tasks[task_num - 1]
    else:
        # Generate a random task
        return tasks[0]


def compute_ground_truth_pairs(ground_truth: dict, task: dict) -> list[tuple[int, int]]:
    """Compute the correct pairs for a given task."""
    
    user_ids = sorted([int(uid) for uid in ground_truth.keys()])
    pairs = []
    
    criteria = task["criteria"]
    
    if criteria["type"] == "both_have_any":
        # Both users have at least one instance with any of the specified categories
        target_cats = set(criteria["categories"])
        
        for i, uid1 in enumerate(user_ids):
            for uid2 in user_ids[i+1:]:
                cats1 = set(e["category"] for e in ground_truth[str(uid1)])
                cats2 = set(e["category"] for e in ground_truth[str(uid2)])
                
                if (cats1 & target_cats) and (cats2 & target_cats):
                    pairs.append((uid1, uid2))
    
    elif criteria["type"] == "both_have_any_with_date":
        target_cats = set(criteria["categories"])
        date_cat = criteria["date_constraint"]["category"]
        before_date = datetime.strptime(criteria["date_constraint"]["before"], "%Y-%m-%d")
        
        for i, uid1 in enumerate(user_ids):
            for uid2 in user_ids[i+1:]:
                entries1 = ground_truth[str(uid1)]
                entries2 = ground_truth[str(uid2)]
                
                cats1 = set(e["category"] for e in entries1)
                cats2 = set(e["category"] for e in entries2)
                
                # Check category requirement
                if not ((cats1 & target_cats) and (cats2 & target_cats)):
                    continue
                
                # Check date constraint for the specific category
                def check_date_constraint(entries):
                    for e in entries:
                        if e["category"] == date_cat:
                            ts = datetime.strptime(e["timestamp"], "%Y-%m-%d %H:%M:%S")
                            if ts >= before_date:
                                return False
                    return True
                
                if check_date_constraint(entries1) and check_date_constraint(entries2):
                    pairs.append((uid1, uid2))
    
    elif criteria["type"] == "asymmetric":
        user_a_req = criteria["user_a"]
        user_b_req = criteria["user_b"]
        
        def matches_a(entries):
            cats = set(e["category"] for e in entries)
            return all(c in cats for c in user_a_req.get("has_all", []))
        
        def matches_b(entries):
            cat_counts = {}
            for e in entries:
                cat_counts[e["category"]] = cat_counts.get(e["category"], 0) + 1
            for cat, count in user_b_req.get("exactly", {}).items():
                if cat_counts.get(cat, 0) != count:
                    return False
            return True
        
        for i, uid1 in enumerate(user_ids):
            for uid2 in user_ids[i+1:]:
                entries1 = ground_truth[str(uid1)]
                entries2 = ground_truth[str(uid2)]
                
                # Check both orderings (asymmetric)
                if (matches_a(entries1) and matches_b(entries2)) or \
                   (matches_a(entries2) and matches_b(entries1)):
                    pairs.append((uid1, uid2))
    
    return pairs


def format_dataset_for_prompt(entries: list[dict]) -> str:
    """Format the dataset as it would appear in a prompt."""
    lines = []
    for e in entries:
        lines.append(f"User {e['user_id']} | {e['timestamp']} | {e['question']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate OOLONG-Pairs dataset")
    parser.add_argument("--num_users", type=int, default=50, help="Number of users")
    parser.add_argument("--min_questions", type=int, default=3, help="Min questions per user")
    parser.add_argument("--max_questions", type=int, default=10, help="Max questions per user")
    parser.add_argument("--task", type=int, default=1, help="Task number (1-5)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output_dir", type=str, default=".", help="Output directory")
    args = parser.parse_args()
    
    # Generate dataset
    entries, ground_truth = generate_dataset(
        num_users=args.num_users,
        min_questions_per_user=args.min_questions,
        max_questions_per_user=args.max_questions,
        seed=args.seed,
    )
    
    # Generate task
    task = generate_task(args.task)
    
    # Compute ground truth pairs
    correct_pairs = compute_ground_truth_pairs(ground_truth, task)
    
    # Format dataset for prompts
    dataset_text = format_dataset_for_prompt(entries)
    
    # Build the full prompt
    prompt = f"""In the above data, each line contains: User ID | Timestamp | Question

The questions can be labelled as one of these categories (the data does not provide the labels, you need to figure out the label from the semantics of the question):
- description and abstract concept
- entity  
- human being
- numeric value
- location
- abbreviation

{task['query']}

In your answer, list all pairs in the format (user id 1, user id 2), separated by newlines."""
    
    # Save outputs
    output = {
        "dataset": entries,
        "dataset_text": dataset_text,
        "task": task,
        "prompt": prompt,
        "ground_truth_classifications": ground_truth,
        "correct_pairs": [list(p) for p in correct_pairs],
        "num_correct_pairs": len(correct_pairs),
        "metadata": {
            "num_users": args.num_users,
            "num_entries": len(entries),
            "seed": args.seed,
        },
    }
    
    with open(f"{args.output_dir}/dataset.json", "w") as f:
        json.dump(output, f, indent=2)
    
    with open(f"{args.output_dir}/input.txt", "w") as f:
        f.write(dataset_text + "\n\n" + prompt)
    
    print(f"Generated dataset with {len(entries)} entries from {args.num_users} users")
    print(f"Task {args.task}: {len(correct_pairs)} correct pairs")
    print(f"Output saved to {args.output_dir}/dataset.json and {args.output_dir}/input.txt")


if __name__ == "__main__":
    main()
