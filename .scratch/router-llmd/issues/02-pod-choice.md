# 02: Function that chooses the pod

**What to build:** A function with no I/O takes the state of the pods (queue, running, KV cache use, prefix history) and a request, and returns the best pod with its score. The weights come from environment variables.

**Blocked by:** 01

**Status:** ready-for-agent

**Test status:** not started.

- [ ] Tests are written first (pytest) with fake vLLM `/metrics` text and a fake pod list
- [ ] Score: prefix bonus, minus a weight times the queue (waiting plus running plus in-flight), minus a weight times the KV cache use
- [ ] The prefix key is a hash of the system prompt and the first N characters of the first user message; N is chosen here and written in the spec
- [ ] A pod that does not answer is not chosen; with no ready pod the function returns no choice
- [ ] The parser of the `/metrics` text reads the five vLLM metric names of the spec
- [ ] Ties are broken in a fixed way, and a test shows it
