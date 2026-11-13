#!/usr/bin/env bash
# Run `vllm bench serve` for three workloads at concurrency 1, 8, and 16.
# Workloads:
#   random   workload A: random tokens, input 512, output 128 (engine only)
#   chat     workload C: chat text from bench/prompts, output 128
#   prefix   workload B: shared prefix 1024, input 256, output 128 (prefix caching), concurrency 1 and 8
#   summarize  workload E: summarize a text of about 450 words (bench/prompts/summarize_prompts.jsonl), output 128,
#              temperature 0. The answer copies words of the prompt, which is the case for n-gram decoding.
#   multiturn  workload D: chat with a history of earlier turns (bench/prompts/multiturn_prompts.jsonl), output 128
# The command runs inside the vLLM pod, so it measures the engine without network noise.
# The benchmark shares the pod CPU with the server. Do not run other work at the same time.
#
#   bench/run.sh baseline
#   WORKLOADS=multiturn bench/run.sh baseline-multiturn    # one workload only
#
# Raw JSON results are copied to bench/results/<label>/. Make the table with:
#   python3 bench/summarize.py <label>
set -euo pipefail

LABEL="${1:?usage: bench/run.sh <label>}"
MODEL="${MODEL:-Qwen/Qwen2.5-3B-Instruct}"
SEED="${SEED:-0}"
WARMUPS="${WARMUPS:-3}"
CONCURRENCIES="${CONCURRENCIES:-1 8 16}"
WORKLOADS="${WORKLOADS:-random chat prefix multiturn summarize}"
want() { case " $WORKLOADS " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

nprompts() { # prompts per concurrency level. NUM_PROMPTS overrides all levels.
  case "$1" in 1) echo 24 ;; 8) echo 96 ;; 16) echo 160 ;; *) echo 64 ;; esac
}

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/results/$LABEL"
POD="$(kubectl get pod -l app=vllm -o jsonpath='{.items[0].metadata.name}')"
REMOTE="/tmp/bench/$LABEL"

echo "pod: $POD  label: $LABEL"
kubectl exec "$POD" -- mkdir -p "$REMOTE" /tmp/bench-data
# The `custom` dataset needs pandas, which the vLLM image does not have. The `sharegpt` dataset
# reads plain JSON. The reply text is not used: --sharegpt-output-len sets the output length.
python3 -c 'import json, sys
print(json.dumps([{"conversations": [{"from": "human", "value": json.loads(l)["prompt"]},
                                     {"from": "gpt", "value": "-"}]} for l in sys.stdin if l.strip()]))' \
  < "$HERE/prompts/chat_prompts.jsonl" \
  | kubectl exec -i "$POD" -- sh -c 'cat > /tmp/bench-data/chat_prompts.json'
python3 -c 'import json, sys
print(json.dumps([{"conversations": [{"from": "human", "value": json.loads(l)["prompt"]},
                                     {"from": "gpt", "value": "-"}]} for l in sys.stdin if l.strip()]))' \
  < "$HERE/prompts/summarize_prompts.jsonl" \
  | kubectl exec -i "$POD" -- sh -c 'cat > /tmp/bench-data/summarize_prompts.json'
# The earlier turns go into one user message as a transcript. The server sees a long prompt that
# holds text that an answer can copy (n-gram decoding looks for it). The turns are not separate messages.
python3 -c 'import json, sys
def flat(turns):
    return "\n\n".join(("User: " if r == "user" else "Assistant: ") + t for r, t in turns)
print(json.dumps([{"conversations": [{"from": "human", "value": flat(json.loads(l)["turns"])},
                                     {"from": "gpt", "value": "-"}]} for l in sys.stdin if l.strip()]))' \
  < "$HERE/prompts/multiturn_prompts.jsonl" \
  | kubectl exec -i "$POD" -- sh -c 'cat > /tmp/bench-data/multiturn_prompts.json'

bench() { # name, concurrency, then the workload flags
  local name="$1" c="$2"; shift 2
  kubectl exec "$POD" -- vllm bench serve \
    --base-url http://localhost:8000 --model "$MODEL" --tokenizer "$MODEL" \
    --seed "$SEED" --num-warmups "$WARMUPS" \
    --max-concurrency "$c" --num-prompts "${NUM_PROMPTS:-$(nprompts "$c")}" \
    --percentile-metrics ttft,tpot,itl,e2el --metric-percentiles 50,99 \
    --save-result --result-dir "$REMOTE" --result-filename "${name}_c${c}.json" "$@"
}

for c in $CONCURRENCIES; do
  want random && bench random "$c" \
    --dataset-name random --random-input-len 512 --random-output-len 128 --random-prefix-len 0 \
    --ignore-eos --backend openai --endpoint /v1/completions
  want chat && bench chat "$c" \
    --dataset-name sharegpt --dataset-path /tmp/bench-data/chat_prompts.json --sharegpt-output-len 128 \
    --ignore-eos --backend openai-chat --endpoint /v1/chat/completions
  want multiturn && bench multiturn "$c" \
    --dataset-name sharegpt --dataset-path /tmp/bench-data/multiturn_prompts.json --sharegpt-output-len 128 \
    --ignore-eos --backend openai-chat --endpoint /v1/chat/completions
  want summarize && bench summarize "$c" \
    --dataset-name sharegpt --dataset-path /tmp/bench-data/summarize_prompts.json --sharegpt-output-len 128 \
    --ignore-eos --temperature 0 --backend openai-chat --endpoint /v1/chat/completions
  if want prefix; then
    case "$c" in 1|8)
      bench prefix "$c" \
        --dataset-name random --random-prefix-len 1024 --random-input-len 256 --random-output-len 128 \
        --ignore-eos --backend openai --endpoint /v1/completions ;;
    esac
  fi
done

mkdir -p "$OUT"
for f in $(kubectl exec "$POD" -- ls "$REMOTE"); do
  kubectl exec "$POD" -- cat "$REMOTE/$f" > "$OUT/$f"
done
echo "raw results: $OUT"
