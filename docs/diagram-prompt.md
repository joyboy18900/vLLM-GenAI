# Prompt for the workflow diagram

The file `docs/workflow.png` was made with ChatGPT from the diagram of the reference project. The file
`docs/workflow.svg` shows the same system, drawn as code. Use this prompt in an AI image tool to make
a new version. Save the result as `docs/workflow.png`. Then check the image
against the list "Check the image" below. Fix the prompt and generate again if a check fails.

The diagram shows only parts that exist in this repository. It must not show the LLM-D router,
the feedback collector, Redis, or the retraining job. They are planned and not built.

## Prompt

```
Create a clean, flat technical architecture diagram on a white background, 16:10 landscape,
colored icons, rounded boxes, numbered circle badges, all text in English.

Title (top left, bold): "AI Voice Chat System on k3s (Single Node, 1 GPU)"
Subtitle: "Workflow: User > Open WebUI > vLLM + STT + TTS > Response | Monitoring covers the whole system"

LEFT COLUMN, top to bottom:
1. "User" box (person icon, chat bubble, microphone). Badge 1.
2. "Ingress (Traefik)" box with a globe icon and the text ":443 HTTPS". A small lock box
   "HTTPS (TLS, local CA)" next to it. Under it, a small grey note: "or SSH tunnel to NodePort :30080".
3. "Open WebUI" box (browser window icon) with the text ":8080". Badge 1.

CENTER: a large dashed blue rounded box labeled "k3s Cluster (Single Node)" with a Kubernetes
wheel icon. Inside it:
- "vLLM (LLM Inference)" box with a cube icon, the text "Qwen3.5-4B, bf16" and ":8000". Badge 2.
- Next to vLLM, a green "GPU" box with the NVIDIA logo style icon and the text
  "NVIDIA RTX 4070 SUPER, 12 GB". A two-way arrow between vLLM and the GPU box.
- Below vLLM, two pink boxes side by side: "STT (faster-whisper, CPU)" with a microphone icon and
  ":8000", and "TTS (Piper, CPU)" with a speaker icon and ":8000". Badge 3 on both.
- A purple box "Internal Networking (ClusterIP Services)" with four small labels:
  "webui", "vllm", "stt", "tts". Badge 4.

RIGHT SIDE INSIDE THE k3s BOX: an orange dashed box "Monitoring & Observability" with badge 6.
Left part, "Exporters / Metrics Sources", five rows with icons:
  "vLLM metrics (/metrics)", "STT metrics (/metrics)", "TTS metrics (/metrics)",
  "Node Exporter (CPU, RAM, disk) :9100", "DCGM Exporter (GPU) :9400",
  "kube-state-metrics (pods, nodes) :8080".
Right part, a vertical chain of boxes with down arrows:
  "Prometheus :9090" (flame icon) > "Grafana :3000" (dashboard icon, small line chart),
  "Alertmanager :9093" (bell icon) under Prometheus,
  "Loki :3100" (log icon) with a small box "Alloy (log collector)" feeding Loki, and Loki feeding Grafana.
Orange dashed arrows go from every exporter to Prometheus. Grafana reads from Prometheus and Loki.

BOTTOM ROW, outside the k3s box, three green boxes with badge 5:
  "Hugging Face (Model Hub), model weights",
  "Container registries (Docker Hub, GHCR, NVIDIA), images",
  "Persistent Storage (PVC, local-path), models, caches, chat history, metrics, logs".

ARROWS (use these colors):
- Black solid: User > Ingress > Open WebUI (user request and response).
- Blue solid: Open WebUI > vLLM, label "Chat Completion (OpenAI API, streaming)".
- Pink dashed: Open WebUI <-> STT and Open WebUI <-> TTS (audio path, optional).
- Purple dashed: internal communication through the ClusterIP Services.
- Green dashed: external integration (Hugging Face, registries, storage).
- Orange dashed: metrics and logs.

RIGHT PANEL, six numbered cards, each with a small icon, a colored title, and one short line:
1 "User > Open WebUI": the user opens the web UI through HTTPS or an SSH tunnel.
2 "Open WebUI > vLLM": chat requests use the OpenAI API. vLLM runs Qwen3.5-4B on the GPU.
3 "Voice Flow (Optional)": user speech > STT (faster-whisper) > text. Answer text > TTS (Piper) > sound.
4 "Internal Networking": services talk through ClusterIP Services (webui, vllm, stt, tts).
5 "External Services": model download from Hugging Face, images from registries, data on PVC.
6 "Monitoring & Observability": metrics in Prometheus, dashboards in Grafana, logs in Loki, alerts in Alertmanager.

BOTTOM LEGEND (one line): black "User Request / Response", blue "LLM Inference Path",
pink dashed "Audio Path (Optional)", purple dashed "Internal Communication",
green dashed "External Integration", orange dashed "Metrics / Logs".

Style: Inter or similar sans-serif font, consistent icon style, thin borders, soft pastel fills,
no shadows, no 3D, no gradients, no extra components, no Thai text.
```

## Check the image

- [ ] Every box in the prompt appears, and the ports match (8080, 8000, 8000, 8000, 9090, 3000, 3100, 9093, 9100, 9400, 8080).
- [ ] No router, no Redis, no feedback collector, no retraining job.
- [ ] The text is readable and has no spelling errors.
- [ ] The arrow colors match the legend.
- [ ] The image shows the deployed system. If you change the system, change the prompt too.
