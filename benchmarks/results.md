# Benchmark results — three plugin variants

_Environment: Linux-6.18.5-x86_64-with-glibc2.39, Python 3.11.15, PowerShell 7.6.3. Median of 5 runs. **Numbers are machine-specific — re-run `benchmarks/run_benchmarks.py` locally.**_

The Python and PowerShell variants are timed directly; the scriptless variant has no scripts to time (its cost is model tokens + tool round-trips) so it is shown separately as a context-load proxy.


## `lint` — wall-clock, median ms (lower is better)

| KB pages | .md files | Python | PowerShell | PS ÷ Py | output parity |
|---:|---:|---:|---:|---:|:---:|
| 20 | 37 | 45.4 ms | 914.2 ms | 20.14× | ✓ |
| 200 | 217 | 63.5 ms | 1728.1 ms | 27.21× | ✓ |
| 1000 | 1017 | 95.9 ms | 4783.8 ms | 49.88× | ✓ |

## `search` — wall-clock, median ms (lower is better)

| KB pages | .md files | Python | PowerShell | PS ÷ Py | output parity |
|---:|---:|---:|---:|---:|:---:|
| 20 | 37 | 39.6 ms | 947.9 ms | 23.94× | ✓ |
| 200 | 217 | 63.7 ms | 2026.2 ms | 31.81× | ✓ |
| 1000 | 1017 | 167.4 ms | 5483.9 ms | 32.76× | ✓ |

## `detect` — wall-clock, median ms (lower is better)

| KB pages | .md files | Python | PowerShell | PS ÷ Py | output parity |
|---:|---:|---:|---:|---:|:---:|
| 20 | 37 | 37.3 ms | 816.7 ms | 21.90× | ✓ |
| 200 | 217 | 42.5 ms | 841.4 ms | 19.80× | ✓ |
| 1000 | 1017 | 40.9 ms | 817.7 ms | 19.99× | ✓ |

## Scriptless variant — context-load proxy

No script runs; an agent must read the pages into context and make several tool calls. Cost scales with the volume below (roughly tokens ≈ bytes ÷ 4), plus per-call latency — so it grows fastest with KB size and is best on small KBs.

| KB pages | .md files to scan | bytes to read | ≈ tokens |
|---:|---:|---:|---:|
| 20 | 37 | 8,193 | ~2,048 |
| 200 | 217 | 65,032 | ~16,258 |
| 1000 | 1017 | 321,258 | ~80,314 |

## Reading the results

- **Python vs PowerShell**: identical output (parity column). PowerShell carries a higher interpreter start-up cost per call, so it is slower on small KBs; the gap narrows as real work dominates.

- **Scriptless**: not timed here because it needs the model in the loop. Its proxy grows linearly with KB size and, unlike the script variants, consumes model context every call — the reason it is best for small/personal KBs and the script variants win at scale.

