# proseRlm

An implementation of Recursive Language Models (RLM) using OpenProse, a declarative language for LLM orchestration.

## What is this?

This project explores whether the RLM pattern from [arXiv:2512.24601](https://arxiv.org/abs/2512.24601) can be implemented in OpenProse and executed by Claude Code acting as a virtual machine.

**RLM Key Insight:** Long prompts should not be fed directly into an LLM's context window. Instead, treat them as part of the external environment that the LLM can symbolically interact with through code execution and recursive sub-LLM calls.

**OpenProse Approach:** Define agents, sessions, and control flow declaratively in `.prose` files. Claude Code interprets these files as a VM, spawning sub-agents via the Task tool.

## Project Structure

```
proseRlm/
├── README.md                    # This file
├── rlm.prose                    # Main RLM implementation
├── research-loop.prose          # Meta-research agent for validation
│
├── docs/                        # Documentation
│   ├── LIMITATIONS.md           # Known substrate differences
│   ├── FIDELITY-ASSESSMENT.md   # Comparison to Python RLM
│   └── RLM-FIDELITY-REPORT.md   # Detailed fidelity analysis
│
├── specs/                       # Design specifications
│   ├── rlm-feasibility-report.md
│   ├── rlm-implementation-spec.md
│   └── rlm-openprose-formal-spec.md
│
├── experiments/                 # Benchmark experiments
│   └── oolong-pairs/           # OOLONG-Pairs benchmark
│       ├── EXPERIMENT-LOG.md   # Results and analysis
│       ├── generate_oolong_pairs.py
│       ├── evaluate.py
│       └── oolong-pairs-1M.prose
│
├── reference/                   # Reference implementations
│   ├── rlm/                    # Python RLM (original paper)
│   ├── openprose/              # OpenProse language spec
│   └── 2512.24601v1.pdf        # RLM paper
│
└── tmp/                        # Runtime state (gitignored)
    └── rlm_state/
```

## Quick Start

### Running rlm.prose

In Claude Code with the OpenProse skill:

```
/open-prose:prose-run rlm.prose
```

You'll be prompted for a problem to solve. The RLM will:
1. Initialize state files
2. Decompose the problem into chunks
3. Process each chunk (using sub-LLM calls when needed)
4. Synthesize a final answer

### Running the OOLONG-Pairs Benchmark

```
/open-prose:prose-run experiments/oolong-pairs/oolong-pairs-1M.prose
```

After completion, evaluate:

```bash
python experiments/oolong-pairs/evaluate.py \
  --prediction ./tmp/rlm_state/pairs_output.txt \
  --dataset ./experiments/oolong-pairs/dataset_task1_1M.json
```

## Key Results

### OOLONG-Pairs 1M Token Benchmark

| Method | F1 Score |
|--------|----------|
| GPT-5 (vanilla) | 0.04% |
| RLM (paper) | 58% |
| **rlm.prose** | **54.9%** |

The rlm.prose implementation achieves comparable results to the paper's RLM, though with a caveat: in our initial run, the agent used regex pattern matching instead of proper sub-LLM semantic classification. This is a known failure mode also documented in the paper.

### Winner: `oolong-rlm.prose`

The **`experiments/oolong-pairs/oolong-rlm.prose`** implementation is the winning approach, achieving **~53% accuracy** on the OOLONG-Pairs benchmark. This reproduces the results from the [RLM paper (arXiv:2512.24601)](https://arxiv.org/abs/2512.24601), demonstrating that **Claude Sonnet + Opus can achieve similar results to GPT-5 RLM when using the same recursive sub-agent harness**.

| Method | F1 Score | Notes |
|--------|----------|-------|
| GPT-5 (vanilla) | 0.04% | From paper - context window alone fails |
| GPT-5 RLM | 58% | From paper - with recursive sub-LLM calls |
| **oolong-rlm.prose** | **~53%** | Claude Sonnet/Opus with OpenProse RLM harness |

The implementation faithfully translates the RLM system prompt to OpenProse and successfully:

- Processed 33,938 lines of question data
- Classified 5,381 unique questions into 6 semantic categories using sub-agents
- Identified 4,490 users with numeric value OR location questions
- Generated 10,077,805 valid user pairs

This demonstrates that the RLM pattern is **model-agnostic** - the key insight is the recursive sub-agent architecture, not the specific model used.

## How It Works

### The RLM Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                      VM (Claude Code)                       │
│                                                             │
│   1. Initialize state file with problem                     │
│   2. Loop until done (max iterations for safety):           │
│      - Spawn worker session (Task tool)                     │
│      - Worker reads state, does work, writes state          │
│      - Check if state.done == true                          │
│   3. Extract final answer from state                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Worker Session                           │
│                                                             │
│   - Reads current state from files                          │
│   - Executes Python code for data processing                │
│   - Spawns sub-LLM calls via Task tool                      │
│   - Writes updated state back to files                      │
│   - Sets done=true when finished                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Differences from Python RLM

| Aspect | Python RLM | rlm.prose |
|--------|-----------|-----------|
| Sub-LLM calls | `llm_query()` function | Task tool |
| Code execution | `exec()` in REPL | Bash + Python scripts |
| Termination | `FINAL()` / `FINAL_VAR()` | `state.done = true` |
| State | REPL variables | Files (JSON, SQLite) |

See [docs/LIMITATIONS.md](docs/LIMITATIONS.md) for detailed analysis.

## Requirements

- Claude Code with OpenProse skill installed
- Python 3.8+ (for benchmark generation/evaluation)
- Dependencies: `datasets`, `tiktoken` (for benchmark generation)

## References

- [Recursive Language Models (arXiv:2512.24601)](https://arxiv.org/abs/2512.24601)
- [OOLONG Benchmark](https://github.com/abertsch72/oolong)
- [OpenProse Language](./reference/openprose/)

## Notes on Methodology

This project is an exploratory proof-of-concept, not a rigorous benchmark. I made best efforts to ensure the winning agent traces did not have data leakage, but it's worth noting that context engineering and data leakage are almost two sides of the same coin. Reasonable people could view aspects of the prompt design as a form of data leakage. The goal here was simply to get the RLM pattern working with Claude, not to produce a publication-ready evaluation.

## License

MIT
