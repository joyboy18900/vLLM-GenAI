#!/usr/bin/env bash
# Run `vllm bench serve` for three workloads at concurrency 1, 8, and 16.
# The command runs inside the vLLM pod, so it measures the engine without network noise.
# The benchmark shares the pod CPU with the server. Do not run other work at the same time.
#
#   bench/run.sh baseline
#
# Raw JSON results are copied to bench/results/<label>/. Make the table with:
#   python3 bench/summarize.py <label>
set -euo pipefail

LABEL="${1:?usage: bench/run.sh <label>}"
MODEL="${MODEL:-Qwen/Qwen3.5-4B}"
NUM_PROMPTS="${NUM_PROMPTS:-64}"
SEED="${SEED:-42}"
WARMUPS="${WARMUPS:-3}"
CONCURRENCIES="${CONCURRENCIES:-1 8 16}"

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/results/$LABEL"
POD="$(kubectl get pod -l app=vllm -o jsonpath='{.items[0].metadata.name}')"
REMOTE="/tmp/bench/$LABEL"

echo "pod: $POD  label: $LABEL"
kubectl exec "$POD" -- mkdir -p "$REMOTE" /tmp/bench-data
kubectl exec -i "$POD" -- sh -c 'cat > /tmp/bench-data/chat_prompts.jsonl' < "$HERE/prompts/chat_prompts.jsonl"

bench() { # name, then the dataset flags
  local name="$1"; shift
  kubectl exec "$POD" -- vllm bench serve \
    --backend openai-chat --endpoint /v1/chat/completions \
    --base-url http://localhost:8000 --model "$MODEL" \
    --num-prompts "$NUM_PROMPTS" --num-warmups "$WARMUPS" --seed "$SEED" \
    --save-result --result-dir "$REMOTE" --result-filename "$name.json" "$@"
}

for c in $CONCURRENCIES; do
  # engine only: random tokens
  bench "random_c$c" --max-concurrency "$c" \
    --dataset-name random --random-input-len 256 --random-output-len 128
  # real chat text
  bench "chat_c$c" --max-concurrency "$c" \
    --dataset-name custom --dataset-path /tmp/bench-data/chat_prompts.jsonl --custom-output-len 128
  # long shared prefix: shows the effect of prefix caching
  bench "prefix_c$c" --max-concurrency "$c" \
    --dataset-name prefix_repetition --prefix-repetition-prefix-len 1024 \
    --prefix-repetition-suffix-len 64 --prefix-repetition-num-prefixes 4 \
    --prefix-repetition-output-len 64
done

mkdir -p "$OUT"
for f in $(kubectl exec "$POD" -- ls "$REMOTE"); do
  kubectl exec "$POD" -- cat "$REMOTE/$f" > "$OUT/$f"
done
echo "raw results: $OUT"
