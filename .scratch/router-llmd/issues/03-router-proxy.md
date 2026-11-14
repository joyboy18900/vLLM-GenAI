# 03: Router proxy with stream and error handling

**What to build:** A FastAPI service proxies `/v1/chat/completions` (stream and not stream) and `/v1/models` to the chosen pod, and has `/health`, `/metrics`, and `/router/stats`.

**Blocked by:** 02

**Status:** ready-for-agent

**Test status:** not started.

- [ ] Tests are written first: stream and non-stream answers pass through, and the header `X-Routed-Pod` is on every answer
- [ ] One retry on another pod when the chosen pod fails before the first byte; no retry after the stream started; the error is counted
- [ ] 503 with a clear message when no pod is ready
- [ ] The router polls `/metrics` of each pod every 1 to 2 seconds, and counts its own in-flight requests
- [ ] `/router/stats` shows the state and the score of each pod
- [ ] The image has pinned package versions
