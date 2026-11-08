# 16: Workflow diagram

**What to build:** A workflow diagram of our system in the style of the reference diagram, saved in the docs folder.

**Blocked by:** 15

**Status:** ready-for-human

**Test status:** the diagram exists. `docs/workflow.png` was made with ChatGPT from the reference diagram. `docs/workflow.svg` is the same system drawn as code, with correct arrows in the monitoring box. Known issues of the PNG, to fix later: in the monitoring box the arrows Grafana > Loki and Loki > Alertmanager are wrong (the real ones are Prometheus > Alertmanager, Loki > Grafana, Prometheus > Grafana), and the purple dashed line from Internal Networking to Open WebUI is cut. Check the word "Traefik" in the image. The prompt and the architecture text for ChatGPT are kept outside the repository. Box 3 (matches the deployed system) stays open until the full run.

- [x] The agent writes an image prompt that lists every component, port, and data path of our system, in the style of the reference diagram
- [ ] The user creates the image with an AI image tool and saves it in the docs folder
- [ ] The diagram matches the deployed system (no components that do not exist)
