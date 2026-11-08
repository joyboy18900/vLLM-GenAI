#!/usr/bin/env python3
"""Set the vLLM Deployment to the baseline or to one optimization lever.

Each lever changes one thing against the baseline, so its effect is measured alone.

    python3 bench/levers.py list
    python3 bench/levers.py show spec-ngram          # print the vLLM arguments
    python3 bench/levers.py apply spec-ngram         # patch the Deployment and wait
    bench/run.sh spec-ngram                          # then measure
    python3 bench/quality_check.py --label spec-ngram

    python3 bench/levers.py apply awq --model <AWQ checkpoint>   # AWQ needs its own checkpoint

Flag names were checked against vllm/engine/arg_utils.py at v0.28.0.
"""
import argparse
import json
import subprocess
import sys

DEPLOYMENT = "deploy/vllm-qwen"

# Baseline: bf16, no optional engine levers. Prefix caching and chunked prefill are
# switched off on purpose, so their levers show a real difference.
# Keep every other flag in step with k8s/vllm-deployment.yaml. Change both files together.
BASELINE = [
    "Qwen/Qwen3.5-4B",
    "--served-model-name=Qwen/Qwen3.5-4B",
    "--dtype=bfloat16",
    "--language-model-only",
    "--gpu-memory-utilization=0.80",
    "--max-model-len=4096",
    "--max-num-seqs=4",
    "--no-enable-prefix-caching",
    "--no-enable-chunked-prefill",
    "--reasoning-parser=qwen3",
    '--default-chat-template-kwargs={"enable_thinking": false}',
    "--enable-auto-tool-choice",
    "--tool-call-parser=qwen3_coder",
    "--host=0.0.0.0",
    "--port=8000",
]

NGRAM = {"method": "ngram", "num_speculative_tokens": 4, "prompt_lookup_max": 4, "prompt_lookup_min": 2}
MTP = {"method": "qwen3_next_mtp", "num_speculative_tokens": 2}  # from the Qwen3.5-4B model card

# name: (flags to remove by prefix, flags to add)
LEVERS = {
    "baseline": ([], []),
    "prefix-caching": (["--no-enable-prefix-caching"], ["--enable-prefix-caching"]),
    "chunked-prefill": (
        ["--no-enable-chunked-prefill"],
        ["--enable-chunked-prefill", "--max-num-batched-tokens=2048"],
    ),
    "spec-ngram": ([], ["--speculative-config=" + json.dumps(NGRAM)]),
    "spec-mtp": ([], ["--speculative-config=" + json.dumps(MTP)]),
    "awq": ([], ["--quantization=awq"]),
    "fp8-weights": ([], ["--quantization=fp8"]),
    "fp8-kv-cache": ([], ["--kv-cache-dtype=fp8"]),
    "thinking-on": (
        ["--default-chat-template-kwargs"],
        ['--default-chat-template-kwargs={"enable_thinking": true}'],
    ),
}


def build_args(lever, model=None):
    remove, add = LEVERS[lever]
    args = [a for a in BASELINE if not any(a.startswith(r) for r in remove)] + add
    if model:
        args[0] = model
    elif lever == "awq":
        sys.exit("the awq lever needs --model <AWQ checkpoint>")
    return args


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["list", "show", "apply"])
    ap.add_argument("lever", nargs="?", choices=sorted(LEVERS))
    ap.add_argument("--model", help="checkpoint to use instead of the baseline model")
    a = ap.parse_args()

    if a.command == "list":
        print("\n".join(sorted(LEVERS)))
        return
    if not a.lever:
        ap.error("a lever name is required")
    args = build_args(a.lever, a.model)
    if a.command == "show":
        print(json.dumps(args, indent=2))
        return
    patch = [{"op": "replace", "path": "/spec/template/spec/containers/0/args", "value": args}]
    subprocess.run(["kubectl", "patch", DEPLOYMENT, "--type=json", "-p", json.dumps(patch)], check=True)
    subprocess.run(["kubectl", "rollout", "status", DEPLOYMENT, "--timeout=20m"], check=True)


if __name__ == "__main__":
    main()
