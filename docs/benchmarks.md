# Benchmarks

Each number here comes from a vLLM log line, from `nvidia-smi`, or from a script. Do not type
numbers by hand. Every result says where it was measured. The first runs are on WSL2, so the label
is "WSL2". They do not replace the runs on Ubuntu or EC2.

## Test setup

| Item | Value |
|---|---|
| Machine | The local PC (Ryzen 7 8700F, 32 GB RAM) in WSL2 (Ubuntu 24.04, 24 GB limit) on Windows. Run on 2026-11-08. |
| GPU and driver version | RTX 4070 SUPER 12 GB. Windows driver 616.64, driver seen in WSL2 615.65.07, CUDA 13.4. |
| vLLM version | v0.28.0 (`vllm/vllm-openai:v0.28.0`) |
| Model and dtype | `Qwen/Qwen3.5-4B`, bfloat16, text-only (`--language-model-only`) |
| Flags | `--gpu-memory-utilization 0.89 --max-model-len 4096 --max-num-seqs 4 --reasoning-parser qwen3 --default-chat-template-kwargs '{"enable_thinking": false}' --enable-auto-tool-choice --tool-call-parser qwen3_coder` |

## VRAM (ticket 02)

Measured on WSL2, with the Windows desktop on the same GPU.

| Item | Value | Source |
|---|---|---|
| Desktop display, before vLLM | 1,067 MiB (later reads between 403 and 1,085 MiB) | `nvidia-smi` |
| Checkpoint size | 8.68 GiB | vLLM log |
| Weights, text-only (`--language-model-only`) | 7.99 GiB | vLLM log: "Model loading took" |
| Weights, with the vision encoder | 8.61 GiB | vLLM log |
| KV cache at utilization 0.89 | 0.92 GiB, 16,384 tokens, 4.00x concurrency for 4,096 tokens | vLLM log |
| Total VRAM in use, vLLM idle | 10,541 MiB of 12,282 MiB (this includes the desktop) | `nvidia-smi` |
| Start time | 135 s with the caches. The first start also downloads the model (264 s). | vLLM log |

Start failures that show the limits:

| Setting | Result |
|---|---|
| Utilization 0.80, text-only | KV cache memory is -0.15 GiB. vLLM does not start. |
| Utilization 0.90, text-only | vLLM refuses: free memory 10.79 GiB is not enough for 10.79 GiB plus rounding. |
| Utilization 0.89, with the vision encoder | KV cache memory is -0.18 GiB. vLLM does not start. |

Choice: keep `--language-model-only` and `--gpu-memory-utilization 0.89`. The highest value is set
by the free VRAM at the start (the total VRAM minus the desktop). Each 0.01 is about 0.12 GiB. fp8
weights were not tested, because the text-only option was enough. They stay a lever for ticket 13.

Checks that passed on WSL2: `/v1/models` lists the model, a chat completion answers (normal and
stream), thinking is off (no reasoning field, `reasoning_tokens` is 0), and a tool call returns
`tool_calls` with the right arguments.

## Baseline (ticket 12)

Not measured yet. Run these commands, then paste the table here:

```bash
bench/run.sh baseline
python3 bench/summarize.py baseline
python3 bench/quality_check.py --label baseline
```

## Optimization levers (ticket 13)

Not measured yet. One section per lever: latency, throughput, VRAM, and the quality result.
The levers are: prefix caching, chunked prefill, n-gram speculative decoding, MTP speculative
decoding, AWQ, fp8 weights, fp8 KV cache, and thinking on or off (TTFT). Run them with
`bench/levers.py` (see `docs/setup.md`, section "Optimization levers").

Final choice: not made yet. Write the chosen flags and the reasons here.

## Voice (ticket 06)

Not measured yet. The time from the end of speech to the first audio.

## Thai TTS (ticket 18, bonus)

Candidates. The facts come from the model cards and the project pages. Time and quality are not
measured yet (see `docs/setup.md`, section "Thai TTS").

| Item | Piper `th_TH-tsync2-medium` | FastThaiG2P (Thai Kokoro-82M, ONNX) |
|---|---|---|
| Runs on | CPU | CPU |
| Size | 63 MB | about 326 MB |
| Sample rate | 22.05 kHz | not checked |
| License of the code | GPL-3.0 (`piper-tts` 1.8.0, from PyPI and the repository) | Apache-2.0 |
| License of the voice data or weights | CC BY-NC-SA 3.0, non-commercial (from the model card of the voice) | not stated in the release notes or the README |
| Needs | Piper 1.8 or newer (we use 1.8.0) | a new server in this repository |
| Time to first audio | not measured yet | not measured yet |
| RTF | not measured yet | not measured yet (the authors state about 0.2 on the CPU) |
| Listening result | not heard yet | not heard yet |

Chosen voice: not chosen yet.

