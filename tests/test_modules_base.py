from hat.modules import Module, ModuleStatus, Orchestrator


class FakeModuleA(Module):
    name = "a"
    order = 0

    def __init__(self):
        self.activated = False
        self.deactivated = False

    def activate(self, config, secrets):
        self.activated = True

    def deactivate(self):
        self.deactivated = True

    def status(self):
        return ModuleStatus(active=self.activated, details="fake a")


class FakeModuleB(Module):
    name = "b"
    order = 1

    def __init__(self):
        self.activated = False
        self.deactivated = False

    def activate(self, config, secrets):
        self.activated = True

    def deactivate(self):
        self.deactivated = True

    def status(self):
        return ModuleStatus(active=self.activated, details="fake b")


def test_orchestrator_activate_order():
    a = FakeModuleA()
    b = FakeModuleB()
    orch = Orchestrator([b, a])  # pass in wrong order
    activated = orch.activate(config={}, secrets={})
    assert activated == ["a", "b"]  # sorted by order
    assert a.activated
    assert b.activated


def test_orchestrator_deactivate_reverse_order():
    a = FakeModuleA()
    b = FakeModuleB()
    orch = Orchestrator([a, b])
    orch.activate(config={}, secrets={})
    deactivated = orch.deactivate(["a", "b"])
    assert deactivated == ["b", "a"]  # reverse order
    assert a.deactivated
    assert b.deactivated


def test_orchestrator_skips_unconfigured():
    a = FakeModuleA()
    b = FakeModuleB()
    orch = Orchestrator([a, b])
    # config only has section for "a"
    config = {"a": {"key": "val"}}
    activated = orch.activate(config=config, secrets={}, only_configured=True)
    assert activated == ["a"]
    assert a.activated
    assert not b.activated


def test_orchestrator_status():
    a = FakeModuleA()
    b = FakeModuleB()
    orch = Orchestrator([a, b])
    orch.activate(config={}, secrets={})
    statuses = orch.status()
    assert statuses["a"].active is True
    assert statuses["b"].active is True


def test_orchestrator_rollback_on_failure():
    class FailingModule(Module):
        name = "fail"
        order = 2
        def activate(self, config, secrets):
            raise ValueError("boom")
        def deactivate(self):
            pass
        def status(self):
            return ModuleStatus(active=False)

    import pytest
    a = FakeModuleA()
    fail = FailingModule()
    orch = Orchestrator([a, fail])

    with pytest.raises(RuntimeError, match="Module 'fail' failed"):
        orch.activate(config={}, secrets={})

    # Module A should have been deactivated (rolled back)
    assert a.deactivated
