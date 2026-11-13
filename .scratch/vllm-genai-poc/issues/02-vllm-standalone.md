# 02: vLLM standalone on the PC

**What to build:** vLLM serves Qwen2.5-3B-Instruct directly on the PC (outside Kubernetes). A `curl` chat completion returns an answer. The real VRAM use is measured and replaces the estimates in CLAUDE.md.

**Blocked by:** 01

**Status:** ready-for-agent

**Test status:** ran on WSL2 on 2026-11-13 with Qwen2.5-3B-Instruct in Docker (the cache folder of the k3s PVC was mounted, so no new download). Ready in 61 s. `/v1/models`, chat (normal and stream), and a tool call worked. The numbers equal those of the k3s pod (`docs/benchmarks.md`). Not ticked: the fp8 KV cache or AWQ test (the KV cache is not too small, 11.59x, the levers benchmark compares them) The table in CLAUDE.md has the measured numbers (2026-11-13).

- [x] vLLM version pinned, Qwen2.5-3B-Instruct served in fp16 through the OpenAI-compatible API
- [x] Tool calling enabled with the hermes parser
- [x] `curl` to `/v1/models` lists the model, and `curl` to `/v1/chat/completions` returns a non-empty answer (stream and non-stream)
- [x] VRAM measured: weights, KV cache size (tokens and max concurrency from the vLLM log), desktop display use
- [ ] If the KV cache is too small, the fp8 KV cache or AWQ is tested and the choice is recorded
- [x] The VRAM budget table in CLAUDE.md shows the measured numbers
- [x] The setup runbook and the benchmarks document record the commands and numbers
- [x] The standalone process is stopped and the GPU is free at the end
