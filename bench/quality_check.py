#!/usr/bin/env python3
"""Run a fixed English and Thai prompt set at temperature 0 and check the answers.

The check is a simple "answer contains an expected word" test. It is a guard for
lossless levers: a lever that changes the answers must show up here.

    kubectl port-forward svc/vllm 8000:8000     # in another terminal
    python3 bench/quality_check.py --label baseline

The raw answers go to bench/results/<label>/quality.json, so two runs can be compared.
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent


def ask(base_url, model, prompt, timeout):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 128,
        "seed": 42,
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions", body, {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    return (data["choices"][0]["message"].get("content") or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--label", required=True, help="result folder name, for example baseline")
    ap.add_argument("--results-dir", default=str(HERE / "results"))
    ap.add_argument("--timeout", type=float, default=120)
    args = ap.parse_args()

    prompts = json.loads((HERE / "prompts" / "quality_prompts.json").read_text())
    rows = []
    for item in prompts:
        answer = ask(args.base_url, args.model, item["prompt"], args.timeout)
        ok = any(word.lower() in answer.lower() for word in item["expect"])
        rows.append({**item, "answer": answer, "pass": ok})
        print(f"{'PASS' if ok else 'FAIL'}  {item['id']}")

    out = Path(args.results_dir) / args.label
    out.mkdir(parents=True, exist_ok=True)
    (out / "quality.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))

    for lang in ("en", "th"):
        group = [r for r in rows if r["lang"] == lang]
        print(f"{lang}: {sum(r['pass'] for r in group)}/{len(group)} passed")
    sys.exit(0 if all(r["pass"] for r in rows) else 1)


if __name__ == "__main__":
    main()
