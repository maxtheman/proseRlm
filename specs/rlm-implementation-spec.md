# RLM Implementation Specification for OpenProse/Claude Code

## Executive Summary

We are building a bridge that enables Recursive Language Model (RLM) patterns—where LLMs programmatically control iteration, branching, and sub-model invocation—within the OpenProse/Claude Code ecosystem. The core insight is that OpenProse's VM-controlled constructs (`parallel for`, `pmap`, `repeat`, conditional blocks) already provide 85-90% of RLM's capabilities through a different paradigm: instead of LLMs generating Python code that calls `llm_query()`, OpenProse declaratively specifies iteration patterns that the VM executes with LLM-generated decisions at each step. The remaining 10-15% gap—truly dynamic code generation where the LLM writes and executes arbitrary control flow—requires a `repl:` extension that would be a modification to OpenProse.

---

## The Tradeoff

**RLM's Core Innovation:** LLMs generate executable Python code containing loops, conditionals, and `llm_query()` calls. The LLM decides *at runtime* what code to write based on the problem structure it discovers.

**OpenProse's Approach:** The programmer declares iteration patterns (`for`, `repeat`, `parallel for`), and the LLM provides the *content* at each iteration—but cannot invent new control structures dynamically.

| Capability | RLM | OpenProse (Today) | Gap |
|------------|-----|-------------------|-----|
| Fixed iteration with LLM body | `for i in range(n): llm_query()` | `for item in {{items}}: session:` | None |
| Parallel sub-queries | `llm_query_batched()` | `parallel:` blocks, `pmap` | None |
| Conditional branching | `if llm_decides(): ...` | `**condition**` blocks | Minor |
| Early termination | `return FINAL(result)` | `until: **condition**` | Minor |
| **Dynamic code generation** | LLM writes Python with loops | Not possible | **10-15%** |

The gap matters for problems where the decomposition strategy itself must be discovered—e.g., "break this problem into subproblems however makes sense, then solve each recursively."

---

## Option A: Full RLM Parity (requires `repl:` extension)

### What It Enables

A `repl:` block type that allows LLM-generated code to execute within the OpenProse VM, with access to `llm_query()` and session state:

```prose
program solve_dynamic
  input: problem: string
  
  repl:
    language: python
    sandbox: true
    available_functions:
      - llm_query(prompt) -> string
      - llm_query_batched(prompts) -> list[string]
      - get_context(key) -> any
      - set_context(key, value) -> void
      - FINAL(result) -> NoReturn
    
    prompt: |
      You have a problem to solve: {{problem}}
      
      Write Python code that:
      1. Analyzes the problem structure
      2. Decomposes it into subproblems using llm_query()
      3. Combines results
      4. Calls FINAL(answer) when done
      
      Available functions: llm_query, llm_query_batched, get_context, set_context, FINAL
```

### Implementation Sketch

```typescript
// In OpenProse VM (pseudocode)
class ReplBlock extends Block {
  async execute(context: Context): Promise<Result> {
    const code = await this.llm.generate(this.prompt, context);
    
    const sandbox = new PythonSandbox({
      functions: {
        llm_query: async (prompt: string) => {
          return await this.runtime.interactions_create({ input: prompt });
        },
        llm_query_batched: async (prompts: string[]) => {
          return await Promise.all(prompts.map(p => 
            this.runtime.interactions_create({ input: p })
          ));
        },
        FINAL: (result: any) => {
          throw new FinalResult(result);
        },
        get_context: (key: string) => context.get(key),
        set_context: (key: string, val: any) => context.set(key, val),
      },
      timeout: this.config.timeout || 60000,
      memory_limit: this.config.memory_limit || '256MB',
    });
    
    try {
      await sandbox.execute(code);
    } catch (e) {
      if (e instanceof FinalResult) return e.result;
      throw e;
    }
  }
}
```

### Effort Estimate

- **OpenProse VM changes:** 2-3 days (new block type, sandbox integration)
- **Python sandbox:** 1-2 days (use pyodide or restricted exec)
- **Security hardening:** 2-3 days (escape prevention, resource limits)
- **Testing:** 2-3 days
- **Total:** ~10-14 days of focused work

### Risks

- Security surface area (code execution)
- Complexity in debugging LLM-generated code
- Potential for infinite loops despite safeguards

---

## Option B: No-Modification Path (~85-90% coverage)

### What Patterns ARE Achievable Today

OpenProse can express most RLM patterns through its existing constructs. The key insight: **declare the iteration structure, let LLM fill the content**.

#### Pattern 1: Recursive Decomposition (Fixed Depth)

RLM approach:
```python
def solve(problem, depth=0):
    if depth > MAX_DEPTH:
        return llm_query(f"Solve directly: {problem}")
    subproblems = llm_query(f"Decompose: {problem}").split('\n')
    results = [solve(p, depth+1) for p in subproblems]
    return llm_query(f"Combine {results} for {problem}")
```

OpenProse equivalent:
```prose
program recursive_solve
  input: problem: string
  context:
    max_depth: 3
  
  # Level 0: Decompose
  session decompose_0:
    model: sonnet
    prompt: |
      Problem: {{problem}}
      
      Either solve directly (if simple) or decompose into 2-4 subproblems.
      
      Format:
      DIRECT: [solution]
      OR
      SUBPROBLEMS:
      1. [subproblem]
      2. [subproblem]
      ...
  
  **{{decompose_0.output}} contains "DIRECT:"**
    # Base case - extract and return
    session extract_direct:
      prompt: Extract the solution after "DIRECT:" from: {{decompose_0.output}}
    
    return: {{extract_direct.output}}
  
  **{{decompose_0.output}} contains "SUBPROBLEMS:"**
    # Recursive case - parse and solve each
    session parse_subs:
      prompt: |
        Extract subproblems as JSON array from:
        {{decompose_0.output}}
        
        Return: ["subproblem1", "subproblem2", ...]
    
    parallel for sub in {{parse_subs.output | json}}:
      session solve_sub:
        prompt: |
          Solve this subproblem completely:
          {{sub}}
          
          Context: This is part of solving "{{problem}}"
    
    session combine:
      prompt: |
        Original problem: {{problem}}
        Subproblem solutions:
        {{parallel_results | join("\n---\n")}}
        
        Synthesize these into a complete solution.
    
    return: {{combine.output}}
```

#### Pattern 2: Iterative Refinement with Early Exit

RLM approach:
```python
result = initial_attempt(problem)
for i in range(MAX_ITERATIONS):
    critique = llm_query(f"Critique: {result}")
    if "SATISFACTORY" in critique:
        return FINAL(result)
    result = llm_query(f"Improve {result} based on {critique}")
return result
```

OpenProse equivalent:
```prose
program iterative_refine
  input: problem: string
  context:
    max_iterations: 5
    current_solution: ""
  
  session initial:
    prompt: Provide initial solution to: {{problem}}
  
  set current_solution: {{initial.output}}
  
  repeat {{max_iterations}}:
    until: **{{critique.output}} contains "SATISFACTORY"**
    
    session critique:
      prompt: |
        Problem: {{problem}}
        Current solution: {{current_solution}}
        
        Critique this solution. If it's good enough, say "SATISFACTORY".
        Otherwise, list specific improvements needed.
    
    **{{critique.output}} not contains "SATISFACTORY"**
      session improve:
        prompt: |
          Problem: {{problem}}
          Current solution: {{current_solution}}
          Critique: {{critique.output}}
          
          Provide an improved solution addressing the critique.
      
      set current_solution: {{improve.output}}
  
  return: {{current_solution}}
```

#### Pattern 3: Tree Search with Pruning

```prose
program tree_search
  input: initial_state: string
  context:
    max_depth: 5
    current_state: ""
  
  set current_state: {{initial_state}}
  
  repeat {{max_depth}}:
    until: **{{check_solution.output}} contains "SOLVED"**
    
    session check_solution:
      prompt: |
        State: {{current_state}}
        Is this a complete solution? Say "SOLVED" if yes.
    
    **{{check_solution.output}} not contains "SOLVED"**
      # Generate candidates in parallel
      parallel:
        session candidate_1:
          prompt: Generate approach A from state: {{current_state}}
        session candidate_2:
          prompt: Generate approach B from state: {{current_state}}
        session candidate_3:
          prompt: Generate approach C from state: {{current_state}}
      
      # Score candidates in parallel
      parallel:
        session score_1:
          prompt: Score (1-10) this approach: {{candidate_1.output}}
        session score_2:
          prompt: Score (1-10) this approach: {{candidate_2.output}}
        session score_3:
          prompt: Score (1-10) this approach: {{candidate_3.output}}
      
      # Select best (LLM does the comparison)
      session select_best:
        prompt: |
          Pick the best approach:
          A (score {{score_1.output}}): {{candidate_1.output}}
          B (score {{score_2.output}}): {{candidate_2.output}}
          C (score {{score_3.output}}): {{candidate_3.output}}
          
          Return only the full text of the best approach.
      
      set current_state: {{select_best.output}}
  
  return: {{current_state}}
```

#### Pattern 4: Map-Reduce with Dynamic Chunking

```prose
program map_reduce_analysis
  input: 
    documents: list[string]
    query: string
  
  # Map phase: analyze each document in parallel
  parallel for doc in {{documents}}:
    session analyze:
      prompt: |
        Query: {{query}}
        Document: {{doc}}
        
        Extract relevant information. Be concise.
  
  # Reduce phase: synthesize results
  session synthesize:
    context:
      analyses: {{parallel_results}}
    prompt: |
      Query: {{query}}
      
      Individual analyses:
      {{analyses | enumerate | format("Document %d: %s")}}
      
      Synthesize into a comprehensive answer.
  
  return: {{synthesize.output}}
```

### What's NOT Achievable Without Modification

1. **Dynamic decomposition strategies**: Where the LLM decides "I need a BFS here" vs "I need divide-and-conquer" and generates appropriate code.

2. **Arbitrary recursion depth**: OpenProse requires declaring max depth upfront; RLM can recurse until `FINAL()`.

3. **Runtime control flow invention**: LLM cannot create new loop/branch patterns not declared in the .prose file.

4. **Stateful multi-step algorithms**: Where the LLM maintains and manipulates complex state through code (e.g., building a graph structure iteratively).

---

## Option C: Hybrid Approach

### Phase 1: No-Modification (Weeks 1-4)

1. Build library of `.prose` templates covering common RLM patterns
2. Document the mapping from RLM concepts to OpenProse constructs
3. Create example programs demonstrating recursive decomposition, iterative refinement, tree search
4. Validate on real use cases, identify where gaps hurt

### Phase 2: Evaluate Need (Week 5)

Collect data on:
- How often do users hit the "dynamic code generation" wall?
- What workarounds exist (e.g., multiple specialized .prose files)?
- Is the complexity of `repl:` justified by use cases?

### Phase 3: Targeted Extension (If Needed, Weeks 6-8)

If the gap proves significant:

```prose
# Minimal repl: extension - just for the dynamic cases
program dynamic_solver
  input: problem: string
  
  # Try static approach first
  session attempt_static:
    prompt: |
      {{problem}}
      
      Can this be solved with a fixed strategy? If yes, solve it.
      If no, say "NEEDS_DYNAMIC" and explain why.
  
  **{{attempt_static.output}} not contains "NEEDS_DYNAMIC"**
    return: {{attempt_static.output}}
  
  **{{attempt_static.output}} contains "NEEDS_DYNAMIC"**
    # Fall back to repl: only when necessary
    repl:
      language: python
      prompt: |
        Problem: {{problem}}
        Reason for dynamic approach: {{attempt_static.output}}
        
        Write Python using llm_query() to solve this dynamically.
```

This minimizes security surface by only invoking `repl:` when static patterns fail.

---

## Recommendation

**Start with Option B (No-Modification), prepare for Option C.**

### Rationale

1. **85-90% coverage is substantial.** Most real-world RLM applications use patterns that map cleanly to OpenProse's declarative constructs.

2. **Honoring user constraints.** The strong preference for no modifications is respected, while the path to full parity remains open.

3. **Learn before committing.** Building with existing constructs reveals which gaps actually matter in practice vs. theoretical concerns.

4. **Lower risk.** Avoiding code execution eliminates entire categories of security and debugging issues.

5. **Incremental path.** If `repl:` becomes necessary, it can be added as a minimal, opt-in extension rather than a core feature.

### Concrete Next Steps

1. Create a `rlm-patterns/` library with the four patterns above as `.prose` files
2. Build a "RLM to OpenProse" translation guide
3. Implement one complete example and validate it works end-to-end
4. Document limitations clearly so users know when they need something else

---

## RLM to OpenProse Mapping Reference

| RLM Concept | OpenProse Implementation |
|-------------|--------------------------|
| `llm_query()` | `session:` blocks |
| `llm_query_batched()` | `parallel for ... session:` or `pmap` |
| Recursive decomposition | Nested conditional blocks with depth tracking |
| `FINAL()` termination | `return:` statements in conditional branches |
| Programmatic loops | `parallel for` with parsed JSON arrays |
| Context passing | `context:` with interpolation `{{variable}}` |
| Conditional execution | `**condition**` blocks |
| Error handling | `try:/catch:` blocks |
| Retry logic | `retry:` property on sessions |

---

## Example: Complete `.prose` File

This demonstrates RLM-style recursive decomposition for solving complex reasoning problems:

```prose
# rlm_reasoning_engine.prose
# 
# RLM-equivalent reasoning engine using OpenProse primitives.
# Implements recursive decomposition with parallel sub-solving.

agent analyzer:
  model: sonnet
  prompt: You analyze problem complexity and determine solving strategies.

agent solver:
  model: sonnet
  prompt: You solve problems thoroughly, showing your reasoning.

agent synthesizer:
  model: sonnet
  prompt: You combine multiple solutions into coherent unified answers.

# Track recursion depth
let depth = 0
let max_depth = 3

# Main solving loop with recursive decomposition
loop until **problem is fully solved** (max: 10):
  
  # Phase 1: Analyze complexity
  let analysis = session: analyzer
    prompt: |
      Problem: {{problem}}
      Current depth: {{depth}} / {{max_depth}}
      
      Analyze this problem:
      - COMPLEXITY: SIMPLE | MODERATE | COMPLEX
      - STRATEGY: DIRECT (solve now) | DECOMPOSE (break into subproblems)
      - REASONING: Why this strategy?
      
      Use DIRECT if simple or at max depth.
  
  if **analysis indicates DIRECT strategy**:
    # Base case: solve directly
    let solution = session: solver
      prompt: |
        Solve this problem completely:
        {{problem}}
        
        Show clear step-by-step reasoning.
    
    # Verify and return
    let verification = session: analyzer
      prompt: |
        Problem: {{problem}}
        Solution: {{solution}}
        
        Is this solution correct and complete?
        VERDICT: VALID | INVALID
        ISSUES: (if any)
    
    if **verification says VALID**:
      # Done!
      let final_answer = solution
  
  else:
    # Recursive case: decompose
    let decomposition = session: analyzer
      prompt: |
        Decompose this problem into 2-4 independent subproblems:
        {{problem}}
        
        Format as JSON:
        {"subproblems": ["sub1", "sub2", ...], "synthesis_hint": "how to combine"}
    
    # Solve subproblems in parallel
    parallel for subproblem in decomposition.subproblems:
      let sub_solution = session: solver
        prompt: |
          Solve this subproblem:
          {{subproblem}}
          
          Context: Part of solving "{{problem}}"
    
    # Synthesize results
    let synthesis = session: synthesizer
      prompt: |
        Original problem: {{problem}}
        
        Subproblem solutions:
        {{sub_solutions | enumerate}}
        
        Synthesis hint: {{decomposition.synthesis_hint}}
        
        Combine into a complete solution.
    
    let final_answer = synthesis

# Output the result
session "Write final answer to stdout"
  context: final_answer
```

---

## Summary

OpenProse + Claude Code can implement the vast majority of RLM patterns today through:

1. **`session:`** for sub-LLM queries
2. **`parallel for` / `pmap`** for batched queries
3. **`repeat` with `until:`** for iterative refinement
4. **`**condition**` blocks** for branching
5. **`context:`** for state management
6. **`return:`** for early termination

The 10-15% gap (dynamic code generation) can be addressed later with a `repl:` extension if real-world usage demonstrates the need. For now, the no-modification path provides a powerful, safe, and maintainable foundation for RLM-style reasoning in OpenProse.
