# Spec: vLLM-GenAI proof of concept

Status: ready-for-agent

## Problem Statement

I want to learn LLM serving infrastructure end to end: vLLM, Kubernetes with a GPU, a voice pipeline, and monitoring. I also want a working result: a ChatGPT-like chatbot that I can type to or talk to, on my own hardware.

I found a good reference project, [PoonpipatChangkwain/vLLM-chatBOT](https://github.com/PoonpipatChangkwain/vLLM-chatBOT). It runs this kind of stack on one T4 GPU on AWS EC2. I want to build my own version with the same concept and structure, but with a newer Qwen model, on my own PC, and with the infrastructure that its architecture diagram shows but its code does not have yet.

## Solution

A single-node k3s cluster on my Ubuntu PC (RTX 4070 SUPER 12GB) that runs:

- vLLM serving Qwen3.5-4B through the OpenAI-compatible API
- Open WebUI as the chat frontend, with text chat and voice call mode
- faster-whisper (STT) and Piper (TTS) on CPU, behind OpenAI-compatible audio APIs, so voice mode works in English
- A full monitoring and observability stack: Prometheus, Grafana, Loki, Alertmanager, DCGM exporter, Node Exporter, kube-state-metrics, and `/metrics` on vLLM, STT, and TTS
- Ingress with HTTPS (TLS) and persistent storage through PVCs
- A benchmark harness and recorded results

The repository follows the reference project: the same folder layout, the same documents (README, CLAUDE.md, GUIDE, setup runbook, benchmarks, workflow diagram), translated to English and changed only where the hardware, the model, or our agreed additions require it. The setup runbook says the system was tested on the local PC, and has a short section for EC2.

## User Stories

### Machine setup
1. As the operator, I want a runbook to prepare a fresh Ubuntu PC with the NVIDIA driver, so that the GPU is visible to the OS.
2. As the operator, I want the NVIDIA Container Toolkit installed, so that containers can use the GPU.
3. As the operator, I want k3s installed as a single-node cluster, so that I can deploy every service with Kubernetes.
4. As the operator, I want the NVIDIA device plugin and a `nvidia` RuntimeClass, so that the node reports one `nvidia.com/gpu` resource.
5. As the operator, I want a check command for each setup step, so that I know the step worked before I continue.
6. As the operator, I want the runbook to record the PC spec (CPU, RAM, GPU, disk, OS version), so that others know what was tested.

### LLM serving
7. As the operator, I want to run vLLM alone on the PC first, so that I can tune its flags before I add Kubernetes.
8. As the operator, I want vLLM to serve Qwen3.5-4B, so that the chatbot uses a current Qwen model.
9. As the operator, I want the real VRAM budget measured on the 12GB GPU (weights, KV cache, desktop display), so that the estimates in CLAUDE.md are replaced with facts.
10. As the operator, I want thinking mode off by default, so that replies, and voice replies in particular, start fast.
11. As the operator, I want tool calling enabled with the correct parser for the model, so that Open WebUI requests do not fail.
12. As the operator, I want vLLM deployed as a k3s Deployment with a ClusterIP Service, so that other pods reach it by name.
13. As the operator, I want the vLLM Deployment to use the Recreate strategy, so that a new pod never waits for the one GPU that the old pod holds.
14. As the operator, I want startup, readiness, and liveness probes on `/health`, so that k3s waits for a slow cold start and restarts a stuck pod.
15. As the operator, I want Service links disabled on the vLLM pod, so that the injected `VLLM_PORT` variable does not crash vLLM.
16. As the operator, I want model weights and compile caches on persistent storage, so that a pod restart does not download or compile again.
17. As the operator, I want a shared-memory volume for vLLM, so that its workers have enough `/dev/shm`.

### Speech
18. As a user, I want to speak to the chatbot, so that I can use it hands-free.
19. As a user, I want the chatbot to answer with a voice, so that the conversation feels like a call.
20. As the operator, I want an STT server with the OpenAI `/v1/audio/transcriptions` API backed by faster-whisper on CPU, so that Open WebUI can use it without code changes.
21. As the operator, I want a TTS server with the OpenAI `/v1/audio/speech` API backed by Piper on CPU, so that Open WebUI can use it without code changes.
22. As the operator, I want STT and TTS to use no GPU, so that vLLM keeps all of the VRAM.
23. As the operator, I want STT and TTS as separate, always-on pods with their own ClusterIP Services, so that they restart without an effect on vLLM.
24. As the operator, I want the STT and TTS latency settings from the reference (English-only model, greedy decoding, fixed language, VAD filter, no trailing silence, serialized synthesis), so that voice mode is fast and has no stutter.
25. As a user, I want sentence-level streaming of speech, so that I hear the first sentence while the model still writes the rest.

### Frontend
26. As a user, I want a ChatGPT-like web UI, so that I can chat in a familiar way.
27. As a user, I want streamed text answers, so that I see the answer token by token.
28. As a user, I want a separate voice call screen, so that talking and typing are separate modes, as in the ChatGPT app.
29. As the operator, I want Open WebUI configured through environment variables to use vLLM, STT, and TTS by their Service names, so that no manual UI setup is necessary.
30. As the operator, I want the Open WebUI image pinned to a version, so that a restart does not change its behavior.
31. As the operator, I want Open WebUI data on persistent storage, so that chat history survives a pod restart.

### Ingress and access
32. As a user, I want to open the chat UI over HTTPS, so that the browser allows the microphone.
33. As the operator, I want a k3s Ingress (Traefik) with TLS in front of Open WebUI and Grafana, so that the access path matches the reference diagram.
34. As the operator, I want a documented SSH tunnel option, so that I can reach the UI from my Mac through `localhost` as the reference does.

### Monitoring and observability
35. As the operator, I want Prometheus to scrape vLLM `/metrics`, so that I can see TTFT, TPOT, throughput, KV cache use, queue, and preemptions.
36. As the operator, I want `/metrics` on the STT and TTS servers with request latency, so that the speech targets are up (they are down in the reference).
37. As the operator, I want the DCGM exporter without a GPU request, so that I see GPU temperature, utilization, power, and VRAM without taking the GPU from vLLM.
38. As the operator, I want Node Exporter, so that I see CPU, RAM, and disk use of the PC.
39. As the operator, I want kube-state-metrics, so that I see pod and node state.
40. As the operator, I want Loki to collect pod logs, so that I can search logs in Grafana.
41. As the operator, I want Alertmanager with basic rules (for example: target down, preemptions above zero, GPU too hot), so that problems are visible without watching dashboards.
42. As the operator, I want Grafana dashboards stored as code in the repository, so that a pod restart does not lose them.
43. As the operator, I want a serving dashboard with SLO rows (latency, throughput) and saturation rows (KV cache, queue, preemptions, GPU), so that I can find the bottleneck.
44. As the operator, I want Grafana to require a login, so that it is not open as anonymous admin.

### Storage
45. As the operator, I want PersistentVolumeClaims (k3s local-path) instead of hostPath, so that storage uses the standard Kubernetes API.
46. As the operator, I want separate claims for model cache, Open WebUI data, and monitoring data, so that each one can be sized and cleaned alone.

### Benchmarks
47. As the operator, I want a benchmark harness based on `vllm bench serve`, so that I can measure each vLLM setting the same way.
48. As the operator, I want baseline numbers at concurrency 1, 8, and 16, so that I can compare every change against them.
49. As the operator, I want to test the optimization levers one at a time (prefix caching, chunked prefill, speculative decoding, AWQ, fp8 weights, fp8 KV cache), so that I know what each one gives and costs.
50. As the operator, I want a fixed quality prompt set checked at temperature 0, so that I see when a lever makes answers worse.
51. As the operator, I want the measured results in the benchmarks document, so that the reasons for the final vLLM flags are recorded.

### Smoke test
52. As the operator, I want a smoke test with `curl` like the reference (a chat completion to vLLM, and a TTS to STT round trip), so that I can check the core path in one minute.
53. As the operator, I want the smoke test to also check the added infrastructure endpoints (HTTPS Ingress, Prometheus targets, Grafana, Loki, Alertmanager), so that I know the full stack is up.

### Documentation
54. As a reader, I want a README in English with the same sections as the reference README, so that I can set up the system step by step.
55. As a reader, I want the README to credit the reference project and to say that the project started after the vLLM Bangkok meetup, so that the origin is clear.
56. As a reader, I want a GUIDE that explains how one request moves through the system (text and voice), so that I understand each component.
57. As a reader, I want a setup runbook that says it was tested on the local PC, with a short "If you run on EC2" section about the differences, so that I can try EC2 later.
58. As a reader, I want a workflow diagram in the style of the reference diagram, but with our components, so that I see the whole system in one picture.
59. As an agent, I want CLAUDE.md to follow the reference CLAUDE.md, translated to English and adapted to the PC, so that I follow the same rules as the reference.

### Bonus
60. As a Thai user, I want a Thai TTS voice as a later option, so that voice mode can answer in Thai.

## Implementation Decisions

- **Reference first.** The structure, documents, and concepts come from the reference project. Change only what the decisions below require. Code and manifests from the reference can be adapted where they fit.
- **Machine.** One Ubuntu PC (bare metal): AMD Ryzen 7 8700F, 32GB RAM, RTX 4070 SUPER 12GB (Ada). The desktop display uses the same GPU. The Mac is used only to edit code and run commands remotely. There is no k3s and no model serving on the Mac.
- **EC2.** Not used now. The documents describe it as an option, without an instance type name. They list what to check when the GPU is not the RTX 4070 SUPER: fp8 and bf16 support, VRAM size, quota, cost, and HTTPS or SSH tunnel for the microphone.
- **Model.** Qwen3.5-4B in bf16 as the baseline. Thinking mode off by default. Use the text-only option if the vision encoder takes needed VRAM. Check vLLM support for this model and record the real VRAM numbers in the first serving step.
- **Quantization.** No NVFP4. AWQ/GPTQ are the quantization methods. The RTX 4070 SUPER also supports fp8 weights and fp8 KV cache, which are measured in the benchmarks.
- **Speech.** faster-whisper and Piper on CPU, English voice, as in the reference. Both servers expose OpenAI-compatible audio APIs and a `/metrics` endpoint. Prefer prebuilt images over package installation at pod start.
- **Frontend.** Open WebUI with a pinned image version. Use its built-in voice call mode. No custom UI.
- **Infrastructure scope.** Build everything that the reference diagram shows, also the parts that the reference code does not have: Ingress with HTTPS (TLS), STT/TTS metrics, Node Exporter, kube-state-metrics, Loki, Alertmanager, and PVC storage.
- **Networking.** ClusterIP Services named `vllm`, `stt`, `tts`, and `webui` (as in the diagram). Ingress (Traefik) with TLS for external access. SSH tunnel documented as an option.
- **Single GPU rules.** vLLM uses the Recreate strategy. Nothing except vLLM requests the GPU. DCGM reads GPU metrics without a GPU request.
- **Planned items stay planned.** The LLM-D router, scale-to-zero, the feedback collector, Redis Streams, the retraining CronJob, and LoRA + DPO are in CLAUDE.md as in the reference, but they are not built in this proof of concept.
- **Git.** One private GitHub repository. Ask the user before every push. The first push replaces the old history on `main` (force push, with approval). The PC gets code with `git pull`.
- **No license file and no CI** for now.
- **Writing rules.** All repository documents are in English (ASD-STE100 style), with no em dashes and no filler text.
- **Diagram.** At the end, write an image prompt that describes our components in the style of the reference diagram. The user creates the image with an AI image tool, as the reference author did.
- **Work order.** PC setup, vLLM alone, vLLM on k3s, STT and TTS, Open WebUI, monitoring stack, Ingress with TLS and PVC, benchmarks, documents (GUIDE, setup with EC2 section, benchmarks), diagram, README, Thai TTS bonus.

## Testing Decisions

- A good test checks external behavior through the public HTTP APIs of the running services. It does not check internal code.
- The test seam is the HTTP surface of the deployed services, through one `curl` smoke test as in the reference:
  - vLLM: a chat completion request returns a non-empty answer from the Qwen model.
  - Speech: TTS turns "hello world" into WAV audio, and STT turns that audio back into text that contains "hello world".
  - Infrastructure: the HTTPS Ingress serves Open WebUI and Grafana, Prometheus reports its targets (vLLM, STT, TTS, DCGM, Node Exporter, kube-state-metrics) as up, and Loki and Alertmanager report ready.
- Each work step ends with the check commands from the setup runbook for that step, run on the real PC.
- Prior art: the smoke test section and the per-step checks in the reference README and setup runbook.
- No unit test framework and no CI.

## Out of Scope

- LLM-D router, scale-to-zero, multi-instance AWQ pods
- Feedback collection, Redis Streams, the retraining CronJob, LoRA + DPO training
- ChatGPT features beyond the reference: RAG, web search, memory, image input, image generation, multi-user login
- k3s or model serving on the Mac
- Running on EC2 (documented only)
- CI, a license file, Terraform or other infrastructure-as-code
- Thai voice as a requirement (it is a bonus at the end)

## Further Notes

- Reference repository is cloned next to this project for reading: `../vLLM-chatBOT`.
- The VRAM budget in CLAUDE.md is an estimate until the first serving step measures it.
- Desktop use of the GPU reduces the VRAM for vLLM. If the KV cache is too small, the options are fp8 weights or a smaller context length.
- Pin every image and package version when it is first added.
