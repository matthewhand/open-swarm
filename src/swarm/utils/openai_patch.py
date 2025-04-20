"""
Monkeypatch OpenAI SDK to prevent telemetry/tracing when using a custom endpoint.
This disables any calls to OpenAI's internal tracing/telemetry/reporting subsystems.
Should be imported at startup if a custom OpenAI endpoint is used.
"""

def patch_openai_telemetry():
    try:
        import openai
        # Patch telemetry/tracing if present (for openai>=1.0.0)
        # For openai<1.0.0, there is no tracing, but be defensive.
        if hasattr(openai, "_telemetry"):
            openai._telemetry = None
        # For openai>=1.0.0, tracing is in openai.tracing
        if hasattr(openai, "tracing"):
            class DummyTracer:
                def add_event(self, *a, **k): pass
                def post(self, *a, **k): pass
                def record(self, *a, **k): pass
            openai.tracing.tracer = DummyTracer()
        # Patch any post/trace/report methods
        for attr in ("post", "trace", "report", "send_usage", "_post"):
            if hasattr(openai, attr):
                setattr(openai, attr, lambda *a, **k: None)
        # Patch environment variable if supported
        import os
        os.environ["OPENAI_TELEMETRY_OPTS"] = "off"
    except ImportError:
        pass

# Optionally, auto-patch if this file is imported as __main__
if __name__ == "__main__":
    patch_openai_telemetry()
