# rlm.prose Limitations

## Known Substrate Differences from Python RLM

### 1. Termination Detection Mechanism

**Python RLM:** Uses regex pattern matching to detect `FINAL(...)` or `FINAL_VAR(...)` in LLM text output. Termination is triggered by pattern match.

**rlm.prose:** Uses discretion condition `**state file shows done=true**` where the VM reads the state file and evaluates the condition. Worker signals completion by setting `done: true` in state.json.

**Practical Impact:** Minimal. Both achieve deterministic termination - the worker controls when to signal done. The difference is in the detection mechanism (regex vs. file read), not in capability.

**Workaround:** None needed. The file-based approach is arguably more explicit and debuggable.

---

## Non-Issues (Clarified)

### Code Execution Model

An early review claimed "Bash Python execution ≠ exec() semantics" because Python RLM uses `exec()` with a persistent namespace while rlm.prose workers use Bash.

**Clarification:** This misunderstands the worker's capabilities. Claude Code workers have full access to:
- Python execution (not just Bash)
- Persistent state via files (equivalent to persistent namespace)
- The ability to maintain complex Python objects across iterations via pickle/JSON

The worker can write and execute Python scripts, use Python's `exec()` if needed, or maintain state however it chooses. The execution model is not limited to "Bash subprocess" - it's a full Claude Code agent with all available tools.
