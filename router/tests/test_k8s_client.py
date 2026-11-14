import asyncio
import os
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from k8s_client import KubernetesPodSource
from proxy import PodInfo


def pod(member, ip="10.0.0.1", phase="Running", deleting=False, name=None):
    meta = NS(name=name or f"vllm-awq-{member}-xyz", labels={"pool-member": member} if member else {},
              deletion_timestamp="now" if deleting else None)
    return NS(metadata=meta, status=NS(phase=phase, pod_ip=ip))


class FakeApi:
    def __init__(self, pods):
        self.pods = pods
        self.calls = []

    def list_namespaced_pod(self, namespace, label_selector=None):
        self.calls.append((namespace, label_selector))
        return NS(items=self.pods)


def run(api, **kw):
    src = KubernetesPodSource(api, "default", "pool=awq", **kw)
    return asyncio.run(src())


def test_lists_the_pods_with_the_selector_in_the_namespace():
    api = FakeApi([pod("a", "10.0.0.5")])
    assert run(api) == [PodInfo(name="a", url="http://10.0.0.5:8000")]
    assert api.calls == [("default", "pool=awq")]


def test_uses_the_port_argument():
    assert run(FakeApi([pod("a", "10.0.0.5")]), port=9000)[0].url == "http://10.0.0.5:9000"


def test_skips_pods_that_are_not_running():
    assert run(FakeApi([pod("a", phase="Pending"), pod("b", phase="Failed")])) == []


def test_skips_pods_that_are_ending():
    assert run(FakeApi([pod("a", deleting=True)])) == []


def test_skips_pods_without_an_ip():
    assert run(FakeApi([pod("a", ip=None)])) == []


def test_name_falls_back_to_the_pod_name_without_the_member_label():
    assert run(FakeApi([pod(None, name="vllm-x")]))[0].name == "vllm-x"


def test_no_pods_gives_an_empty_list():
    assert run(FakeApi([])) == []
