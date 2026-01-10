# OOLONG-Pairs Experiment

This experiment reproduces the OOLONG-Pairs benchmark from the RLM paper (arXiv:2512.24601), which demonstrates the most dramatic performance gap between vanilla LLMs and RLM.

## Why This Experiment?

| Method | F1 Score |
|--------|----------|
| GPT-5 (base) | 0.04% |
| Summary agent | 0.01% |
| CodeAct + BM25 | 24.67% |
| **RLM** | **58.00%** |

This is a **1,450x improvement** over the base model. The task is specifically designed to require quadratic reasoning over the input - something vanilla LLMs cannot do.

## The Task

Given a dataset of questions with:
- User IDs
- Timestamps
- Question text (needs semantic classification)

Find all pairs of users (user_id_1, user_id_2) that satisfy criteria like:

> "List all pairs of user IDs where both users have at least one instance with an entity or numeric value, and all instances that are an entity for both users must be before March 15, 2023."

This requires:
1. **Semantic classification** of each question (entity, location, numeric value, human being, description/abstract concept, abbreviation)
2. **Grouping** by user ID
3. **O(n²) pairwise comparison** across all users
4. **Filtering** by complex boolean + temporal criteria

## Why Vanilla LLMs Fail

1. **Context overload**: Even if the data fits in context, reasoning about all pairs exhausts attention
2. **No intermediate storage**: Can't build up a classification table and query it
3. **No programmatic comparison**: Can't enumerate pairs systematically

## Why RLM Succeeds

1. **Decomposition**: Process questions in chunks, classify each
2. **Persistent state**: Store classifications in a data structure
3. **Programmatic aggregation**: Use code to enumerate pairs and check criteria
4. **Sub-LLM calls**: Use LLM for semantic classification of each question

## Files

- `generate_dataset.py` - Generate a synthetic OOLONG-Pairs dataset
- `task.json` - The task specification
- `run_vanilla.py` - Run with vanilla LLM (expected to fail)
- `run_rlm.py` - Run with Python RLM
- `oolong-pairs.prose` - Run with rlm.prose
- `evaluate.py` - Compare results

## Running the Experiment

```bash
# 1. Generate dataset
python generate_dataset.py --num_users 50 --questions_per_user 10

# 2. Run vanilla LLM
python run_vanilla.py

# 3. Run Python RLM
python run_rlm.py

# 4. Run rlm.prose
prose-run oolong-pairs.prose

# 5. Evaluate
python evaluate.py
```
