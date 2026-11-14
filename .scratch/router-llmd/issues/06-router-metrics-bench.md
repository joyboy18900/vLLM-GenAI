# 06: Router metrics, dashboard, alerts, benchmark, and documents

**What to build:** The router is visible in Prometheus and Grafana, has alerts, and its effect is measured and written down.

**Blocked by:** 05

**Status:** ready-for-agent

**Test status:** done on WSL2 on 2026-11-14 (numbers in `docs/benchmarks.md`). 73 tests pass. Prometheus scrapes the router (job `router`, up). The Grafana row "Router" is made by `bench/gen_dash.py` and loaded by Grafana, but the panels were not looked at in the browser, so that box stays open. `RouterNoReadyPod` and `RouterDown` each fired and resolved in a test. The smoke test passed 12 of 12 checks. The benchmark through the router (workload `chat`) shows -3% out tok/s at concurrency 1 and -54% at 8 and 16 against pod `a` direct, because the two pods share one GPU. The `prefix` workload could not run, because it uses `/v1/completions`, which the router does not proxy. README, GUIDE, setup, and what-is-left are updated; `CLAUDE.md` is unchanged (its design text already names the router).

- [x] The router metrics of the spec are exposed and Prometheus scrapes them (a new job)
- [ ] The Grafana row "Router" is made by `bench/gen_dash.py` and shows requests by pod, scores, pods up, cold start wait, and scale events
- [x] Alerts: router down, and no ready pod; each was tested once
- [x] (workload `chat` only, see the note) The benchmark runs through the router and against one pod with the same workloads and concurrency as the proof of concept, and the result is in `docs/benchmarks.md` even if there is no gain
- [x] `bench/smoke_test.sh` has a check for the router
- [x] README, `CLAUDE.md` status table, `docs/GUIDE.md`, and `docs/setup.md` describe the router; `docs/what-is-left.md` is updated
