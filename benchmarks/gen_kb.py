#!/usr/bin/env python3
"""Generate a synthetic OKF knowledge base for benchmarking.

Deterministic (seeded): N concept pages spread across D domains, each page with
realistic frontmatter, a body drawn from a shared vocabulary, and a cross-link to
the next page in its domain (so the bundle is broadly clean — few orphans/broken
links — and the linter does real link-resolution work).
"""
import argparse
import os
import random

VOCAB = ("invoice payment refund dunning webhook signature retry deploy cluster "
         "pipeline token session oauth vat sepa latency cache queue index shard "
         "replica backup restore metric alert throttle quota tenant region").split()


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="KB root directory to create.")
    ap.add_argument("--pages", type=int, required=True)
    ap.add_argument("--domains", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    root = a.out

    domains = [f"domain{i}" for i in range(a.domains)]
    idx = ['---\nokf_version: "0.1"\n---\n\n# Knowledge Base\n\n# Domains\n']
    for d in domains:
        idx.append(f"* [{d}]({d}/index.md) - synthetic domain {d}.\n")
    w(os.path.join(root, "index.md"), "".join(idx))
    w(os.path.join(root, "log.md"), "# Knowledge Base Log\n\nNewest first.\n")

    per = a.pages // a.domains
    for di, d in enumerate(domains):
        ddir = os.path.join(root, d)
        tags = rnd.sample(VOCAB, 3)
        w(os.path.join(ddir, "domain.md"),
          f"---\ntype: Domain\ntitle: {d}\ndescription: Synthetic domain about "
          f"{' '.join(tags)}.\nslug: {d}\ntags: [{', '.join(tags)}]\n"
          f"timestamp: 2026-07-18T00:00:00Z\n---\n\n# Scope\n{' '.join(tags)}\n")
        w(os.path.join(ddir, "raw", "index.md"), "# Raw Sources\n")

        n = per + (a.pages - per * a.domains if di == a.domains - 1 else 0)
        pages = [f"page{j}" for j in range(n)]
        lines = [f"# {d}\n\nSynthetic domain {d}.\n\n# Concepts\n"]
        for j, p in enumerate(pages):
            nxt = pages[(j + 1) % n]
            bw = rnd.sample(VOCAB, 6)
            title = f"{d} {p}"
            w(os.path.join(ddir, p + ".md"),
              f"---\ntype: Reference\ntitle: {title}\ndescription: About "
              f"{' '.join(bw[:3])}.\ntags: [{', '.join(bw[:2])}]\n"
              f"timestamp: 2026-07-18T00:00:00Z\n---\n\n# Overview\nThis page "
              f"covers {' '.join(bw)}. See [{d} {nxt}](/{d}/{nxt}.md).\n")
            lines.append(f"* [{title}]({p}.md) - About {' '.join(bw[:3])}.\n")
        lines.append("\n# Sources\n\n* [Raw sources](raw/) - snapshots.\n")
        w(os.path.join(ddir, "index.md"), "".join(lines))

    print(f"generated {a.pages} pages across {a.domains} domains at {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
