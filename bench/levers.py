#!/usr/bin/env python3
"""Set the vLLM Deployment to one benchmark configuration.

Each configuration is a full argument list for the vLLM container. The first one is the baseline.
The others add one lever, or a few levers together, so that their effect can be measured.

    python3 bench/levers.py list
    python3 bench/levers.py show spec_ngram          # print the vLLM arguments
    python3 bench/levers.py apply spec_ngram         # patch the Deployment and wait
    bench/run.sh spec_ngram                          # then measure
    python3 bench/quality_check.py --label spec_ngram

`deployed` is the argument list of k8s/vllm-deployment.yaml (the same as `baseline`). Keep the two in step.
Flag names were checked against vllm/engine/arg_utils.py at v0.28.0.
"""
import argparse
import json
import subprocess
import sys

DEPLOYMENT = "deploy/vllm-qwen"

MODEL = "Qwen/Qwen2.5-3B-Instruct"
MODEL_AWQ = "Qwen/Qwen2.5-3B-Instruct-AWQ"

# The same at the end of every configuration.
TAIL = [
    f"--served-model-name={MODEL}",
    "--enable-auto-tool-choice",
    "--tool-call-parser=hermes",
    "--host=0.0.0.0",
    "--port=8000",
]

NGRAM = ('--speculative-config={"method":"ngram","num_speculative_tokens":4,'
         '"prompt_lookup_max":4,"prompt_lookup_min":2}')
DRAFT = ('--speculative-config={"method":"draft_model",'
         '"model":"Qwen/Qwen2.5-0.5B-Instruct","num_speculative_tokens":3}')
COMPILE = ["-cc.mode=3", "-cc.cudagraph_mode=FULL_AND_PIECEWISE"]

CONFIGS = {
    # fp16, the plain engine
    "baseline": [
        MODEL, "--dtype=float16", "--gpu-memory-utilization=0.85",
        "--max-model-len=8192", "--max-num-seqs=16", "--enable-prefix-caching",
    ],
    # AWQ W4A16: 4-bit weights
    "awq": [
        MODEL_AWQ, "--gpu-memory-utilization=0.85",
        "--max-model-len=8192", "--max-num-seqs=16", "--enable-prefix-caching",
    ],
    # scheduler and memory right-sizing
    "sched": [
        MODEL, "--dtype=float16", "--gpu-memory-utilization=0.92",
        "--max-model-len=4096", "--max-num-seqs=8", "--max-num-batched-tokens=4096",
        "--enable-prefix-caching",
    ],
    # the same as `sched` at utilization 0.85, because 0.92 does not start on the WSL2 PC
    "sched_085": [
        MODEL, "--dtype=float16", "--gpu-memory-utilization=0.85",
        "--max-model-len=4096", "--max-num-seqs=8", "--max-num-batched-tokens=4096",
        "--enable-prefix-caching",
    ],
    # the same as `kv_fp8` at utilization 0.85
    "kv_fp8_085": [
        MODEL, "--dtype=float16", "--gpu-memory-utilization=0.85",
        "--max-model-len=4096", "--max-num-seqs=8", "--max-num-batched-tokens=4096",
        "--enable-prefix-caching", "--kv-cache-dtype=fp8",
    ],
    # fp8 KV cache
    "kv_fp8": [
        MODEL, "--dtype=float16", "--gpu-memory-utilization=0.92",
        "--max-model-len=4096", "--max-num-seqs=8", "--max-num-batched-tokens=4096",
        "--enable-prefix-caching", "--kv-cache-dtype=fp8",
    ],
    # speculative decoding: n-gram (prompt lookup), no extra weights
    "spec_ngram": [
        MODEL, "--dtype=float16", "--gpu-memory-utilization=0.85",
        "--max-model-len=8192", "--max-num-seqs=16", "--enable-prefix-caching",
        NGRAM,
    ],
    # speculative decoding: a draft model (about 1 GiB more)
    "spec_draft": [
        MODEL, "--dtype=float16", "--gpu-memory-utilization=0.85",
        "--max-model-len=8192", "--max-num-seqs=16", "--enable-prefix-caching",
        DRAFT,
    ],
    # torch.compile mode 3 and full CUDA graphs
    "compile": [
        MODEL, "--dtype=float16", "--gpu-memory-utilization=0.85",
        "--max-model-len=8192", "--max-num-seqs=16", "--enable-prefix-caching",
        *COMPILE,
    ],
    # the earlier Deployment: n-gram, chunked prefill, utilization 0.80
    "ngram_chunked": [
        MODEL, "--dtype=float16", "--gpu-memory-utilization=0.80",
        "--max-model-len=8192", "--max-num-seqs=16", "--enable-prefix-caching",
        "--enable-chunked-prefill", "--max-num-batched-tokens=2048",
        NGRAM,
    ],
    # AWQ, scheduler sizing, compile, and n-gram together
    "min_latency": [
        MODEL_AWQ, "--gpu-memory-utilization=0.92",
        "--max-model-len=4096", "--max-num-seqs=8", "--max-num-batched-tokens=4096",
        "--enable-prefix-caching", *COMPILE, NGRAM,
    ],
}

# The final choice: the Deployment uses the arguments of the baseline.
CONFIGS["deployed"] = CONFIGS["baseline"]


def build_args(name):
    return CONFIGS[name] + TAIL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["list", "show", "apply"])
    ap.add_argument("config", nargs="?", choices=sorted(CONFIGS))
    a = ap.parse_args()

    if a.command == "list":
        print("\n".join(CONFIGS))
        return
    if not a.config:
        ap.error("a configuration name is required")
    args = build_args(a.config)
    if a.command == "show":
        print(json.dumps(args, indent=2))
        return
    patch = [{"op": "replace", "path": "/spec/template/spec/containers/0/args", "value": args}]
    subprocess.run(["kubectl", "patch", DEPLOYMENT, "--type=json", "-p", json.dumps(patch)], check=True)
    subprocess.run(["kubectl", "rollout", "status", DEPLOYMENT, "--timeout=20m"], check=True)


if __name__ == "__main__":
    main()
