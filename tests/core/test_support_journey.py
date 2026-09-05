from swarm.core.support_journey import (
    SUPPORT_JOURNEY_FIXTURE,
    is_support_consumer,
    support_kickstart,
)


def test_support_consumers_and_kickstart_phrases():
    assert SUPPORT_JOURNEY_FIXTURE == "ONBOARD_JOURNEY_CLI_API_REMOTE"
    assert is_support_consumer("support")
    assert is_support_consumer("starter-support")
    assert not is_support_consumer("codey")
    chips = " ".join(support_kickstart()).lower()
    assert "create a team" in chips
    assert "add a remote" in chips
    assert "wire a cli" in chips
