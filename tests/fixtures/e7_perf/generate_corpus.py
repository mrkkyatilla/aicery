#!/usr/bin/env python3
"""Generate 100 markdown files for E7 index perf tests (deterministic seed)."""
from __future__ import annotations

import argparse
import random
from pathlib import Path

DEFAULT_COUNT = 100
SEED = 42


def generate_one(rng: random.Random, index: int) -> str:
    title = f"Perf doc {index:03d}"
    token = f"PERF_TOKEN_{index:03d}_{rng.randint(1000, 9999)}"
    body = rng.choice(
        [
            "Indexing performance validates chunking and embedding batch paths.",
            "Hybrid search combines vector similarity with workspace grep fallback.",
            "MinIO stores raw blobs for reindex and audit workflows.",
        ]
    )
    paragraphs = [f"# {title}\n", f"\nUnique marker: {token}\n\n", body + "\n"]
    for _ in range(rng.randint(2, 6)):
        paragraphs.append(f"\n{rng.choice(['Section', 'Note', 'Detail'])} {rng.randint(1, 99)}: ")
        paragraphs.append(" ".join(rng.choice(body.split()) for _ in range(rng.randint(40, 120))))
        paragraphs.append("\n")
    return "".join(paragraphs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "corpus")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    for i in range(args.count):
        path = args.out / f"doc_{i:03d}.md"
        path.write_text(generate_one(rng, i), encoding="utf-8")
    print(f"Wrote {args.count} files to {args.out}")


if __name__ == "__main__":
    main()
