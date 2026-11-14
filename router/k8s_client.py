"""Pod list of the router, read from the Kubernetes API."""
import asyncio

from proxy import PodInfo


class KubernetesPodSource:
    """Running pods that match a label selector. Each pod is a vLLM pod of the pool. The name is
    the value of the label `pool-member` (for example `a`), so it stays the same after a restart."""

    def __init__(self, api, namespace, selector, port=8000):
        self._api = api
        self._namespace = namespace
        self._selector = selector
        self._port = port

    async def __call__(self):
        # The client of Kubernetes is synchronous, so it runs in a thread.
        pods = await asyncio.to_thread(self._api.list_namespaced_pod, self._namespace,
                                       label_selector=self._selector)
        found = []
        for p in pods.items:
            if p.status.phase != "Running" or p.metadata.deletion_timestamp or not p.status.pod_ip:
                continue
            name = (p.metadata.labels or {}).get("pool-member") or p.metadata.name
            found.append(PodInfo(name=name, url=f"http://{p.status.pod_ip}:{self._port}"))
        return found


def in_cluster_source(selector, namespace=None, port=8000):
    """Source for a router that runs in a pod (uses its ServiceAccount)."""
    from kubernetes import client, config

    config.load_incluster_config()
    if namespace is None:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            namespace = f.read().strip()
    return KubernetesPodSource(client.CoreV1Api(), namespace, selector, port)
