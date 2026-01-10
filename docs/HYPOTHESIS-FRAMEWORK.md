# RLM-as-OpenProse: Formal Hypothesis Framework

**Date:** 2026-01-10  
**Status:** Response to Critic's Blocking Issue  
**Goal:** Separate conflated claims and establish rigorous validation criteria

---

## The Blocking Issue

The critic identified that **one experimental result (54.9% F1) is being used to support three distinct claims**:

1. **H1 (Structural):** rlm.prose can express RLM patterns
2. **H2 (Behavioral):** rlm.prose achieves similar results to Python RLM
3. **H3 (Gap explanation):** The agent used regex instead of the Task tool

**Problem:** These hypotheses require separate validation. A single F1 score cannot conclusively validate all three.

---

## User's Research Question

> "My aim is to see how close we can get to RLM with OpenProse. Structural isomorphism? Behavioral equivalence?"

This question contains two distinct dimensions:

1. **Structural isomorphism:** Can OpenProse express the same computational patterns as RLM?
2. **Behavioral equivalence:** Do OpenProse implementations produce equivalent results to RLM?

---

## Formal Hypothesis Definitions

### H1: Structural Expressiveness

**Claim:** OpenProse (as currently implemented) can express all core RLM computational patterns.

**Formal Definition:**
```
∀ pattern ∈ RLM_PATTERNS:
  ∃ prose_code ∈ OpenProse:
    semantics(prose_code) ≡ semantics(pattern)
```

Where `RLM_PATTERNS` includes:
- Bounded iteration loop with worker-controlled termination
- Persistent state across iterations
- Sub-LLM queries (recursive calls to LLM)
- Parallel sub-LLM queries
- Dynamic problem decomposition
- Code execution within iterations

**Validation Method:** Structural mapping (already performed in FIDELITY-ASSESSMENT.md)

**Current Evidence:**
- ✓ Iteration loop: `loop until **condition** (max: N)`
- ✓ Persistent state: State files maintained across iterations
- ✓ Sub-LLM queries: `Task()` tool available to worker
- ✓ Parallel queries: Multiple concurrent `Task()` calls
- ✓ Dynamic decomposition: Worker modifies `state.items`, `state.phase`
- ✓ Code execution: Worker has Bash/Python access

**Conclusion:** **H1 is VALIDATED** based on structural analysis.

**Remaining structural gaps:**
- Depth tracking (not blocking - implementable via state)
- Automatic code block extraction (design difference, not gap)

---

### H2: Behavioral Equivalence

**Claim:** For a given problem, rlm.prose produces results equivalent to Python RLM.

**Formal Definition:**
```
Given problem P, implementation I ∈ {Python_RLM, rlm.prose}:
  semantic_similarity(I(P), Python_RLM(P)) ≥ θ

Where θ = 0.9 (90% semantic similarity threshold)
```

**Validation Method:** Controlled comparison experiments on benchmark tasks

**Current Evidence:**
- ✗ NO DIRECT COMPARISON EXISTS
- The OOLONG-Pairs experiment (54.9% F1) was run with rlm.prose only
- We do NOT have a Python RLM baseline on the same dataset
- We do NOT know what Python RLM would score on this specific task

**What we know:**
- RLM paper reports ~58% F1 on OOLONG-Pairs (different dataset, unknown scale)
- Our rlm.prose scored 54.9% F1 (1M token dataset)
- The 54.9% vs 58% comparison is INDIRECT and not statistically valid

**Conclusion:** **H2 is UNVALIDATED** - no controlled comparison exists

**What's needed:**
1. Run SAME problem through both Python RLM and rlm.prose
2. Compare outputs on multiple metrics (F1, precision, recall, semantic similarity)
3. Establish statistical significance

---

### H3: Implementation Fidelity (Gap Explanation)

**Claim:** When rlm.prose underperforms expectations, it's due to the agent not using the proper tool (Task) for semantic reasoning.

**Formal Definition:**
```
Given expected_performance E and actual_performance A where A < E:
  
  H3a: agent_used_regex(execution_trace) → explains(A < E)
  H3b: agent_used_task_tool(execution_trace) → A ≈ E

Where:
  E = 58% (paper's reported RLM F1)
  A = 54.9% (our observed F1)
```

**Validation Method:** Ablation study with controlled tool usage

**Current Evidence:**
- ✓ Execution trace shows `classification_method: "Pattern-based regex matching"`
- ✓ This matches RLM paper's documented failure mode (Section B.2)
- ⚠ We do NOT have a controlled experiment showing what happens when Task tool is used

**What we observed:**
```json
// From state.json
{
  "classification_method": "Pattern-based regex matching for question classification",
  "questions_classified": 67866,
  "qualifying_users": 4370,
  "expected_users": 7535
}
```

**Conclusion:** **H3a is SUPPORTED** (agent did use regex), **H3b is UNVALIDATED** (we haven't tested with enforced Task usage)

**What's needed:**
1. Modify prompts to REQUIRE Task tool usage for classification
2. Re-run experiment
3. Compare F1 scores (regex version vs Task version)
4. Measure classification accuracy directly (separate from pair F1)

---

## Validation Criteria Matrix

| Hypothesis | What It Claims | Validation Method | Evidence Type | Current Status |
|------------|----------------|-------------------|---------------|----------------|
| **H1: Structural** | OpenProse can express RLM patterns | Structural mapping | Theoretical analysis | ✓ VALIDATED |
| **H2: Behavioral** | rlm.prose ≈ Python RLM performance | Controlled comparison | Empirical experiment | ✗ UNVALIDATED |
| **H3a: Gap observed** | Agent used regex instead of Task | Trace inspection | Empirical observation | ✓ SUPPORTED |
| **H3b: Gap explains** | Using Task would improve performance | Ablation study | Empirical experiment | ✗ UNVALIDATED |

---

## What the 54.9% F1 Result Actually Supports

The OOLONG-Pairs experiment provides evidence for:

### ✓ Supported Claims

1. **rlm.prose can execute on the OOLONG-Pairs task**
   - The program ran to completion
   - It produced a list of user pairs
   - F1 = 54.9% is dramatically better than vanilla LLM (~0%)

2. **The RLM pattern is expressible in OpenProse**
   - State was maintained across iterations
   - The agent decomposed the problem into phases
   - Programmatic pair enumeration worked correctly

3. **The agent took a suboptimal approach**
   - Used regex instead of semantic classification
   - This matches a known RLM failure mode from the paper

### ✗ Unsupported Claims

1. **rlm.prose is behaviorally equivalent to Python RLM**
   - We have no Python RLM baseline on the SAME dataset
   - Cannot compare 54.9% to Python RLM's score (we don't have it)
   - Paper's 58% is from a different dataset/scale

2. **54.9% is close to the theoretical maximum**
   - We don't know what perfect semantic classification would yield
   - Ground truth has 19.3M pairs; we found 7.9M true positives
   - Unknown what Python RLM achieves on this specific 1M token dataset

3. **Using the Task tool would improve to 58%**
   - Untested hypothesis
   - Need ablation study to confirm

---

## What Still Needs Testing

### Priority 1: Behavioral Equivalence (H2)

**Experiment Design:**

```
For problem P ∈ {OOLONG-32k, OOLONG-131k, OOLONG-1M}:
  
  1. Run Python RLM:
     result_py = python_rlm.completion(P)
  
  2. Run rlm.prose:
     result_prose = prose_run(P)
  
  3. Compare:
     - F1 scores (precision, recall)
     - Semantic similarity of outputs
     - Iteration counts
     - Intermediate state structure
  
  4. Metrics:
     Δ_F1 = |F1_py - F1_prose|
     sem_sim = cosine_similarity(embed(result_py), embed(result_prose))
  
  5. Success criteria:
     Δ_F1 < 5 percentage points  AND  sem_sim > 0.9
```

**Why this validates H2:**
- Direct comparison on identical problem
- Controls for dataset differences
- Measures multiple dimensions of equivalence

---

### Priority 2: Tool Usage Impact (H3b)

**Experiment Design:**

```
For OOLONG-1M problem:
  
  Condition A (Baseline): Current prompts
    → Agent self-selects approach
    → Observed: Regex classification
    → Result: 54.9% F1
  
  Condition B (Enforced Task): Modified prompts
    → Explicit instruction: "MUST use Task tool for each question classification"
    → Add validation: Check that Task was called N times
    → Result: F1_task
  
  Condition C (Ground truth classification): Oracle
    → Provide pre-classified questions
    → Isolates pair enumeration accuracy
    → Result: F1_oracle
  
  Analysis:
    If F1_task > F1_baseline AND F1_task ≈ F1_oracle:
      → H3b validated (Task usage improves performance)
    
    If F1_task ≈ F1_baseline:
      → H3b rejected (Tool choice doesn't matter, gap is elsewhere)
```

**Why this validates H3b:**
- Isolates the impact of Task vs regex
- Provides upper bound (oracle) for comparison
- Directly tests the causal claim

---

### Priority 3: Scaling Behavior

**Experiment Design:**

```
For scale ∈ {32k, 131k, 262k, 524k, 1M} tokens:
  
  1. Run both implementations:
     F1_py(scale), F1_prose(scale)
  
  2. Plot scaling curves
  
  3. Test hypothesis:
     H_scale: Δ_F1(scale) remains constant as scale increases
  
  4. Success criteria:
     Correlation(F1_py, F1_prose) > 0.95
     Mean(Δ_F1) < 5 percentage points
```

**Why this validates behavioral equivalence:**
- Tests if differences are systematic or random
- Reveals if implementations diverge at scale
- Provides multiple comparison points

---

## Rigorous Framework: 3.A Approach

Based on user's priority ("3.A rigorous, then B pragmatic"), here is the rigorous validation plan:

### Phase 1: Establish Baseline (Required for H2)

**Goal:** Get Python RLM performance on our exact datasets

**Steps:**
1. Install Python RLM in `./rlm/` environment
2. Run on OOLONG-32k, OOLONG-131k, OOLONG-1M
3. Record F1, precision, recall, iteration count, token usage
4. Save execution traces for comparison

**Deliverable:** `experiments/oolong-pairs/python-rlm-baseline.md`

**Estimated effort:** 2-4 hours (setup + 3 runs)

---

### Phase 2: Controlled Comparison (Tests H2)

**Goal:** Direct comparison on identical problems

**Steps:**
1. For each scale (32k, 131k, 1M):
   - Run Python RLM
   - Run rlm.prose (already done for 1M)
   - Compute comparative metrics

2. Analyze differences:
   - Are F1 scores within 5 percentage points?
   - Do iteration patterns match?
   - Is semantic similarity > 0.9?

**Deliverable:** `experiments/oolong-pairs/comparison-report.md`

**Success criteria:**
- H2 validated if: Mean(Δ_F1) < 5pp AND sem_sim > 0.9
- H2 rejected if: Systematic gap > 10pp

**Estimated effort:** 4-6 hours (runs + analysis)

---

### Phase 3: Ablation Study (Tests H3b)

**Goal:** Isolate impact of Task tool usage

**Steps:**
1. Create `oolong-pairs-enforced-task.prose`:
   - Add explicit Task requirements to prompts
   - Add validation that Task was called

2. Run on OOLONG-1M:
   - Record F1_enforced
   - Count actual Task calls

3. Compare:
   - F1_enforced vs F1_baseline (54.9%)
   - F1_enforced vs F1_python (from Phase 1)

4. Create oracle condition:
   - Pre-classify questions using ground truth
   - Run pair enumeration only
   - Record F1_oracle

**Deliverable:** `experiments/oolong-pairs/ablation-study.md`

**Success criteria:**
- H3b validated if: F1_enforced > F1_baseline + 5pp
- H3b rejected if: F1_enforced ≈ F1_baseline

**Estimated effort:** 6-8 hours (implementation + runs)

---

### Phase 4: Statistical Validation

**Goal:** Establish confidence intervals and significance

**Steps:**
1. Multiple runs (N=5) for each condition:
   - Python RLM on OOLONG-1M
   - rlm.prose on OOLONG-1M (baseline)
   - rlm.prose on OOLONG-1M (enforced Task)

2. Compute statistics:
   - Mean ± std for each condition
   - Paired t-test: Python RLM vs rlm.prose
   - Effect size (Cohen's d)

3. Establish confidence intervals:
   - 95% CI for Δ_F1

**Deliverable:** `experiments/oolong-pairs/statistical-analysis.md`

**Success criteria:**
- H2 validated if: p > 0.05 (no significant difference)
- H3b validated if: p < 0.05 for Task vs baseline comparison

**Estimated effort:** 4-6 hours (runs + analysis)

---

## Pragmatic Next Steps: 3.B Approach

For immediate progress without full rigorous validation:

### Quick Win 1: Run Python RLM Baseline (2 hours)

**Why:** Provides the missing comparison point for H2

**Steps:**
```bash
cd reference/rlm
python examples/oolong_pairs.py \
  --input ../../experiments/oolong-pairs/input_task1_1M.txt \
  --task ../../experiments/oolong-pairs/task.json \
  --output python_rlm_output.txt

cd ../../experiments/oolong-pairs
python evaluate.py \
  --prediction ../../reference/rlm/python_rlm_output.txt \
  --ground-truth ground_truth_1M.txt
```

**Deliverable:** One F1 score to compare against 54.9%

---

### Quick Win 2: Enforce Task Usage (3 hours)

**Why:** Tests H3b with minimal implementation effort

**Steps:**
1. Copy `oolong-pairs-1M.prose` → `oolong-pairs-1M-enforced.prose`

2. Modify worker prompt:
```prose
agent worker:
  prompt: """
  ...
  
  CRITICAL REQUIREMENT FOR CLASSIFICATION:
  You MUST use the Task tool to classify each question semantically.
  Do NOT use regex patterns or heuristics.
  
  For each question, call:
    Task({
      subagent_type: "general-purpose",
      prompt: "Classify this question as one of: entity, location, 
               numeric value, human being, description, abbreviation.
               Question: <question text>
               Return only the category."
    })
  
  After classification, verify you actually called Task by checking
  the tool usage logs. If you didn't, the run is invalid.
  """
```

3. Run and compare F1

**Deliverable:** F1_enforced to compare against 54.9%

---

### Quick Win 3: Smaller Scale Test (1 hour)

**Why:** Faster iteration for development

**Steps:**
1. Run both Python RLM and rlm.prose on OOLONG-32k
2. Compare F1 scores
3. If close → good signal for H2
4. If divergent → debug at smaller scale first

**Deliverable:** Quick validation signal

---

## Summary Table

| Hypothesis | What We Currently Know | What We Need | Priority |
|------------|----------------------|--------------|----------|
| **H1: Structural** | ✓ Validated via mapping analysis | Nothing - complete | N/A |
| **H2: Behavioral** | 54.9% F1 on rlm.prose, unknown for Python RLM | Python RLM baseline, direct comparison | **HIGH** |
| **H3a: Gap observed** | ✓ Agent used regex, confirmed via trace | Nothing - complete | N/A |
| **H3b: Gap explains** | Hypothesis based on paper's failure modes | Ablation study with enforced Task | **MEDIUM** |

---

## Recommended Execution Plan

### Rigorous Path (User Priority: 3.A)

1. **Week 1:** Run Python RLM baseline (Phase 1)
   - Deliverable: `python-rlm-baseline.md`
   - Validates/Invalidates: H2 (partial)

2. **Week 2:** Controlled comparison at multiple scales (Phase 2)
   - Deliverable: `comparison-report.md`
   - Validates/Invalidates: H2 (complete)

3. **Week 3:** Ablation study (Phase 3)
   - Deliverable: `ablation-study.md`
   - Validates/Invalidates: H3b

4. **Week 4:** Statistical validation (Phase 4)
   - Deliverable: `statistical-analysis.md`
   - Establishes confidence intervals

### Pragmatic Path (Immediate Action)

**This weekend:**
- Quick Win 1: Python RLM baseline (2 hours)
- Quick Win 2: Enforced Task version (3 hours)
- Quick Win 3: 32k scale test (1 hour)

**Deliverable:** Initial comparison data to inform full rigorous study

---

## Success Criteria Summary

| Claim | Success Threshold | Current Status |
|-------|------------------|----------------|
| H1: OpenProse can express RLM | All patterns mappable | ✓ MET |
| H2: Behavioral equivalence | Δ_F1 < 5pp, sem_sim > 0.9 | ⚠ UNTESTED |
| H3a: Agent used regex | Trace evidence | ✓ MET |
| H3b: Task improves performance | F1_task - F1_regex > 5pp | ⚠ UNTESTED |

---

## Conclusion

The blocking critique is **valid and addressed** by this framework:

1. **H1, H2, H3 are now formally separated** with distinct validation criteria
2. **Current evidence is properly scoped** to what it actually supports
3. **Missing experiments are identified** with concrete designs
4. **Both rigorous (3.A) and pragmatic (3.B) paths** are provided

**Bottom line:** The 54.9% F1 result demonstrates that rlm.prose can execute RLM-style programs, but we cannot claim behavioral equivalence to Python RLM without a direct controlled comparison.

**Next action:** User chooses between rigorous multi-week plan or pragmatic quick-win weekend experiments.
