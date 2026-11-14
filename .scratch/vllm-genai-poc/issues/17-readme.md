# 17: README

**What to build:** A README in English with the same sections as the reference README, so a reader can set up and use the system.

**Blocked by:** 15, 16

**Status:** ready-for-agent

**Test status:** checked on 2026-11-14. Sections, credit, and the vLLM Bangkok sentence are in place. `docs/workflow.png` exists (made with ChatGPT, known issues in ticket 16). The criterion "every command was run on the PC" stays open: the commands ran on WSL2, but the HTTPS Ingress step (step 6) did not run, and the README status table says so.

- [x] Same sections as the reference README: overview with the diagram, machine requirements, setup steps, smoke test, repo layout, documents, status
- [x] Credit: inspired by the reference project, with a link, and 1-2 sentences that the project started after the vLLM Bangkok meetup
- [ ] Every command in the README was run on the PC
- [x] ASD-STE100 style, no em dashes, no filler text
