# 03: Router proxy with stream and error handling

**What to build:** A FastAPI service proxies `/v1/chat/completions` (stream and not stream) and `/v1/models` to the chosen pod, and has `/health`, `/metrics`, and `/router/stats`.

**Blocked by:** 02

**Status:** ready-for-agent

**Test status:** done on the Mac on 2026-11-14. 47 tests pass (`router/tests/`: 26 for the choice, 21 for the proxy), written first. A run with two fake pods over real HTTP showed that the stream arrives chunk by chunk, with the header `X-Routed-Pod` and the state in `/router/stats`. The image builds (`docker build router`) and has pinned packages (`router/requirements.txt`). Not tested yet with real vLLM pods (ticket 04). "First byte" in the retry rule means the response headers of the pod: a pod that fails before them is retried, and a stream that breaks after them is not. The router reads the pod list from `ROUTER_PODS` (a fixed list). The Kubernetes pod list comes in ticket 04 or 05.

- [x] Tests are written first: stream and non-stream answers pass through, and the header `X-Routed-Pod` is on every answer
- [x] One retry on another pod when the chosen pod fails before the first byte; no retry after the stream started; the error is counted
- [x] 503 with a clear message when no pod is ready
- [x] The router polls `/metrics` of each pod every 1 to 2 seconds, and counts its own in-flight requests
- [x] `/router/stats` shows the state and the score of each pod
- [x] The image has pinned package versions
