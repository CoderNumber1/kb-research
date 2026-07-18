# Benchmark results — three plugin variants

_Environment: Linux-6.18.5-x86_64-with-glibc2.39, Python 3.11.15, PowerShell 7.6.3. Median of 5 runs. **Numbers are machine-specific — re-run `benchmarks/run_benchmarks.py` locally.**_

The Python and PowerShell variants are timed directly; the scriptless variant has no scripts to time (its cost is model tokens + tool round-trips) so it is shown separately as a context-load proxy.


## `lint` — wall-clock, median ms (lower is better)

| KB pages | .md files | Python | PowerShell | PS ÷ Py | output parity |
|---:|---:|---:|---:|---:|:---:|
| 20 | 37 | 74.9 ms | 1192.8 ms | 15.93× | ✓ |
| 200 | 217 | 63.9 ms | 2085.1 ms | 32.63× | ✓ |
| 1000 | 1017 | 135.4 ms | 4677.8 ms | 34.55× | ✓ |

## `search` — wall-clock, median ms (lower is better)

| KB pages | .md files | Python | PowerShell | PS ÷ Py | output parity |
|---:|---:|---:|---:|---:|:---:|
| 20 | 37 | 48.1 ms | 1271.9 ms | 26.44× | ✓ |
| 200 | 217 | 77.7 ms | 2219.0 ms | 28.56× | ✓ |
| 1000 | 1017 | 163.9 ms | 5774.4 ms | 35.23× | ✓ |

## `detect` — wall-clock, median ms (lower is better)

| KB pages | .md files | Python | PowerShell | PS ÷ Py | output parity |
|---:|---:|---:|---:|---:|:---:|
| 20 | 37 | 49.5 ms | 964.0 ms | 19.47× | ✓ |
| 200 | 217 | 43.7 ms | 851.0 ms | 19.47× | ✓ |
| 1000 | 1017 | 41.7 ms | 784.0 ms | 18.80× | ✓ |

## `analyze` — wall-clock, median ms (lower is better)

| KB pages | .md files | Python | PowerShell | PS ÷ Py | output parity |
|---:|---:|---:|---:|---:|:---:|
| 20 | 37 | 47.7 ms | 1256.4 ms | 26.34× | ✓ |
| 200 | 217 | 138.1 ms | 4632.9 ms | 33.55× | ✓ |
| 1000 | 1017 | 429.1 ms | 9512.1 ms | 22.17× | ✓ |

## Scriptless variant — context-load proxy

No script runs; an agent must read the pages into context and make several tool calls. Cost scales with the volume below (roughly tokens ≈ bytes ÷ 4), plus per-call latency — so it grows fastest with KB size and is best on small KBs.

| KB pages | .md files to scan | bytes to read | ≈ tokens |
|---:|---:|---:|---:|
| 20 | 37 | 8,793 | ~2,198 |
| 200 | 217 | 71,332 | ~17,833 |
| 1000 | 1017 | 354,158 | ~88,539 |

## Reading the results

- **Python vs PowerShell**: identical output (parity column). PowerShell carries a higher interpreter start-up cost per call, so it is slower on small KBs; the gap narrows as real work dominates.

- **Scriptless**: not timed here because it needs the model in the loop. Its proxy grows linearly with KB size and, unlike the script variants, consumes model context every call — the reason it is best for small/personal KBs and the script variants win at scale.

