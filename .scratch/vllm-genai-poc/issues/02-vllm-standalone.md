# 02: vLLM standalone on the PC

**What to build:** vLLM serves Qwen3.5-4B directly on the PC (outside Kubernetes). A `curl` chat completion returns an answer. The real VRAM use is measured and replaces the estimates in CLAUDE.md.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] vLLM version pinned, Qwen3.5-4B served in bf16 through the OpenAI-compatible API
- [ ] Thinking mode off by default, tool calling enabled with the correct parser for the model
- [ ] `curl` to `/v1/models` lists the model, and `curl` to `/v1/chat/completions` returns a non-empty answer (stream and non-stream)
- [ ] VRAM measured: weights, KV cache size (tokens and max concurrency from the vLLM log), desktop display use
- [ ] If the KV cache is too small, the text-only option or fp8 weights are tested and the choice is recorded
- [ ] The VRAM budget table in CLAUDE.md shows the measured numbers
- [ ] The setup runbook and the benchmarks document record the commands and numbers
- [ ] The standalone process is stopped and the GPU is free at the end
