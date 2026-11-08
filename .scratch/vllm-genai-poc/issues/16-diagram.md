# 16: Workflow diagram

**What to build:** A workflow diagram of our system in the style of the reference diagram, saved in the docs folder.

**Blocked by:** 15

**Status:** ready-for-human

**Test status:** the diagram exists: `docs/workflow.svg` (drawn as code by the agent) and `docs/workflow.png` (rendered from it). The prompt for an AI-made version is in `docs/diagram-prompt.md`. Every part in the diagram has a manifest in the repository. Check the diagram against the full run later (ticket box 3 stays open).

- [x] The agent writes an image prompt that lists every component, port, and data path of our system, in the style of the reference diagram
- [ ] The user creates the image with an AI image tool and saves it in the docs folder
- [ ] The diagram matches the deployed system (no components that do not exist)
