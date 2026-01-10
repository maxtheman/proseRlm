# RLM Fidelity Assessment: rlm.prose vs Python Reference Implementation

## Executive Summary

After detailed analysis of the Python RLM reference implementation (`./rlm/`) and the OpenProse implementation (`rlm.prose`), this assessment concludes that **rlm.prose achieves functional equivalence** with the Python RLM for its core computational model. The systems differ in substrate (Python library vs. declarative VM), but the fundamental RLM algorithm is preserved.

---

## Structural Mapping Table

| Python RLM Component | Location | rlm.prose Equivalent | Notes |
|---------------------|----------|---------------------|-------|
| **Core Loop** | | | |
| `RLM.completion()` | `rlm/core/rlm.py:104-175` | `loop until **state file shows done=true**` | Main iteration loop |
| `max_iterations=30` | `rlm/core/rlm.py:47` | `(max: 30)` in loop | Safety bound |
| `_completion_turn()` | `rlm/core/rlm.py:177-197` | `session: worker` | Single iteration |
| **Termination** | | | |
| `find_final_answer()` | `rlm/utils/parsing.py:26-56` | `done: true` in state.json | Different mechanism, same semantics |
| `FINAL(...)` pattern | `rlm/utils/parsing.py:49-52` | `state.answer = <result>` | File-based vs regex |
| `FINAL_VAR(...)` pattern | `rlm/utils/parsing.py:38-47` | `state.answer = variable_value` | Worker resolves variable |
| **State Management** | | | |
| `LocalREPL.locals` | `rlm/environments/local_repl.py:177-181` | `./tmp/rlm_state/state.json` | Persistent namespace vs file |
| `LocalREPL.globals` | `rlm/environments/local_repl.py:128-133` | Worker's computational context | Agent has full tool access |
| Context loading | `LocalREPL.load_context()` | `state.json["problem"]` | Both inject into execution context |
| **Code Execution** | | | |
| `exec(code, combined, combined)` | `rlm/environments/local_repl.py:276` | Bash/Python execution in worker | Worker can use `exec()` directly |
| `_SAFE_BUILTINS` sandbox | `rlm/environments/local_repl.py:18-100` | Claude Code permission system | Different sandboxing model |
| `find_code_blocks()` | `rlm/utils/parsing.py:11-23` | Worker decides execution | No regex extraction needed |
| **Sub-LLM Calls** | | | |
| `llm_query(prompt)` | `rlm/environments/local_repl.py:161-179` | `Task({ prompt: ... })` in worker | Different layer, same capability |
| `llm_query_batched(prompts)` | `rlm/environments/local_repl.py:181-211` | Multiple concurrent `Task()` calls | Parallel execution preserved |
| `LMHandler` socket server | `rlm/core/lm_handler.py` | Mx gateway / Claude CLI | Infrastructure abstraction |
| **Agent Definitions** | | | |
| System prompt | `rlm/utils/prompts.py:RLM_SYSTEM_PROMPT` | `agent worker: prompt: ...` | Role-specific instructions |
| Model selection | `backend_kwargs["model_name"]` | `agent: model: sonnet` | Model binding |
| **Orchestration** | | | |
| `RLM.__init__()` | `rlm/core/rlm.py:27-91` | VM initialization | Configuration |
| Environment spawn | `_spawn_completion_context()` | `session: initializer` | Setup phase |
| Result extraction | `RLMChatCompletion` | `session: extractor` | Answer formatting |
| **Logging/Observability** | | | |
| `RLMLogger` | `rlm/logger/` | State files in `./tmp/rlm_state/` | File-based trace |
| `VerbosePrinter` | `rlm/logger/verbose.py` | VM narration (emoji markers) | Execution visibility |
| **Multi-turn Support** | | | |
| `SupportsPersistence` protocol | `rlm/environments/base_env.py:68-140` | Persistent state directory | Both support continuation |
| `add_context()` / `add_history()` | `rlm/environments/local_repl.py:213-270` | Append to state files | State accumulation |

---

## Architectural Comparison

### Python RLM Architecture
```
User Code
    │
    ▼
┌─────────────┐
│    RLM      │  ◄── Orchestrator (Python class)
└─────┬───────┘
      │
      ▼
┌─────────────┐     ┌─────────────┐
│  LMHandler  │◄───►│   Client    │  ◄── LLM API (OpenAI, Anthropic, etc.)
└─────┬───────┘     └─────────────┘
      │
      ▼
┌─────────────┐
│  LocalREPL  │  ◄── Execution environment (exec() with namespace)
└─────────────┘
      │
      ├── llm_query() ──► LMHandler (socket) ──► LLM
      ├── llm_query_batched() ──► LMHandler (async) ──► LLMs
      └── FINAL(...) / FINAL_VAR(...) ──► Termination signal
```

### rlm.prose Architecture
```
User invokes prose-run
    │
    ▼
┌─────────────┐
│  OpenProse  │  ◄── Orchestrator (VM executing .prose file)
│     VM      │
└─────┬───────┘
      │
      ▼
┌─────────────┐     ┌─────────────┐
│    Task     │◄───►│   Claude    │  ◄── Claude CLI / Mx gateway
│    Tool     │     │     API     │
└─────┬───────┘     └─────────────┘
      │
      ▼
┌─────────────┐
│   Worker    │  ◄── Claude Code session (full agent capabilities)
│   Session   │
└─────────────┘
      │
      ├── Task() ──► Sub-agent ──► LLM
      ├── Bash/Python ──► Code execution
      └── state.done = true ──► Termination signal
```

---

## Semantic Equivalence Analysis

### 1. Iteration Model: EQUIVALENT

**Python RLM:**
```python
for i in range(self.max_iterations):
    iteration = self._completion_turn(prompt, lm_handler, environment)
    final_answer = find_final_answer(iteration.response, environment)
    if final_answer is not None:
        return RLMChatCompletion(response=final_answer, ...)
```

**rlm.prose:**
```
loop until **state file shows done=true** (max: 30):
  session: worker
    prompt: "Execute one iteration..."
```

Both implement: bounded iteration with worker-controlled termination.

### 2. Worker Capabilities: EQUIVALENT

| Capability | Python RLM | rlm.prose |
|-----------|-----------|-----------|
| Execute Python | `exec()` in LocalREPL | Worker runs Python via Bash or direct |
| Persistent state | `self.locals` namespace | State files (JSON, SQLite, pickle) |
| Sub-LLM calls | `llm_query()` function | `Task()` tool invocation |
| Parallel LLM | `llm_query_batched()` | Multiple concurrent `Task()` calls |
| Dynamic re-decomposition | Modify data structures | Update `state.items`, set `phase` |

### 3. Termination Semantics: FUNCTIONALLY EQUIVALENT

**Python RLM:** Regex matches `FINAL(...)` or `FINAL_VAR(...)` in LLM text output.

**rlm.prose:** Worker sets `done: true` in state file; VM reads and checks.

**Practical difference:** None. Both are deterministic, worker-controlled. The file-based approach is more explicit and debuggable.

### 4. Context Passing: EQUIVALENT

**Python RLM:** `context` variable injected into exec namespace.

**rlm.prose:** `state.json["problem"]` read by worker; `{problem}` interpolated into prompts.

---

## Remaining Gaps (Post-Clarification)

### Gap 1: Depth Recursion (`max_depth`)

**Python RLM:** Supports `max_depth` parameter for recursive RLM instantiation:
```python
if self.depth >= self.max_depth:
    return self._fallback_answer(prompt)  # Becomes plain LLM
```

**rlm.prose:** No explicit depth tracking. Workers can spawn sub-agents, but there's no built-in depth limit or fallback-to-LLM mechanism.

**Severity:** LOW. Most RLM use cases use `max_depth=1`. If needed, depth can be tracked in state and enforced by worker logic.

**Workaround:**
```json
{
  "depth": 0,
  "max_depth": 2,
  ...
}
```
Worker checks depth before spawning sub-RLM sessions.

### Gap 2: Code Block Parsing

**Python RLM:** Automatically extracts `\`\`\`repl ... \`\`\`` blocks from LLM output and executes them.

**rlm.prose:** Worker decides what to execute. No automatic extraction.

**Severity:** NONE (design difference, not gap). The worker has full agency and can execute code directly. This is actually more flexible.

### Gap 3: Output Truncation

**Python RLM:** `format_iteration()` truncates results > 20,000 chars before adding to history.

**rlm.prose:** No explicit truncation in specification.

**Severity:** LOW. Workers can implement truncation if needed. State files handle large data naturally.

### Gap 4: Usage Tracking

**Python RLM:** `UsageSummary` tracks tokens, calls, execution time per model.

**rlm.prose:** No built-in usage tracking.

**Severity:** LOW. Usage is tracked at the Mx/Claude CLI layer, not in the prose specification.

---

## Validation Experiment Design

### Selected Use Case: Document Analysis (from RLM paper)

The RLM paper describes chunking large documents and querying sub-LLMs per chunk. This is the canonical RLM use case.

### Test Problem
```
Analyze a 50,000 character document and extract:
1. Main themes
2. Key entities mentioned
3. A 100-word summary
```

### Python RLM Implementation

```python
# test_python_rlm.py
from rlm import RLM

document = open("large_document.txt").read()  # 50K chars

rlm = RLM(
    backend="anthropic",
    backend_kwargs={"model_name": "claude-sonnet-4-20250514"},
    environment="local",
    max_iterations=10,
    verbose=True,
)

result = rlm.completion(
    prompt=document,
    root_prompt="Extract themes, entities, and a 100-word summary"
)
print(result.response)
```

**Expected behavior:** The LLM will:
1. Inspect `context` variable
2. Chunk the document (e.g., 5 chunks of 10K chars)
3. Call `llm_query_batched()` on each chunk
4. Aggregate results
5. Return `FINAL(aggregated_answer)`

### rlm.prose Implementation

```
# In rlm.prose, run with:
# prose-run rlm.prose --problem="$(cat large_document.txt)"

# The worker will:
# 1. Read state.json["problem"] (the document)
# 2. Chunk it into state.items
# 3. Process each chunk with Task() calls
# 4. Synthesize and set done=true
```

**Expected behavior:** The worker will:
1. Read state file, see 50K char problem
2. Decompose into chunks, set `phase: "process"`
3. For each chunk, spawn `Task({ prompt: "Analyze: " + chunk })`
4. Aggregate to `state.results`
5. Synthesize, set `done: true`, `answer: <result>`

### Comparison Methodology

| Metric | How to Compare |
|--------|---------------|
| **Correctness** | Both should extract same themes/entities (semantic similarity > 0.9) |
| **Iteration count** | Both should converge in similar iterations (within +/- 2) |
| **Token usage** | Compare total tokens (allowing for prompt overhead differences) |
| **Execution time** | Wall-clock time (network latency dominates) |
| **Trace structure** | Decompose -> Process x N -> Synthesize pattern should match |

### Execution Steps

1. **Prepare test document:** Select a public domain text (e.g., first chapter of a novel)

2. **Run Python RLM:**
   ```bash
   cd ./rlm
   python test_python_rlm.py > python_output.txt 2>&1
   ```

3. **Run rlm.prose:**
   ```bash
   prose-run rlm.prose --problem="$(cat large_document.txt)" > prose_output.txt 2>&1
   ```

4. **Compare state traces:**
   - Python: Check `./logs/` for iteration dumps
   - Prose: Check `./tmp/rlm_state/state.json` snapshots

5. **Semantic comparison:**
   ```python
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('all-MiniLM-L6-v2')
   
   sim = cosine_similarity(
       model.encode([python_answer]),
       model.encode([prose_answer])
   )
   assert sim > 0.9, "Answers should be semantically equivalent"
   ```

---

## Conclusion

**Fidelity Rating: HIGH (4.5/5)**

rlm.prose faithfully implements the core RLM algorithm:
- Bounded iteration loop
- Worker-controlled termination
- Persistent state across iterations
- Sub-LLM call capability
- Dynamic decomposition support

The remaining gaps are minor:
- Depth recursion: Easily added to state schema
- Usage tracking: Handled at infrastructure layer
- Truncation: Optional optimization

The file-based state mechanism is arguably superior for debugging and persistence. The declarative syntax makes the control flow explicit.

**Recommendation:** Proceed with rlm.prose as a valid RLM implementation for OpenProse environments. The validation experiment above can be run to empirically confirm equivalence on real workloads.
