import logging

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


def test_hook_exception_is_logged_and_pipeline_continues(caplog, monkeypatch):
    monkeypatch.setenv("SWARM_DETERMINISTIC_HOOKS", "1")
    # Parent 'swarm' logger may have propagate=False; enable for caplog.
    monkeypatch.setattr(logging.getLogger("src.swarm"), "propagate", True)
    monkeypatch.setattr(logging.getLogger("swarm"), "propagate", True)
    d = Dispatcher()
    called: list[str] = []

    @d.pre
    def boom(ctx):
        raise RuntimeError("hook blew up")

    @d.pre
    def still_runs(ctx):
        called.append("still_runs")

    with caplog.at_level(logging.ERROR):
        d.run({})

    assert called == ["still_runs"]
    assert any(
        "failed during pre phase" in rec.getMessage() and rec.exc_info is not None
        for rec in caplog.records
    )
