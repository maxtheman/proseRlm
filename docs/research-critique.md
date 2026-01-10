# Research Critique: OpenProse RLM Replication

**Date:** 2025-01-10  
**Task:** Critical evaluation of OOLONG-Pairs dataset reproduction and RLM replication  
**Goal:** Assess structural isomorphism and behavioral equivalence between OpenProse and Python RLM

---

## Executive Summary

| Question | Finding |
|----------|---------|
| Did we faithfully reproduce OOLONG-Pairs? | ✅ **YES** - Used authentic TREC-QC data with proper scaling |
| Does the RLM paper provide verification methods? | ✅ **YES** - Ground truth labels enable objective F1 evaluation |
| Is the experiment design sound? | ⚠️ **PARTIALLY** - Strong foundation, missing Python RLM baseline |

**Key Finding:** We achieved 54.9% F1 on OOLONG-1M, but the agent used regex shortcuts instead of the Task tool. Without a Python RLM baseline on our dataset, we cannot determine if this represents equivalent performance.

---

## 1. Data Provenance: ✅ VERIFIED

### Evidence

**Source:** Real TREC-QC dataset from HuggingFace (`SetFit/TREC-QC`)

```python
# From experiments/oolong-pairs/generate_oolong_pairs.py
trec = load_dataset("SetFit/TREC-QC", split="train")
```

**Scale:** 5,452 authentic questions with 6 coarse-grained categories (DESC, ENTY, HUM, NUM, LOC, ABBR)

**Dataset Statistics:**

| Scale | Entries | Unique Users | Ground Truth Pairs |
|-------|---------|--------------|-------------------|
| 32k | 1,089 | 452 | 39,621 |
| 131k | 4,443 | 982 | 319,600 |
| 262k | 8,886 | 1,955 | 1,355,481 |
| 524k | 17,780 | 3,863 | 5,185,810 |
| 1M | 33,933 | 7,535 | 19,316,220 |

**Format matches paper:** `Date: Jan 06, 2023 || User: 44741 || Instance: <question>`

**Conclusion:** Dataset reproduction is faithful to the RLM paper's methodology.

---

## 2. Ground Truth & Verification: ✅ SOUND

### How Verification Works

1. **Labels held back:** TREC coarse labels are used for evaluation only, NOT provided to the model
2. **Task 1 query:** "Find pairs where both users have NUM or LOC questions"
3. **Ground truth computed from actual TREC labels**
4. **F1 score:** Standard precision/recall metric on predicted pairs

### Our Evaluation Script

```python
# From experiments/oolong-pairs/evaluate.py
def compute_f1(predicted, ground_truth):
    true_positives = len(predicted & ground_truth)
    precision = true_positives / len(predicted)
    recall = true_positives / len(ground_truth)
    f1 = 2 * (precision * recall) / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}
```

**Conclusion:** Evaluation framework is sound and objective.

---

## 3. Vanilla GPT-5 Baseline: ✅ EXPLAINED

### The Discrepancy

| Method | F1 Score | Tools Available |
|--------|----------|-----------------|
| GPT-5 vanilla (paper) | 0.04% | ❌ None (raw context only) |
| Our agent (regex) | 54.9% | ✅ Bash, Python, file I/O |
| RLM (paper) | 58% | ✅ REPL, llm_query() |

### Root Cause

The paper's "vanilla" baseline had **NO tools** - just the raw LLM with a massive context window. It failed because:
- Cannot build data structures
- Cannot enumerate O(n²) pairs programmatically
- Pure attention-based reasoning collapses at 1M tokens

Our 55% result had code execution, which is why regex patterns could achieve reasonable precision (82.99%) even without semantic understanding.

**Conclusion:** The gap is explained by capability differences, not dataset issues.

---

## 4. Structural Isomorphism: ✅ STRONG

### Mapping: Python RLM → OpenProse

| RLM Concept | Python RLM | rlm.prose | Match |
|-------------|------------|-----------|-------|
| REPL environment | Python REPL | Bash + file system | ✅ |
| Context variable | `context` string | Input file path | ✅ |
| LLM sub-calls | `llm_query()` | Task tool | ✅ |
| Batch LLM calls | `llm_query_batched()` | Multiple concurrent Tasks | ✅ |
| Code execution | `exec()` in REPL | Bash + Python scripts | ✅ |
| State persistence | Python variables + pickle | state.json + SQLite | ✅ |
| Iterative loop | `while not done` | `loop until done=true` | ✅ |
| Termination | `FINAL()` / `FINAL_VAR()` | `state.done + state.answer` | ✅ |

### Key Architectural Difference

**Python RLM:** Single session with persistent REPL, `llm_query()` makes API calls

**rlm.prose:** Multiple worker sessions in a loop, Task tool spawns new Claude agents

**Semantic equivalence:** Both achieve iterative refinement with sub-LLM decomposition.

**Conclusion:** OpenProse can express all RLM computational patterns.

---

## 5. Behavioral Equivalence: ⚠️ UNVALIDATED

### Our Result

| Metric | Value |
|--------|-------|
| F1 Score | 54.9% |
| Precision | 82.99% |
| Recall | 41.01% |
| Pairs predicted | 9,546,265 |
| Ground truth pairs | 19,316,220 |

### The Critical Problem

**Expected behavior:** Agent uses Task tool for semantic classification

**Actual behavior:** Agent used regex pattern matching

From `state.json`:
```json
"classification_method": "Pattern-based regex matching for question classification"
```

### Why Comparison to Paper is Invalid

We **cannot** compare our 54.9% to the paper's 58% because:
1. **Different datasets** - We generated our own OOLONG-Pairs
2. **Different LLMs** - Claude vs GPT-5
3. **Different behavior** - Regex vs proper sub-LLM calls
4. **No Python RLM baseline** - Never ran Python RLM on our data

**Conclusion:** Behavioral equivalence is UNVALIDATED until we run Python RLM on our dataset.

---

## 6. Hypothesis Framework

### H1: Structural Expressiveness
**Claim:** OpenProse can express all RLM computational patterns  
**Status:** ✅ **VALIDATED** (theoretical mapping complete)

### H2: Behavioral Equivalence
**Claim:** rlm.prose produces equivalent results to Python RLM  
**Status:** ✗ **UNVALIDATED** (no Python RLM baseline on our dataset)

### H3a: Gap Observed
**Claim:** Agent used regex instead of Task tool  
**Status:** ✅ **CONFIRMED** (from state.json execution trace)

### H3b: Gap Explains Performance
**Claim:** Using Task tool would improve performance to ~58%  
**Status:** ⚠️ **UNTESTED** (requires ablation study)

---

## 7. Next Steps

### Priority 1: Establish Python RLM Baseline (H2)
Run the original Python RLM on our OOLONG datasets:
```bash
cd reference/rlm
python -m rlm.run --input ../experiments/oolong-pairs/input_task1_32k.txt
```

### Priority 2: Enforce Task Tool Usage (H3b)
Modify worker prompts to REQUIRE Task tool:
```
CRITICAL: You MUST use the Task tool for semantic classification.
Do NOT use regex or keyword matching. This will be validated.
```

### Priority 3: Multi-Scale Comparison
- Start at 32k for fast iteration
- Compare: Python RLM vs rlm.prose (regex) vs rlm.prose (Task-enforced)
- Scale to 131k, 262k if results are promising

### Success Criteria

For **H2 (Behavioral Equivalence)** to be validated:
- OpenProse F1 within 5 percentage points of Python RLM
- Both use semantic classification (not regex)
- Results hold across multiple scales

### Estimated Timeline
- Python RLM baseline: 1-2 days
- Task-enforced version: 1 day  
- 32k comparison runs: 1 day
- **Total: 3-4 days to definitive answer**

---

## 8. Conclusion

### What We Proved

1. ✅ **Data is authentic** - Real TREC-QC, properly scaled
2. ✅ **Ground truth is sound** - Objective F1 evaluation
3. ✅ **Vanilla baseline explained** - Paper's 0.04% had no tools
4. ✅ **Structural isomorphism** - All RLM patterns expressible in OpenProse
5. ✅ **Agent shortcut confirmed** - Used regex instead of Task tool

### What Remains Unvalidated

1. ⚠️ **Behavioral equivalence** - No Python RLM baseline for comparison
2. ⚠️ **Task tool performance** - Would enforcing Task tool reach 58%?

### Key Insight

The 54.9% F1 result demonstrates that **rlm.prose works structurally** - it can orchestrate iterative problem decomposition with persistent state. However, the agent took a shortcut (regex) rather than using the intended sub-LLM pattern.

This is a **known failure mode** from the RLM paper (Section B.2): agents may choose "faster" approaches over semantically correct ones.

### Confidence Levels

| Claim | Confidence |
|-------|------------|
| Structural isomorphism | 95% |
| Behavioral equivalence | 40% (unvalidated) |
| Experiment soundness | 70% (missing baseline) |

---

## Files Reference

- **Dataset generator:** `experiments/oolong-pairs/generate_oolong_pairs.py`
- **Evaluation script:** `experiments/oolong-pairs/evaluate.py`
- **OpenProse implementation:** `rlm.prose`
- **OOLONG-specific version:** `experiments/oolong-pairs/oolong-pairs-1M.prose`
- **Experiment results:** `experiments/oolong-pairs/EXPERIMENT-LOG.md`
- **RLM paper:** `reference/2512.24601v1.pdf`
