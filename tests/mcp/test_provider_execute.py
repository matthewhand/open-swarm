

def test_provider_set_executor_and_execute(monkeypatch):
    # Fake discovery with class_type placeholder
    fake_discovered = {
        "suggestion": {"metadata": {"name": "Suggestion"}, "class_type": object},
    }

    from swarm.mcp import provider as prov
    monkeypatch.setattr(prov, "discover_blueprints", lambda _: fake_discovered)

    p = prov.BlueprintMCPProvider(blueprint_dir="ignored")

    # Provide an executor that returns structured content
    def exec_fn(cls, instruction, args):
        assert cls is object
        return {"content": f"EXEC:{instruction}"}

    p.set_executor(exec_fn)
    out = p.call_tool("suggestion", {"instruction": "Hello"})
    assert out["content"] == "EXEC:Hello"

