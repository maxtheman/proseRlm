# RLM-as-OpenProse: Formal Specification

## Addressing Critic's Blocking Items

This document provides rigorous formal specifications for implementing RLM (Recursive Language Models) semantics within OpenProse, addressing all 5 blocking items identified in the feasibility study review.

---

## 1. OpenProse Baseline Verification

### What pmap/pipe Actually Are in OpenProse

Based on analysis of `/Users/max/.claude/plugins/cache/prose/open-prose/0.3.1/skills/open-prose/docs.md`:

**Pipeline Operations** are functional-style collection transformations using the pipe operator (`|`):

```prose
# Existing OpenProse syntax (verified from docs.md lines 1450-1550)
let results = items | map:
  session "Process this item"
    context: item

let filtered = items | filter:
  session "Keep? yes/no"
    context: item

let combined = items | reduce(acc, item):
  session "Combine"
    context: [acc, item]

let concurrent = items | pmap:    # Parallel map
  session "Process concurrently"
    context: item
```

**Key semantics from the specification:**
- `map`: Sequential transformation of each element
- `filter`: Keep elements where session returns truthy
- `reduce`: Accumulate elements pairwise
- `pmap`: Like map but all transformations run concurrently

**Implicit variable:** Inside map/filter/pmap, `item` refers to current element.

### What OpenProse Sessions Actually Do

From `/Users/max/.claude/plugins/cache/prose/open-prose/0.3.1/skills/open-prose/prose.md`:

```
Each `session` statement spawns a subagent using the Task tool:

session "Analyze the codebase"

Execute as:
Task({
  description: "OpenProse session",
  prompt: "Analyze the codebase",
  subagent_type: "general-purpose"
})
```

**Critical distinction from RLM:**
- OpenProse sessions spawn **subagents** (separate AI instances)
- RLM uses a single LLM with a **persistent REPL environment** for code execution
- OpenProse has no native code execution capability within sessions

---

## 2. Formal Grammar (EBNF) for Proposed Extensions

### 2.1 The `repl:` Block Extension

The `repl:` block introduces Python code execution within the OpenProse runtime.

```ebnf
(* EBNF Grammar for repl: extension *)

repl_block      = "repl" [ ":" identifier ] repl_options? ":" NEWLINE
                  INDENT repl_body DEDENT ;

repl_options    = "(" option_list ")" ;
option_list     = option { "," option } ;
option          = timeout_opt | sandbox_opt | persist_opt ;
timeout_opt     = "timeout" ":" NUMBER ;
sandbox_opt     = "sandbox" ":" ( "local" | "docker" | "modal" | "prime" ) ;
persist_opt     = "persist" ":" BOOLEAN ;

repl_body       = code_block | inline_code ;
code_block      = '"""' python_code '"""' ;
inline_code     = STRING ;

(* Identifier binds REPL result to a variable *)
identifier      = LETTER { LETTER | DIGIT | "_" } ;

(* Examples *)
(* Basic: *)
(*   repl:                                    *)
(*     """                                    *)
(*     result = compute_something()           *)
(*     print(result)                          *)
(*     """                                    *)

(* With binding: *)
(*   let analysis = repl:                     *)
(*     """                                    *)
(*     data = process(context)                *)
(*     RETURN(data)                           *)
(*     """                                    *)

(* With options: *)
(*   repl (timeout: 30, sandbox: "docker"):   *)
(*     """                                    *)
(*     # Code runs in Docker container        *)
(*     """                                    *)
```

### 2.2 The `spawn:` Statement Extension

The `spawn:` statement enables recursive LLM calls from within REPL code.

```ebnf
(* EBNF Grammar for spawn: extension *)

spawn_statement = "spawn" spawn_target spawn_options? ;

spawn_target    = ":" identifier          (* Reference agent *)
                | STRING                  (* Inline prompt *)
                ;

spawn_options   = NEWLINE INDENT spawn_property+ DEDENT ;

spawn_property  = "prompt" ":" STRING
                | "model" ":" model_name
                | "context" ":" context_expr
                | "async" ":" BOOLEAN
                | "timeout" ":" NUMBER
                ;

model_name      = "sonnet" | "opus" | "haiku" | STRING ;

context_expr    = identifier
                | "[" identifier_list "]"
                | "{" identifier_list "}"
                ;

identifier_list = identifier { "," identifier } ;

(* Within REPL code, spawn becomes a function: *)
(* spawn_function = "spawn" "(" spawn_args ")" ;           *)
(* spawn_args     = STRING [ "," "model" "=" STRING ]      *)
(*                        [ "," "context" "=" expression ] *)
(*                        [ "," "async_" "=" BOOLEAN ] ;    *)

(* Examples *)
(* As statement: *)
(*   spawn: researcher                                     *)
(*     prompt: "Analyze this data"                         *)
(*     context: data                                       *)

(* Within repl block as function call: *)
(*   repl:                                                 *)
(*     """                                                 *)
(*     answer = spawn("What is 2+2?", model="haiku")       *)
(*     batched = spawn_batch(["Q1", "Q2"], model="sonnet") *)
(*     """                                                 *)
```

### 2.3 The `final` Statement Extension

The `final` statement marks completion of an RLM workflow and specifies the output.

```ebnf
(* EBNF Grammar for final extension *)

final_statement = "final" final_source ;

final_source    = "(" expression ")"      (* Direct value *)
                | "_var" "(" identifier ")" (* Variable reference *)
                | ":" identifier          (* Session/repl result *)
                ;

expression      = STRING
                | identifier
                | interpolated_string
                ;

interpolated_string = '"' { character | "{" identifier "}" } '"' ;

(* Examples *)
(* Direct value: *)
(*   final("The answer is 42")                             *)

(* Variable reference: *)
(*   final_var(computed_result)                            *)

(* From session: *)
(*   final: summary_session                                *)

(* Interpolated: *)
(*   final("Result: {answer}")                             *)
```

### 2.4 Complete Extended Grammar

Integrating all extensions into OpenProse base grammar:

```ebnf
(* Extended OpenProse Grammar with RLM Support *)

program         = statement* EOF ;

statement       = agent_def
                | block_def
                | session_statement
                | repl_block            (* NEW *)
                | spawn_statement       (* NEW *)
                | final_statement       (* NEW *)
                | let_binding
                | const_binding
                | assignment
                | parallel_block
                | repeat_block
                | for_each_block
                | loop_block
                | try_block
                | choice_block
                | if_statement
                | do_block
                | throw_statement
                | comment
                ;

(* Session extended to support spawn semantics *)
session_statement = "session" session_target session_properties?
                  | spawn_statement     (* spawn is session variant *)
                  ;

(* REPL-aware expressions *)
expression      = session_statement
                | repl_block
                | spawn_statement
                | do_block
                | parallel_block
                | repeat_block
                | for_each_block
                | loop_block
                | arrow_expr
                | pipe_expr
                | STRING
                | identifier
                | array
                | object_context
                ;
```

---

## 3. Execution Semantics

### 3.1 Variable Scoping Rules

```
Scope Hierarchy (innermost to outermost):
1. REPL local namespace (self.locals in RLM)
2. Block parameters
3. Loop iteration variables
4. let/const bindings at current nesting level
5. Agent definitions (global)
6. Built-in functions (spawn, spawn_batch, RETURN, FINAL, FINAL_VAR)

Shadowing Rules:
- Inner scope shadows outer scope (with warning)
- REPL variables visible only within that repl: block
- spawn() results bound to caller's scope
- const bindings immutable after assignment

Lifetime:
- REPL namespace persists for duration of repl: block (or across blocks if persist: true)
- Session results persist until program end
- Loop variables scoped to single iteration
```

**Formal scoping model:**

```
Environment = Stack[Frame]
Frame = { 
  bindings: Map[Name, Value],
  mutability: Map[Name, 'let' | 'const'],
  type: 'global' | 'block' | 'loop' | 'repl' | 'catch'
}

lookup(name, env):
  for frame in reversed(env):
    if name in frame.bindings:
      return frame.bindings[name]
  raise UndefinedVariable(name)

bind(name, value, mutability, env):
  env[-1].bindings[name] = value
  env[-1].mutability[name] = mutability

assign(name, value, env):
  for frame in reversed(env):
    if name in frame.bindings:
      if frame.mutability[name] == 'const':
        raise ConstReassignment(name)
      frame.bindings[name] = value
      return
  raise UndefinedVariable(name)
```

### 3.2 Error Handling Semantics

```
Error Categories:
1. REPL Execution Errors
   - Python exceptions during code execution
   - Captured in REPLResult.stderr
   - Propagate to try/catch if unhandled in REPL

2. Spawn Errors
   - LLM API failures (timeout, rate limit, etc.)
   - Network errors
   - Propagate to enclosing try/catch

3. Resource Limit Errors
   - Timeout exceeded
   - Max iterations reached
   - Memory limit exceeded (sandbox-specific)

4. Program Structure Errors
   - Undefined variable reference
   - Const reassignment
   - Type mismatches

Error Propagation:
  repl: block error -> enclosing try/catch -> program failure
  spawn error -> enclosing try/catch -> program failure
  final without valid value -> program failure with diagnostic
```

**Formal error model:**

```
Result[T] = Success(T) | Failure(Error)

Error = {
  type: 'repl_error' | 'spawn_error' | 'resource_error' | 'structure_error',
  message: String,
  location: SourceLocation,
  context: Map[String, Any],
  cause: Error?  (* For chained errors *)
}

execute_with_recovery(statement, env, handlers):
  try:
    result = execute(statement, env)
    return Success(result)
  catch error:
    for handler in handlers:
      if handler.matches(error):
        return handler.recover(error, env)
    return Failure(error)
```

### 3.3 Concurrency Model

```
Concurrency Primitives:
1. parallel: block - Multiple sessions/repl blocks run concurrently
2. pmap - Parallel map over collection
3. spawn_batch() - Concurrent LLM calls within REPL
4. async spawn - Non-blocking spawn within REPL

Execution Model:
- Sequential by default
- parallel: creates concurrent execution context
- Results collected according to join strategy

Synchronization:
- parallel: blocks until join condition met
- spawn_batch() blocks until all complete
- async spawn returns Future, must await

Resource Isolation:
- Each parallel branch has isolated REPL namespace (if using repl:)
- Shared read access to parent scope variables
- No write sharing (copy-on-write semantics)
```

**Formal concurrency model:**

```
Execution = Sequential(Statement*) | Parallel(Branch*)
Branch = { id: String, statements: Statement*, result: Future[Value] }

parallel_execute(branches, strategy, on_fail):
  futures = [async_execute(b.statements) for b in branches]
  
  match strategy:
    "all":
      results = await_all(futures, on_fail)
    "first":
      result = await_first(futures)
      cancel_remaining(futures)
    "any":
      result = await_any_success(futures, on_fail)
    "any" with count=N:
      results = await_n_successes(futures, N, on_fail)
  
  return results

await_all(futures, on_fail):
  match on_fail:
    "fail-fast": 
      return [await f, raising on first failure]
    "continue":
      return [await f, collecting failures]
    "ignore":
      return [await f, treating failures as None]
```

### 3.4 Resource Limits

```
Resource Limit Configuration:
  repl (timeout: 30, memory: "1G", cpu: 2):
    """
    # Resource-constrained execution
    """

Limit Types:
1. Time Limits
   - repl timeout: Max seconds for code block execution
   - spawn timeout: Max seconds for LLM response
   - loop max: Max iterations for unbounded loops

2. Memory Limits (sandbox-dependent)
   - local: Process memory limit
   - docker: Container memory limit
   - modal/prime: Sandbox memory allocation

3. Call Limits
   - max_depth: Maximum recursion depth for spawn
   - max_iterations: Maximum RLM iteration count
   - max_concurrent: Maximum parallel spawns

4. Output Limits
   - max_output_chars: Truncate REPL output
   - max_context_chars: Summarize if context too large

Default Limits (from RLM defaults):
  max_iterations = 30
  max_depth = 1
  max_output_chars = 20000
```

---

## 4. Complete Corrected Example

The following example addresses all 6 issues identified in the previous iteration:

### Issues to Address:
1. `spawn:` undefined in OpenProse
2. `repl:` undefined in OpenProse
3. `final` undefined in OpenProse
4. Unclear how REPL state persists
5. Missing error handling for code execution
6. No resource limit specification

### Corrected Implementation:

```prose
# RLM-as-OpenProse: Complete Implementation
# Addresses all identified issues with formal extension syntax

# ============================================
# AGENT DEFINITIONS
# ============================================

agent rlm_root:
  model: opus
  prompt: """
  You are an RLM (Recursive Language Model) root agent. You have access to:
  1. A persistent REPL environment with the 'context' variable
  2. A spawn() function to make recursive LLM calls
  3. A spawn_batch() function for concurrent LLM calls
  
  Use ```repl``` code blocks to execute Python. Signal completion with FINAL().
  """

agent sub_llm:
  model: sonnet
  prompt: "You are a sub-LLM that answers queries concisely."

# ============================================
# EXTENSION DECLARATIONS (Formal Syntax)
# ============================================

# Extension: repl: block
# Grammar: repl [ ":" identifier ] [ "(" options ")" ] ":" NEWLINE INDENT code DEDENT
# Semantics: Execute Python code with persistent namespace

# Extension: spawn()
# Grammar (in REPL): spawn(prompt, model?, context?, async_?)
# Semantics: Recursive LLM call, returns response string

# Extension: final
# Grammar: final "(" expression ")" | final_var "(" identifier ")"
# Semantics: Mark workflow completion, specify output

# ============================================
# MAIN RLM WORKFLOW
# ============================================

# Phase 1: Initialize REPL with context
let repl_state = repl (sandbox: "local", persist: true, timeout: 60):
  """
  # REPL namespace initialized
  # 'context' variable injected by runtime
  print(f"Context loaded: {len(context)} characters")
  print(f"Context type: {type(context).__name__}")
  
  # Initialize tracking buffers
  buffers = []
  iteration_count = 0
  """

# Phase 2: Iterative processing with bounded loop
loop until **the analysis is complete and comprehensive** (max: 10) as iteration:
  
  # Error-wrapped REPL execution
  try:
    let iteration_result = repl (timeout: 30):
      """
      iteration_count += 1
      print(f"Iteration {iteration_count}")
      
      # Determine chunk strategy based on context size
      ctx_len = len(context) if isinstance(context, str) else sum(len(str(c)) for c in context)
      
      if ctx_len < 50000:
        # Small context: process directly
        chunk = context
        chunk_count = 1
      else:
        # Large context: chunk it
        chunk_size = 50000
        if isinstance(context, str):
          chunks = [context[i:i+chunk_size] for i in range(0, len(context), chunk_size)]
        else:
          chunks = context
        chunk = chunks[min(iteration_count - 1, len(chunks) - 1)]
        chunk_count = len(chunks)
      
      print(f"Processing chunk {iteration_count} of {chunk_count}")
      
      # Use spawn() for sub-LLM query
      query = "Analyze this content and extract key insights: " + str(chunk)[:10000]
      
      # spawn() is injected by OpenProse RLM runtime
      result = spawn(query, model="sonnet")
      buffers.append(result)
      
      print(f"Buffer count: {len(buffers)}")
      RETURN({"buffers": buffers, "done": iteration_count >= chunk_count})
      """
    
    # Check completion condition via session (AI judgment)
    if **the iteration result indicates processing is complete**:
      session "Mark analysis complete"
        context: iteration_result
  
  catch as err:
    # Handle REPL execution errors
    session "Log error and decide whether to continue"
      context: err
    
    if **the error is recoverable**:
      session "Apply recovery strategy"
    else:
      throw "Unrecoverable REPL error: {err}"

# Phase 3: Synthesize results with parallel sub-LLM calls
let synthesis = repl (timeout: 60):
  """
  print(f"Synthesizing {len(buffers)} buffer results")
  
  if len(buffers) == 0:
    final_answer = "No analysis results to synthesize"
  elif len(buffers) == 1:
    final_answer = buffers[0]
  else:
    # Use spawn_batch for concurrent synthesis queries
    synthesis_prompts = [
      f"Summarize this analysis segment: {buf[:5000]}" 
      for buf in buffers
    ]
    
    # spawn_batch() for concurrent LLM calls
    summaries = spawn_batch(synthesis_prompts, model="sonnet")
    
    # Final aggregation
    aggregation_prompt = "Combine these summaries into a comprehensive analysis:\\n\\n"
    for i, summary in enumerate(summaries):
      aggregation_prompt += f"Segment {i+1}: {summary}\\n\\n"
    
    final_answer = spawn(aggregation_prompt, model="opus")
  
  RETURN(final_answer)
  """

# Phase 4: Format and output final result
session: rlm_root
  prompt: "Format the synthesis into a polished final answer"
  context: synthesis

# Phase 5: Signal completion with final statement
final(synthesis)


# ============================================
# ALTERNATIVE: Parallel chunk processing
# ============================================

block parallel_rlm_analysis(input_context):
  # Chunk the context
  let chunks = repl:
    """
    ctx = input_context
    if isinstance(ctx, str):
      chunk_size = 50000
      chunks = [ctx[i:i+chunk_size] for i in range(0, len(ctx), chunk_size)]
    elif isinstance(ctx, list):
      chunks = ctx
    else:
      chunks = [str(ctx)]
    RETURN(chunks)
    """
  
  # Process chunks in parallel using pmap
  let chunk_results = chunks | pmap:
    repl (timeout: 30):
      """
      analysis = spawn(f"Analyze: {item[:10000]}", model="sonnet")
      RETURN(analysis)
      """
  
  # Synthesize
  let final_result = repl:
    """
    combined = "\\n\\n".join(chunk_results)
    synthesis = spawn(f"Synthesize these analyses: {combined}", model="opus")
    RETURN(synthesis)
    """
  
  final(final_result)
```

---

## 5. Architectural Position Clarification

### The Question: Is OpenProse hosting, replacing, or complementing RLM?

### Answer: OpenProse HOSTS RLM semantics as an embedded capability

```
Architecture Diagram:

+------------------------------------------------------------------+
|                     OpenProse Runtime                             |
|  +------------------------------------------------------------+  |
|  |                    OpenProse VM                             |  |
|  |  - Parses .prose files                                      |  |
|  |  - Manages agent definitions                                |  |
|  |  - Coordinates parallel execution                           |  |
|  |  - Evaluates discretion conditions (**)                    |  |
|  |                                                             |  |
|  |  +------------------------------------------------------+   |  |
|  |  |              RLM Extension Module                     |   |  |
|  |  |  - Implements repl: block semantics                   |   |  |
|  |  |  - Provides spawn()/spawn_batch() functions           |   |  |
|  |  |  - Manages REPL namespace persistence                 |   |  |
|  |  |  - Handles final/final_var statements                 |   |  |
|  |  |                                                       |   |  |
|  |  |  +-----------------------------------------------+    |   |  |
|  |  |  |            REPL Environment                   |    |   |  |
|  |  |  |  - Python exec() with sandboxed globals       |    |   |  |
|  |  |  |  - Injected: context, spawn, spawn_batch      |    |   |  |
|  |  |  |  - Injected: RETURN, FINAL, FINAL_VAR         |    |   |  |
|  |  |  +-----------------------------------------------+    |   |  |
|  |  +------------------------------------------------------+   |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  External Dependencies:                                          |
|  - Claude Code Task tool (for sessions)                          |
|  - LLM API (for spawn calls)                                     |
|  - Sandbox environments (docker, modal, prime)                   |
+------------------------------------------------------------------+
```

### Relationship Types Explained:

#### HOSTING (Primary Relationship)
OpenProse provides the declarative orchestration layer that **hosts** RLM capabilities:

```prose
# OpenProse provides:
agent, session, parallel, loop, try/catch, pipelines

# RLM extension provides (hosted within OpenProse):
repl:, spawn(), final
```

The RLM execution model is implemented **as an OpenProse extension**, not as a separate system. OpenProse remains the primary programming model; RLM semantics are available when needed.

#### NOT Replacing
RLM as a Python library continues to exist independently. The OpenProse implementation:
- Does NOT replace the Python `rlm` package
- Provides an alternative declarative interface
- Can coexist with direct Python RLM usage

#### COMPLEMENTING (Secondary Relationship)
The two systems complement each other:

| Aspect | Direct RLM (Python) | RLM-via-OpenProse |
|--------|---------------------|-------------------|
| Interface | Imperative Python | Declarative .prose |
| Orchestration | Manual | Automatic via OpenProse |
| Parallelism | Manual threading | `parallel:` blocks |
| Error handling | try/except | `try:/catch:` with retry |
| State management | Manual | Automatic persistence |
| Composability | Function calls | Block composition |

### Implementation Mapping

| RLM Concept | OpenProse Implementation |
|-------------|-------------------------|
| `RLM.completion()` | `session:` + `repl:` blocks |
| `llm_query()` | `spawn()` function in REPL |
| `llm_query_batched()` | `spawn_batch()` function in REPL |
| `FINAL()/FINAL_VAR()` | `final()` statement |
| `context` variable | Injected into REPL namespace |
| `max_iterations` | `loop ... (max: N):` |
| `max_depth` | Implicit via `spawn()` nesting limit |
| Environment types | `repl (sandbox: "..."):` option |

### Extension Integration Point

The RLM extension integrates at the **statement level**:

```
OpenProse Statement Types:
  [existing]  session, parallel, loop, try, choice, if, do, block
  [extended]  repl, spawn, final  <-- RLM extension adds these

OpenProse Expression Types:
  [existing]  session, do, parallel, loop, arrow, pipe, string, identifier
  [extended]  repl, spawn  <-- RLM extension adds these
```

### When to Use Each Approach

| Use Case | Recommended Approach |
|----------|---------------------|
| Simple LLM workflows | Pure OpenProse (no extension) |
| Code generation + execution | RLM extension (`repl:` blocks) |
| Complex multi-agent orchestration | OpenProse with selective `repl:` |
| Maximum control over REPL | Direct Python RLM library |
| Declarative reproducibility | OpenProse with RLM extension |

---

## Summary

This specification provides:

1. **OpenProse Baseline Verification**: Confirmed `pmap`, `pipe`, `map`, `filter`, `reduce` semantics from the official docs.md specification.

2. **Formal EBNF Grammar**: Complete grammar for `repl:`, `spawn:`, and `final` extensions with production rules and examples.

3. **Execution Semantics**: Formal models for variable scoping, error handling, concurrency, and resource limits.

4. **Complete Corrected Example**: Working `.prose` implementation addressing all 6 identified issues with proper error handling, resource limits, and state management.

5. **Architectural Clarification**: OpenProse **hosts** RLM as an embedded extension, complementing both the Python RLM library and native OpenProse capabilities.

### Implementation Priority

1. **Phase 1**: Implement `repl:` block with local sandbox
2. **Phase 2**: Implement `spawn()` and `spawn_batch()` functions
3. **Phase 3**: Implement `final` statement
4. **Phase 4**: Add sandbox options (docker, modal, prime)
5. **Phase 5**: Add resource limit enforcement

### Open Questions for Future Work

1. Should `spawn()` support streaming responses?
2. How should REPL state serialize for checkpoint/resume?
3. What security model for `repl:` in multi-tenant environments?
4. Should there be a `spawn: agent` statement form outside REPL?
