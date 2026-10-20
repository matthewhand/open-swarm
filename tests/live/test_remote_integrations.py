"""Real adapter health, authenticated discovery and completed inference.

Run this directory explicitly. Only SWARM_LIVE_* variables opt services in.
"""
import os
import re
import uuid

import pytest

from tests.live.support import connection, instance_ids, reply_text

pytestmark = [pytest.mark.integration, pytest.mark.live_remote, pytest.mark.timeout(330)]


@pytest.mark.parametrize("instance", instance_ids(os.environ))
@pytest.mark.parametrize("phase", ["health", "discovery", "inference"])
def test_live_remote(instance, phase, caplog, capsys):
    # Suppress transport logs and raw exception details, which can carry secrets.
    caplog.set_level("CRITICAL")
    try:
        resolved = connection(instance, os.environ)
        if resolved is None:
            pytest.skip("no explicit SWARM_LIVE instance URL")
        spec, timeout, target = resolved
        from swarm.remotes.registry import create_remote_adapter

        adapter = create_remote_adapter(spec, {"remotes": {}, "settings": {}})
        if adapter is None:
            pytest.fail("adapter is not registered", pytrace=False)
        if phase == "health":
            result = adapter.health(min(timeout, 8))
        elif phase == "discovery":
            result = adapter.list(min(timeout, 12))
        else:
            # These adapters otherwise pick an existing bot/thread automatically.
            if spec.kind in {"omb", "rakazo", "anythingllm"} and not target:
                pytest.fail("set TARGET to a dedicated test bot/workspace before inference", pytrace=False)
            # Unique prompt avoids accepting a stale stored answer. Expected answer
            # is absent from the prompt, so an echo/202 receipt cannot pass.
            a = 1000 + int(uuid.uuid4().hex[:4], 16)
            b = 1000 + int(uuid.uuid4().hex[:4], 16)
            result = adapter.send(
                f"Integration verification: calculate {a} + {b}. Reply only with the integer. "
                "Do not use tools, modify files or control the computer.",
                timeout, target=target, session_id=None,
            )
            if result.ok and not re.search(rf"(?<!\d){a+b}(?!\d)", reply_text(result.data)):
                pytest.fail("no completed, correct model answer (a receipt is insufficient)", pytrace=False)
        if not result.ok:
            status = getattr(result, "http_status", None)
            pytest.fail(f"adapter {phase} failed (HTTP {status or 'unavailable'}); inspect service privately", pytrace=False)
    except Exception as exc:
        pytest.fail(f"adapter {phase} raised {type(exc).__name__}; details withheld", pytrace=False)
    finally:
        caplog.clear()
        capsys.readouterr()
