# Benchmarks

This file has no measured numbers yet. Each section says which step fills it. A number goes
here only when a script made it. Do not type numbers by hand.

## Test setup

Fill this table before the first run. It makes each result repeatable.

| Item | Value |
|---|---|
| Machine | not measured yet |
| GPU and driver version | not measured yet |
| vLLM version | not measured yet |
| Model and dtype | not measured yet |
| Flags | not measured yet |

## VRAM (ticket 02)

Not measured yet. Ticket 02 measures weights, KV cache size (tokens and maximum
concurrency from the vLLM log), and the desktop display use.

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

