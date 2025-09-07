

# Import the dispatcher we just created
from src.swarm.utils.hook_dispatcher import Dispatcher


def _register_dummy(dispatcher: Dispatcher, log: list[str]):
    @dispatcher.pre
    def pre_a(ctx):
        log.append("pre_a")

    @dispatcher.listen
    def listen_b(ctx):
        log.append("listen_b")

    @dispatcher.post
    def post_c(ctx):
        log.append("post_c")


def test_deterministic_order_enabled(monkeypatch):
    monkeypatch.setenv("SWARM_DETERMINISTIC_HOOKS", "1")
    d = Dispatcher()
    called: list[str] = []
    _register_dummy(d, called)

    d.run({})
    assert called == ["pre_a", "listen_b", "post_c"]


def test_deterministic_order_disabled(monkeypatch):
    # Ensure the env var is not set
    monkeypatch.delenv("SWARM_DETERMINISTIC_HOOKS", raising=False)
    d = Dispatcher()
    called: list[str] = []
    _register_dummy(d, called)

    d.run({})
    # In non-deterministic mode, we still run in phase order by insertion,
    # but the contract only guarantees same elements in any order.
    assert sorted(called) == ["listen_b", "post_c", "pre_a"]
