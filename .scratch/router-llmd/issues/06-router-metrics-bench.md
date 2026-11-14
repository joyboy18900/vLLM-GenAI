# 06: Router metrics, dashboard, alerts, benchmark, and documents

**What to build:** The router is visible in Prometheus and Grafana, has alerts, and its effect is measured and written down.

**Blocked by:** 05

**Status:** ready-for-agent

**Test status:** not started.

- [ ] The router metrics of the spec are exposed and Prometheus scrapes them (a new job)
- [ ] The Grafana row "Router" is made by `bench/gen_dash.py` and shows requests by pod, scores, pods up, cold start wait, and scale events
- [ ] Alerts: router down, and no ready pod; each was tested once
- [ ] The benchmark runs through the router and against one pod with the same workloads and concurrency as the proof of concept, and the result is in `docs/benchmarks.md` even if there is no gain
- [ ] `bench/smoke_test.sh` has a check for the router
- [ ] README, `CLAUDE.md` status table, `docs/GUIDE.md`, and `docs/setup.md` describe the router; `docs/what-is-left.md` is updated
