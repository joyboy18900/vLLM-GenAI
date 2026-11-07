# 11: Ingress with HTTPS

**What to build:** The user opens Open WebUI and Grafana through HTTPS host names from the Mac browser. Voice mode works over HTTPS without an SSH tunnel.

**Blocked by:** 06, 07

**Status:** ready-for-agent

- [ ] k3s Ingress (Traefik) routes host names to Open WebUI and Grafana
- [ ] TLS certificate from a local certificate authority, trusted by the Mac browser; no private keys committed to the repository
- [ ] Open WebUI and Grafana load over HTTPS with no certificate warning
- [ ] Voice call mode works over HTTPS (microphone allowed)
- [ ] The setup runbook has the certificate, Ingress, and host name steps
