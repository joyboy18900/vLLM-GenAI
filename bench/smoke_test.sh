#!/bin/sh
# Full smoke test. Prints PASS or FAIL for each check. Exit code is 1 if any check fails.
#
#   sh bench/smoke_test.sh <pc-address> [path to ca.crt]
#   sh bench/smoke_test.sh --no-https           (for example on EC2, without the Ingress)
#
# Part 1 runs in a temporary pod, because most Services are ClusterIP only.
# Part 2 runs on the Mac and calls the Ingress over HTTPS.
# The script is plain sh so that it also runs in the curl image (no bash there).
set -u

MODEL="Qwen/Qwen3.5-4B"
FAILED=0

check() { # name, then the command
  name="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "PASS  $name"; else echo "FAIL  $name"; FAILED=1; fi
}

# ---------------------------------------------------------------- part 1 (in the cluster)
chat_ok() {
  curl -sf -m 120 -H 'Content-Type: application/json' \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hi\"}],\"max_tokens\":32}" \
    http://vllm:8000/v1/chat/completions | grep -q '"content":"[^"]'
}

roundtrip_ok() {
  curl -sf -m 60 -H 'Content-Type: application/json' -d '{"input":"hello world"}' \
    http://tts:8000/v1/audio/speech -o /tmp/hw.wav &&
  curl -sf -m 120 -F file=@/tmp/hw.wav -F model=whisper-1 \
    http://stt:8000/v1/audio/transcriptions | grep -qi 'hello world'
}

target_up() { # a PromQL query that must return 1
  curl -sf -m 10 -G http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query \
    --data-urlencode "query=$1" | grep -q '"value":\[[0-9.]*,"1"\]'
}

loki_ready() { curl -sf -m 10 http://loki.monitoring.svc.cluster.local:3100/ready | grep -q ready; }
alertmanager_ready() { curl -sf -m 10 http://alertmanager.monitoring.svc.cluster.local:9093/-/ready; }

in_cluster() {
  check "vLLM chat completion returns an answer" chat_ok
  check "TTS to STT round trip returns hello world" roundtrip_ok
  check "Prometheus target up: vllm" target_up 'min(up{job="vllm"})'
  check "Prometheus target up: stt" target_up 'min(up{job="speech",app="stt"})'
  check "Prometheus target up: tts" target_up 'min(up{job="speech",app="tts"})'
  check "Prometheus target up: dcgm" target_up 'min(up{job="dcgm"})'
  check "Prometheus target up: node-exporter" target_up 'min(up{job="node-exporter"})'
  check "Prometheus target up: kube-state-metrics" target_up 'min(up{job="kube-state-metrics"})'
  check "Loki is ready" loki_ready
  check "Alertmanager is ready" alertmanager_ready
}

if [ "${1:-}" = "--in-cluster" ]; then
  in_cluster
  exit "$FAILED"
fi

# ---------------------------------------------------------------- part 2 (on the Mac)
HTTPS=1
if [ "${1:-}" = "--no-https" ]; then HTTPS=0; fi
if [ "$HTTPS" -eq 1 ]; then
  PC="${1:?usage: sh bench/smoke_test.sh <pc-address> [ca.crt] | --no-https}"
  CA="${2:-$HOME/.genai-certs/ca.crt}"
fi

https_ok() { # host, path
  curl -sf -m 15 --cacert "$CA" --resolve "$1:443:$PC" -o /dev/null "https://$1$2"
}

echo "== in the cluster =="
OUT="$(kubectl run "smoke-$$" --rm -i --restart=Never --image=curlimages/curl:8.11.1 \
  --command -- sh -s -- --in-cluster < "$0" 2>&1)"
echo "$OUT" | grep -E '^(PASS|FAIL)'
# kubectl run may not pass on the exit code of the pod, so read the text.
if echo "$OUT" | grep -q '^FAIL' || ! echo "$OUT" | grep -q '^PASS'; then FAILED=1; fi

if [ "$HTTPS" -eq 1 ]; then
  echo "== over HTTPS through the Ingress =="
  check "Open WebUI answers over HTTPS" https_ok webui.genai.test /health
  check "Grafana answers over HTTPS" https_ok grafana.genai.test /api/health
fi

if [ "$FAILED" -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECKS FAILED"; fi
exit "$FAILED"
