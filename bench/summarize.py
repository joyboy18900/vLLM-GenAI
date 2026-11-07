#!/usr/bin/env python3
"""Make a Markdown table from the raw `vllm bench serve` results.

    python3 bench/summarize.py baseline

Reads bench/results/<label>/<workload>_c<N>.json. Every number comes from those files.
The table is printed and saved as bench/results/<label>/summary.md.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
COLUMNS = [
    ("workload", None), ("conc", None),
    ("TTFT p50 (ms)", "median_ttft_ms"), ("TTFT p99 (ms)", "p99_ttft_ms"),
    ("TPOT p50 (ms)", "median_tpot_ms"), ("TPOT p99 (ms)", "p99_tpot_ms"),
    ("out tok/s", "output_throughput"), ("req/s", "request_throughput"),
    ("done", "completed"), ("failed", "failed"),
]


def fmt(value):
    if value is None:
        return "-"
    return f"{value:.1f}" if isinstance(value, float) else str(value)


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: summarize.py <label>")
    folder = HERE / "results" / sys.argv[1]
    files = []
    for path in folder.glob("*_c*.json"):
        m = re.fullmatch(r"(.+)_c(\d+)\.json", path.name)
        if m:
            files.append((m.group(1), int(m.group(2)), path))
    if not files:
        sys.exit(f"no results in {folder}")

    lines = ["| " + " | ".join(name for name, _ in COLUMNS) + " |",
             "|" + "|".join("---" for _ in COLUMNS) + "|"]
    for workload, conc, path in sorted(files):
        data = json.loads(path.read_text())
        cells = [workload, str(conc)] + [fmt(data.get(key)) for _, key in COLUMNS[2:]]
        lines.append("| " + " | ".join(cells) + " |")

    table = "\n".join(lines)
    (folder / "summary.md").write_text(table + "\n")
    print(table)


if __name__ == "__main__":
    main()
