# OOLONG-Pairs Experiment Log

## Experiment 1: 1M Token OOLONG-Pairs with rlm.prose

**Date:** 2025-01-09

**Objective:** Validate that rlm.prose can reproduce the RLM paper's results on the OOLONG-Pairs benchmark at 1M token scale.

### Setup

- **Input:** `input_task1_1M.txt` (~1,000,000 tokens, 33,933 entries, 7,535 unique users)
- **Task:** Find all pairs of user IDs where both users have at least one question classified as "numeric value" OR "location"
- **Ground Truth:** 19,316,220 correct pairs
- **Program:** `oolong-pairs-1M.prose`

### Results

| Metric | Value |
|--------|-------|
| Predicted pairs | 9,546,265 |
| True positives | 7,922,190 |
| **Precision** | 82.99% |
| **Recall** | 41.01% |
| **F1 Score** | **54.90%** |

### Comparison to Paper

| Method | F1 Score | Notes |
|--------|----------|-------|
| GPT-5 (vanilla) | 0.04% | Fails catastrophically |
| RLM(GPT-5) | ~58% | Paper's reported result |
| **rlm.prose** | **54.9%** | This experiment |

### Analysis

The agent achieved 54.9% F1, which is close to the paper's 58% RLM result. However, examination of the state file revealed a critical issue:

**The agent used regex pattern matching instead of sub-LLM calls for semantic classification.**

From `state.json`:
```json
"classification_method": "Pattern-based regex matching for question classification"
```

This is a known failure mode documented in the RLM paper (Section B.2):

> "rule-based syntax rules are unable to perform these transformations programmatically"

Yet our agent attempted exactly that - using regex heuristics instead of semantic classification via the Task tool.

### Comparison to Paper's Failure Modes

The paper describes a similar issue with Qwen3-Coder on OOLONG-Pairs (Section B.2):

1. **Paper's failure:** Model correctly used sub-LLM calls and built up the right answer, but then discarded it and generated a wrong answer from the root LM
2. **Our failure:** Model skipped sub-LLM calls entirely and used regex pattern matching

Both represent the model taking shortcuts to avoid the intended recursive decomposition pattern.

### Statistics from Run

- Questions classified: 67,866 (note: 2x the expected 33,933 - possible double-counting)
- Qualifying users found: 4,370 (vs 7,535 in ground truth - 42% missed)
- Classification method: Regex patterns

### Key Observations

1. **High precision (83%)** - Regex patterns work for obvious cases ("how many", "where is")
2. **Low recall (41%)** - Regex misses nuanced questions requiring semantic understanding
3. **User coverage gap** - Found only 58% of qualifying users

### Files

- State: `../../tmp/rlm_state/state.json`
- Output: `../../tmp/rlm_state/pairs_output.txt`
- Database: `../../tmp/rlm_state/questions.db`

### Next Steps

1. Modify prompts to more strongly encourage/require sub-LLM calls for classification
2. Consider adding validation that checks if Task tool was actually used
3. Test at smaller scales (32k, 131k) to iterate faster
4. Compare results when sub-LLM calls are properly used

---

## Baseline Comparison

| Scale | Ground Truth Pairs | Notes |
|-------|-------------------|-------|
| 32k | 39,621 | 452 users |
| 131k | 319,600 | 982 users |
| 262k | 1,355,481 | 1,955 users |
| 524k | 5,185,810 | 3,863 users |
| 1M | 19,316,220 | 7,535 users |

Pair counts scale quadratically with users, confirming O(n²) complexity of the task.
