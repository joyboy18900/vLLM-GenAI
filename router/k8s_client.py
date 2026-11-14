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


class KubernetesScaleClient:
    """Reads and sets the replicas of a Deployment through its scale subresource."""

    def __init__(self, apps_api, namespace):
        self._api = apps_api
        self._namespace = namespace

    async def get_replicas(self, deployment):
        scale = await asyncio.to_thread(self._api.read_namespaced_deployment_scale, deployment, self._namespace)
        return scale.spec.replicas or 0

    async def set_replicas(self, deployment, replicas):
        await asyncio.to_thread(self._api.patch_namespaced_deployment_scale, deployment, self._namespace,
                                {"spec": {"replicas": replicas}})


def in_cluster_scale_client(namespace=None):
    from kubernetes import client, config

    config.load_incluster_config()
    return KubernetesScaleClient(client.AppsV1Api(), namespace or _own_namespace())


def _own_namespace():
    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
        return f.read().strip()
