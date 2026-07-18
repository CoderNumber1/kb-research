# Benchmarks

Compare the three plugin variants — Python scripts, PowerShell scripts, and
scriptless — on the read-heavy operations (`lint`, `search`, `detect`,
`analyze`) across knowledge bases of increasing size.

## Run

```bash
python3 benchmarks/run_benchmarks.py                 # sizes 20,200,1000; 5 runs each
python3 benchmarks/run_benchmarks.py --sizes 50,500 --repeat 10
```

Requires Python 3. If `pwsh` (PowerShell 7+) is on `PATH`, the PowerShell columns
are filled and its output is checked for parity against Python; otherwise those
columns are skipped. Results are written to `results.md` and `results.json`.

## What is measured

- **Python** and **PowerShell** variants are timed directly — wall-clock of the
  CLI, median of N runs — and their JSON output is compared for **parity** (they
  must be identical; the suite enforces this too).
- The **scriptless** variant has no script to time; its real cost is model tokens
  and tool round-trips. So it is reported as a **context-load proxy**: the pages
  and bytes an agent would read into context to do the same work (tokens ≈
  bytes ÷ 4). This is deliberately not presented as a wall-time — it is not
  comparable to a script invocation.

## How the KB is generated

`gen_kb.py` builds a deterministic synthetic bundle: `--pages` concept pages
spread across `--domains` domains, each page with realistic frontmatter, a body
drawn from a shared vocabulary, and a cross-link to the next page in its domain
(so the linter does genuine link-resolution and orphan work).

## Caveats

- **Numbers are machine-specific.** Absolute timings depend on CPU, disk, and
  interpreter start-up; re-run locally before drawing conclusions. `results.md`
  in this repo is one sample run (see its header for the environment).
- Per-call interpreter start-up dominates small KBs (PowerShell's is larger than
  Python's), which is a real cost since each skill invocation spawns a fresh
  process. The gap narrows as actual work grows.
- The scriptless proxy is a lower bound on its cost — it ignores reasoning tokens
  and multi-step tool latency.
