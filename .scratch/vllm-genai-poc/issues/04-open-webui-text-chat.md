# 04: Open WebUI text chat

**What to build:** Open WebUI runs in the cluster and uses the `vllm` Service. The user opens it in a browser (through an SSH tunnel from the Mac to `localhost`) and has a streamed text chat with Qwen3.5-4B.

**Blocked by:** 03

**Status:** ready-for-agent

**Test status:** written, untested. Manifest written. Schema checked with kubeconform only. Image pinned to v0.13.0.

- [ ] Open WebUI image pinned to a version
- [ ] Configured by environment variables to use the `vllm` Service; Ollama off; first boot kept light (no auto model updates, no web search)
- [ ] ClusterIP Service named `webui`, plus a NodePort for the SSH tunnel path
- [ ] Data (chat history, settings) on a PersistentVolumeClaim; history survives a pod restart
- [ ] A text chat in the browser streams the answer token by token
- [ ] The setup runbook has the deploy steps and the SSH tunnel command
