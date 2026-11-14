# 02: Function that chooses the pod

**What to build:** A function with no I/O takes the state of the pods (queue, running, KV cache use, prefix history) and a request, and returns the best pod with its score. The weights come from environment variables.

**Blocked by:** 01

**Status:** ready-for-agent

**Test status:** done on the Mac on 2026-11-14: 26 tests in `router/tests/test_scoring.py` pass (`uv run --python 3.12 --with pytest pytest router/tests`). The prefix key uses the first 200 characters (`PREFIX_CHARS`). The history of served prefixes of each pod is kept by the proxy (ticket 03). The function only reads it.

- [x] Tests are written first (pytest) with fake vLLM `/metrics` text and a fake pod list
- [x] Score: prefix bonus, minus a weight times the queue (waiting plus running plus in-flight), minus a weight times the KV cache use
- [x] The prefix key is a hash of the system prompt and the first N characters of the first user message; N is chosen here and written in the spec
- [x] A pod that does not answer is not chosen; with no ready pod the function returns no choice
- [x] The parser of the `/metrics` text reads the five vLLM metric names of the spec
- [x] Ties are broken in a fixed way, and a test shows it
