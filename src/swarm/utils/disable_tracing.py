"""
Utility to disable OpenAI Agents Python tracing by default unless explicitly enabled in config.
"""
import json


def traces_enabled_from_config(config_path="swarm_config.json"):
    try:
        with open(config_path) as f:
            config = json.load(f)
        # Look for openai_traces or similar in LLM config
        llm_config = config.get("llm", {})
        return llm_config.get("openai_traces", False)
    except Exception:
        return False

def disable_openai_agents_tracing():
    try:
        import agents.tracing.create as tracing_create
        import agents.tracing.setup as tracing_setup
        # Patch GLOBAL_TRACE_PROVIDER to always return disabled traces
        class DisabledTrace:
            def __init__(self, *_args, **_kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *_args, **_kwargs): pass
            def start(self): return self
            def finish(self): return self
        class DummyProvider:
            def get_current_trace(self): return DisabledTrace()
            def new_trace(self, *_args, **_kwargs): return DisabledTrace()
        tracing_setup.GLOBAL_TRACE_PROVIDER = DummyProvider()
        tracing_create.trace = lambda *_args, **_kwargs: DisabledTrace()
    except ImportError:
        pass

# At import, check config and disable tracing if not enabled
if not traces_enabled_from_config():
    disable_openai_agents_tracing()
