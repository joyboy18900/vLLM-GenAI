# 16: Workflow diagram

**What to build:** A workflow diagram of our system saved in the docs folder.

**Blocked by:** 15

**Status:** ready-for-human

**Test status:** the diagram exists. `docs/workflow.png` was made with ChatGPT. `docs/workflow.svg` is the same system drawn as code, with correct arrows in the monitoring box. Known issues of the PNG, to fix later: in the monitoring box the arrows Grafana > Loki and Loki > Alertmanager are wrong (the real ones are Prometheus > Alertmanager, Loki > Grafana, Prometheus > Grafana), and the purple dashed line from Internal Networking to Open WebUI is cut. Check the word "Traefik" in the image. The prompt and the architecture text for ChatGPT are kept outside the repository, as the files `prompt.md` and `architecture.md` on the owner's Desktop. Box 3 (matches the deployed system) stays open until the full run. The vLLM box of the PNG still says Qwen3.5-4B, bf16. It must say Qwen2.5-3B-Instruct, fp16 (the architecture text for ChatGPT is updated).

- [x] The agent writes an image prompt that lists every component, port, and data path of our system
- [ ] The user creates the image with an AI image tool and saves it in the docs folder
- [ ] The diagram matches the deployed system (no components that do not exist)
