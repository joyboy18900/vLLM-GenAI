# Spec A: LLM-D router, several AWQ pods, scale-to-zero

Status: ready-for-agent

This is the first of three specs for the parts of `CLAUDE.md` that the proof of concept left out
(`.scratch/vllm-genai-poc/spec.md`, section "Out of Scope"). The order is A, then B (feedback
pipeline), then C (training and LoRA hot-swap). Each one ends with its own tests before the next one
starts. The specs B and C are written when their turn comes.

## Problem Statement

The proof of concept serves one vLLM pod. The learning goals of the project include the choice of
the best instance for each request (the LLM-D idea), scale-to-zero for idle pods, and a test of the
Kubernetes load balancing with several AWQ pods. None of this exists yet.

## Solution

A small router in front of two vLLM pods (Qwen2.5-3B-Instruct AWQ) on the one GPU of the PC.
Open WebUI talks to the router. The router is an OpenAI-compatible proxy. It reads the metrics of each
pod, gives each pod a score, and sends the request to the best pod. It also scales the second pod down
to zero when it is idle, and up again when a request needs it. The router has its own metrics, a row in
the Grafana dashboard, and basic alerts.

The router is the LLM-D mock of `CLAUDE.md`. It is not the semantic prefix router of the source
project.

## User Stories

1. As the operator, I want Open WebUI to use one OpenAI-compatible address that hides the pods, so
   that I change nothing in the UI when pods start or stop.
2. As the operator, I want the router to choose the pod by queue length, KV cache use, and a prefix
   match, so that I can see how a real inference platform decides.
3. As the operator, I want the weights of the score to be environment variables, so that I can change
   them without a new image.
4. As the operator, I want the router to read the pod list from the Kubernetes API by label, so that a
   pod that starts or stops joins or leaves the pool by itself.
5. As the operator, I want the router to read `/metrics` of each pod every 1 to 2 seconds and to count
   its own in-flight requests, so that a decision uses fresh data.
6. As the operator, I want a pod that does not answer to leave the pool for a short time, so that
   requests do not go to a dead pod.
7. As the operator, I want a retry on another pod when the chosen pod fails before it sends any byte,
   and no retry after the stream started, so that an answer is never doubled or cut in a silent way.
8. As the operator, I want a clear 503 when no pod is ready, so that the UI shows a real error.
9. As the operator, I want the second pod to scale to zero when idle, and the first pod to stay warm,
   so that the VRAM is free when nobody chats and the first message does not wait for a cold start.
10. As a user, I want my request to wait (up to 120 seconds) while a pod starts, so that I get an
    answer instead of an error.
11. As the operator, I want the header `X-Routed-Pod` on every answer and a `/router/stats` page, so
    that I can check which pod was chosen and why.
12. As the operator, I want Prometheus to scrape the router, Grafana to show a row "Router", and
    alerts for a router that is down or has no ready pod, so that I can see the load and test the router.
13. As the operator, I want the real VRAM use of two AWQ pods on the one GPU to be measured before any
    manifest is written, so that the plan does not depend on a guess.
14. As the operator, I want a benchmark through the router against one pod, with the result written
    down, even if the router brings no speed gain on one GPU.
15. As a user of the repository, I want to go back to the single `baseline` pod by pointing Open WebUI
    at the Service `vllm`, so that the proof of concept stays usable.

## Implementation Decisions

- **Language and place.** Python with FastAPI. The code is in `router/main.py` (HTTP layer) and
  `router/k8s_client.py` (pod list and scale), and the choice logic is in its own module with no I/O,
  so that it is easy to test. The image is built on the PC and imported into k3s with `docker save`,
  like the speech images. No registry. Versions of the packages are pinned.
- **Path of a request.** Open WebUI sets `OPENAI_API_BASE_URL` to the router Service. The router proxies
  `/v1/chat/completions` (stream and not stream) and `/v1/models`. STT and TTS do not go through the
  router.
- **Endpoints.** `/v1/chat/completions`, `/v1/models`, `/health`, `/metrics`, `/router/stats` (JSON with
  the state and the score of each pod). Every answer has the header `X-Routed-Pod`.
- **Pod choice.** One score for each ready pod: a bonus when the prefix of the request matches a prefix
  that this pod served before, minus a weight times the queue length (`num_requests_waiting` plus
  `num_requests_running` plus requests that the router has sent and not finished), minus a weight times
  `kv_cache_usage_perc`. The pod with the best score wins. The weights are environment variables. The
  prefix key is a hash of the system prompt and the first characters of the first user message. The
  number of characters is 200 (`PREFIX_CHARS` in `router/scoring.py`).
- **State of the pods.** The router reads `/metrics` of each pod every 1 to 2 seconds. A pod that does
  not answer is out of the pool until it answers again.
- **Pool.** Two Deployments of the AWQ model, `vllm-awq-a` and `vllm-awq-b`, with the same label as the
  `vllm` job of Prometheus, so that Prometheus scrapes them with no change. Each has a share of
  `--gpu-memory-utilization`. A third pod did not start at 0.29 (ticket 01), so the pool has two pods. The fp16 `baseline`
  pod is not in the pool, because it needs all of the VRAM.
- **Scale.** Pod `a` stays at one replica. Pod `b` goes to zero replicas after a set idle time (start
  value: 10 minutes). When no ready pod can take a request, the router scales pod `b` to one and holds
  the request until the pod is ready, for at most 120 seconds. After that it answers 503. The router
  has a ServiceAccount with a Role that can only read pods and change the scale of those two
  Deployments.
- **Errors.** Retry once on another pod when the chosen pod fails before the first byte. No retry after
  the stream started. 503 when no pod is ready.
- **Metrics of the router.** `router_requests_total{pod,status}`, `router_route_score{pod}`,
  `router_pod_up{pod}`, `router_cold_start_wait_seconds`, `router_scale_events_total{direction}`,
  `router_upstream_errors_total`. The dashboard row is made by `bench/gen_dash.py`. Alerts: router down,
  no ready pod.
- **GPU time-slicing.** The node has one `nvidia.com/gpu`, so a second pod stays `Pending`. The device
  plugin runs with time-slicing (`replicas: 3`, found in ticket 01). The Service `vllm` selects
  `variant: fp16`, so the pool pods (which have `app: vllm` for Prometheus) are not behind it.
- **Single GPU rules.** Nothing except the vLLM pods requests the GPU. The pods share the one GPU, so the
  router does not make the system faster. It makes the decisions visible.
- **Writing rules.** The same as in the proof of concept: English documents, ASD-STE100 style, no em
  dash, no filler text. Small commits. No push without a clear "push ja". No pull request (no CI).

## Testing Decisions

- **TDD.** The pod choice and the routing rules are written test first with pytest. The tests use fake
  `/metrics` text from vLLM and a fake pod list. No GPU is needed for them.
- **E2E on the cluster.** The checks are made through the HTTP surface of the router: a chat completion
  through the router returns an answer and the header `X-Routed-Pod`, a stopped pod is out of the
  pool, a scale from zero returns an answer after the cold start, and `/metrics` of the router is
  scraped by Prometheus.
- **Benchmark.** `vllm bench serve` through the router against one pod, with the same workloads and
  concurrency as the proof of concept. The result is written in `docs/benchmarks.md`, even if the router
  gives no gain.
- **Success.** The router chooses the right pod according to the signals, and every number is measured
  and recorded. A higher throughput is not a goal, because the pods share one GPU.
- The smoke test `bench/smoke_test.sh` gets a check for the router.

## Out of Scope

- The semantic prefix router of the source project (bge-m3 embedding).
- A real multi-GPU or multi-node setup.
- The feedback pipeline (spec B) and the training (spec C).
- Authentication, rate limits, and quotas in the router.
- Autoscaling by load (more pods when busy). Only scale to zero and back is in scope.
- CI, a license file, Terraform.

## Further Notes

- The router runs on the PC in WSL2 first. Bare-metal Ubuntu comes after the proof of concept run 2.
- Facts from the proof of concept: vLLM sees 10.79 GiB free VRAM at start, AWQ weights are 1.95 GiB,
  the KV cache of AWQ is 6.89 GiB at utilization 0.85, and a cold start takes about 51 to 71 seconds.
- The vLLM metrics that the router reads: `vllm:num_requests_waiting`, `vllm:num_requests_running`,
  `vllm:kv_cache_usage_perc`, `vllm:prefix_cache_hits_total`, `vllm:prefix_cache_queries_total`.
- `docs/what-is-left.md` lists this work as option 4.
