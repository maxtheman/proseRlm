# RLM-as-OpenProse Feasibility Report

## Executive Summary
**Verdict: PARTIALLY FEASIBLE**
- ~40% of RLM patterns work natively in OpenProse
- ~60% require targeted extensions (repl:, spawn functionality, final statement)
- Architectural position: OpenProse HOSTS RLM as embedded capability

## RLM Capabilities Analysis

| Capability | RLM Implementation | OpenProse Status | Extension Needed |
|------------|-------------------|------------------|------------------|
| Iterative loop | completion() with max_iterations=30 | `loop until (max: N)` | No |
| Code execution | LocalREPL with exec() | None | `repl:` block |
| Sub-LLM calls | llm_query(), llm_query_batched() | `session`, `parallel` | Within repl: via spawn() |
| Context passing | context variable in REPL | `context:` property | Bridge specification |
| Parallel execution | llm_query_batched() | `parallel:`, `pmap` | No |
| Termination | FINAL(), FINAL_VAR() | None | `final` statement |
| Depth tracking | depth/max_depth params | None | $depth built-in |
| Error handling | try/except in REPL | `try:/catch:` | No |

## Required Extensions

### 1. `repl:` Block
```ebnf
repl_block = "repl" repl_options? ":" NEWLINE INDENT code_body DEDENT ;
repl_options = "(" option ("," option)* ")" ;
option = "timeout:" NUMBER | "sandbox:" STRING | "persist:" BOOLEAN ;
```

Execution semantics:
- Spawns sandboxed Python interpreter
- Injects: context, llm_query(), llm_query_batched(), FINAL(), FINAL_VAR()
- Captures stdout/return value as block result
- Errors propagate to OpenProse try/catch

### 2. `final` Statement
```ebnf
final_statement = "final" (STRING | IDENTIFIER | "(" expression ")") ;
```

### 3. Context Bridge
- OpenProse `context: x` becomes REPL variable `context = x`
- Array contexts `context: [a, b]` become `context_0`, `context_1`, plus `context` array

## Example: RLM-Style Document Analysis

```prose
agent analyzer:
  model: opus
  prompt: "You analyze documents by chunking and synthesizing"

# Phase 1: Load and chunk document
let chunks = repl (sandbox: "local", timeout: 30000):
  """
  chunk_size = 10000
  chunks = []
  for i in range(0, len(context), chunk_size):
    chunks.append(context[i:i+chunk_size])
  chunks  # Return value
  """
  context: document

# Phase 2: Analyze each chunk in parallel
let analyses = chunks | pmap:
  session: analyzer
    prompt: "Analyze this chunk for key insights"
    context: item

# Phase 3: Iterative synthesis with RLM-style loop
let synthesis = ""
loop until **synthesis is comprehensive and complete** (max: 10):
  synthesis = repl (persist: true):
    """
    combined = "\n".join(analyses)
    if not synthesis:
      result = llm_query(f"Create initial synthesis from: {combined[:5000]}")
    else:
      gaps = llm_query(f"What's missing from: {synthesis}")
      if "complete" in gaps.lower():
        FINAL(synthesis)
      result = llm_query(f"Improve synthesis addressing: {gaps}")
    result
    """
    context: { analyses, synthesis }

final synthesis
```

## Recommended Implementation Path

### Phase 1: Core Extensions (Priority: HIGH)
1. Implement `repl:` block with local sandbox
2. Inject llm_query() that calls OpenProse sessions
3. Implement `final` statement
4. Define context bridge rules

### Phase 2: Advanced Features (Priority: MEDIUM)
1. Add Docker/Modal sandbox options
2. Implement persist: true for stateful REPLs
3. Add $depth tracking for nested spawns

### Phase 3: Production Features (Priority: LOW)
1. Visualization/logging integration
2. Resource limit enforcement
3. REPL namespace isolation for parallel branches

## Conclusion

RLM can be implemented in OpenProse through targeted extensions that maintain OpenProse's declarative philosophy while adding RLM's code execution capabilities. The two paradigms are complementary:

- **OpenProse** excels at: declarative orchestration, parallel coordination, error handling
- **RLM** excels at: dynamic code generation, programmatic data manipulation, recursive decomposition

The recommended approach is to implement OpenProse as a **host** for RLM capabilities, allowing users to choose the right tool for each part of their workflow.

## Appendix: Key RLM Code References

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Main loop | rlm/core/rlm.py | 188-263 | completion() iteration |
| Code exec | rlm/environments/local_repl.py | 248-277 | execute_code() with exec() |
| Sub-LLM | rlm/environments/local_repl.py | 164-212 | llm_query functions |
| Parsing | rlm/utils/parsing.py | 29-58 | FINAL/FINAL_VAR detection |
| Prompts | rlm/utils/prompts.py | 7-78 | System prompt with REPL instructions |
