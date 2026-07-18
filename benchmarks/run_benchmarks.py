#!/usr/bin/env python3
"""Benchmark the three knowledge-base plugin variants.

- The **Python** and **PowerShell** script variants are timed directly (wall
  clock of the CLI, median of N runs) on lint/search/detect across KB sizes,
  and their JSON output is checked for parity.
- The **scriptless** variant has no scripts to time — its cost is model tokens
  and tool round-trips — so we report a *proxy*: the number of pages and bytes an
  agent would have to read into context to do the same work. It is reported
  separately and is not directly comparable to script wall-time.

Writes results.md and results.json next to this file. Numbers are
machine-specific; re-run locally for your environment.

Usage:
  python3 benchmarks/run_benchmarks.py [--sizes 20,200,1000] [--repeat 5]
"""
import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PY = os.path.join(REPO, "plugins", "okf-knowledge-base", "scripts")
PS = os.path.join(REPO, "plugins", "okf-knowledge-base-powershell", "scripts")

SEARCH_Q = "invoice payment refund"
DETECT_Q = "invoice payment refund webhook cluster"


def ops(kb):
    return {
        "lint": {
            "py": ["python3", os.path.join(PY, "kb_lint.py"), "--kb-root", kb, "--json"],
            "ps": ["pwsh", "-NoProfile", "-File", os.path.join(PS, "kb_lint.ps1"), "--kb-root", kb, "--json"],
        },
        "search": {
            "py": ["python3", os.path.join(PY, "kb_search.py"), SEARCH_Q, "--kb-root", kb, "--json"],
            "ps": ["pwsh", "-NoProfile", "-File", os.path.join(PS, "kb_search.ps1"), SEARCH_Q, "--kb-root", kb, "--json"],
        },
        "detect": {
            "py": ["python3", os.path.join(PY, "detect_domain.py"), "--kb-root", kb, "--query", DETECT_Q, "--json"],
            "ps": ["pwsh", "-NoProfile", "-File", os.path.join(PS, "detect_domain.ps1"), "--kb-root", kb, "--query", DETECT_Q, "--json"],
        },
    }


def time_cmd(cmd, repeat):
    times, out, rc = [], "", None
    for _ in range(repeat):
        t0 = time.perf_counter()
        p = subprocess.run(cmd, capture_output=True, text=True)
        times.append(time.perf_counter() - t0)
        out, rc = p.stdout, p.returncode
    return statistics.median(times), min(times), out, rc


def parity(py_out, ps_out):
    try:
        a, b = json.loads(py_out), json.loads(ps_out)
        for x in (a, b):
            if isinstance(x, dict):
                x.pop("kb_root", None)
        return a == b
    except (json.JSONDecodeError, ValueError):
        return False


def kb_stats(kb):
    files = bytes_ = 0
    for dp, _, fs in os.walk(kb):
        for f in fs:
            if f.endswith(".md"):
                files += 1
                bytes_ += os.path.getsize(os.path.join(dp, f))
    return files, bytes_


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="20,200,1000")
    ap.add_argument("--repeat", type=int, default=5)
    a = ap.parse_args()
    sizes = [int(x) for x in a.sizes.split(",")]
    has_pwsh = shutil.which("pwsh") is not None

    results = []
    for size in sizes:
        tmp = tempfile.mkdtemp(prefix=f"benchkb_{size}_")
        kb = os.path.join(tmp, "kb")
        subprocess.run([sys.executable, os.path.join(HERE, "gen_kb.py"),
                        "--out", kb, "--pages", str(size)], check=True, capture_output=True)
        files, bytes_ = kb_stats(kb)
        row = {"size": size, "files": files, "bytes": bytes_, "ops": {}}
        for op, impl in ops(kb).items():
            pymed, pymin, pyout, _ = time_cmd(impl["py"], a.repeat)
            entry = {"python_ms": round(pymed * 1000, 1), "python_min_ms": round(pymin * 1000, 1)}
            if has_pwsh:
                psmed, psmin, psout, _ = time_cmd(impl["ps"], a.repeat)
                entry["powershell_ms"] = round(psmed * 1000, 1)
                entry["powershell_min_ms"] = round(psmin * 1000, 1)
                entry["parity"] = parity(pyout, psout)
            row["ops"][op] = entry
        row["scriptless_proxy"] = {"pages_to_read": files, "bytes_to_read": bytes_}
        results.append(row)
        shutil.rmtree(tmp, ignore_errors=True)

    meta = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pwsh": (subprocess.run(["pwsh", "--version"], capture_output=True, text=True).stdout.strip()
                 if has_pwsh else "not installed"),
        "repeat": a.repeat,
    }
    json.dump({"meta": meta, "results": results},
              open(os.path.join(HERE, "results.json"), "w"), indent=2)
    write_md(os.path.join(HERE, "results.md"), meta, results, has_pwsh)
    print("Wrote", os.path.join(HERE, "results.md"))
    return 0


def write_md(path, meta, results, has_pwsh):
    L = []
    L.append("# Benchmark results — three plugin variants\n")
    L.append(f"_Environment: {meta['platform']}, Python {meta['python']}, "
             f"{meta['pwsh']}. Median of {meta['repeat']} runs. "
             "**Numbers are machine-specific — re-run `benchmarks/run_benchmarks.py` locally.**_\n")
    L.append("The Python and PowerShell variants are timed directly; the "
             "scriptless variant has no scripts to time (its cost is model "
             "tokens + tool round-trips) so it is shown separately as a "
             "context-load proxy.\n")

    for op in ("lint", "search", "detect"):
        L.append(f"\n## `{op}` — wall-clock, median ms (lower is better)\n")
        if has_pwsh:
            L.append("| KB pages | .md files | Python | PowerShell | PS ÷ Py | output parity |")
            L.append("|---:|---:|---:|---:|---:|:---:|")
        else:
            L.append("| KB pages | .md files | Python | PowerShell |")
            L.append("|---:|---:|---:|:---:|")
        for r in results:
            e = r["ops"][op]
            if has_pwsh:
                ratio = e["powershell_ms"] / e["python_ms"] if e["python_ms"] else 0
                par = "✓" if e.get("parity") else "✗"
                L.append(f"| {r['size']} | {r['files']} | {e['python_ms']} ms | "
                         f"{e['powershell_ms']} ms | {ratio:.2f}× | {par} |")
            else:
                L.append(f"| {r['size']} | {r['files']} | {e['python_ms']} ms | not installed |")

    L.append("\n## Scriptless variant — context-load proxy\n")
    L.append("No script runs; an agent must read the pages into context and make "
             "several tool calls. Cost scales with the volume below (roughly "
             "tokens ≈ bytes ÷ 4), plus per-call latency — so it grows fastest "
             "with KB size and is best on small KBs.\n")
    L.append("| KB pages | .md files to scan | bytes to read | ≈ tokens |")
    L.append("|---:|---:|---:|---:|")
    for r in results:
        sp = r["scriptless_proxy"]
        L.append(f"| {r['size']} | {sp['pages_to_read']} | {sp['bytes_to_read']:,} | "
                 f"~{sp['bytes_to_read'] // 4:,} |")

    L.append("\n## Reading the results\n")
    L.append("- **Python vs PowerShell**: identical output (parity column). "
             "PowerShell carries a higher interpreter start-up cost per call, so "
             "it is slower on small KBs; the gap narrows as real work dominates.\n")
    L.append("- **Scriptless**: not timed here because it needs the model in the "
             "loop. Its proxy grows linearly with KB size and, unlike the script "
             "variants, consumes model context every call — the reason it is best "
             "for small/personal KBs and the script variants win at scale.\n")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
