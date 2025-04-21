# Patch OpenAI telemetry/tracing if using a custom endpoint
from swarm.utils.openai_patch import patch_openai_telemetry
patch_openai_telemetry()
# Disable OpenAI Agents Python tracing unless enabled in config
import swarm.utils.disable_tracing
swarm.utils.disable_tracing.activate()

import asyncio
import logging
from swarm.utils.redact import redact_sensitive_data

class DummyClient:
    base_url = "https://dummy.local"

class OpenAIChatCompletionsModel:
    def __init__(self, model=None, openai_client=None):
        print("[DEBUG] OpenAIChatCompletionsModel __init__ called with model:", redact_sensitive_data(model), "client:", redact_sensitive_data(str(openai_client)))
        self.model = model
        self.openai_client = openai_client
        self._client = DummyClient()  # Patch: provide base_url

    async def get_response(self, messages, **kwargs):
        print("[DEBUG] OpenAIChatCompletionsModel.get_response called with messages:", redact_sensitive_data(messages), "kwargs:", redact_sensitive_data(kwargs))
        # Actually call OpenAI API for chat completions
        # Assumes self.openai_client is an AsyncOpenAI instance from openai>=1.0.0
        params = {
            "model": self.model,
            "messages": messages,
        }
        # Support max_completion_tokens (for o4-mini etc)
        if "max_completion_tokens" in kwargs:
            params["max_tokens"] = kwargs["max_completion_tokens"]
        # Backward compatibility: allow max_tokens if present (but prefer max_completion_tokens)
        if "max_tokens" in kwargs and "max_completion_tokens" not in kwargs:
            params["max_tokens"] = kwargs["max_tokens"]
        # Optionally add other OpenAI parameters
        for k in ["temperature", "stream", "stop", "user", "n"]:
            if k in kwargs:
                params[k] = kwargs[k]
        # PATCH: Add timeout and retry logic for long/slow completions
        import asyncio
        import httpx
        timeout_seconds = int(kwargs.get("timeout", 10))  # Lower for test
        max_retries = 3
        logger = logging.getLogger(__name__)
        for attempt in range(max_retries):
            try:
                logger.info(f"[OPENAI COMPLETIONS] Attempt {attempt+1}/{max_retries} with timeout {timeout_seconds}s")
                response = await asyncio.wait_for(self.openai_client.chat.completions.create(**params), timeout=timeout_seconds)
                logger.info(f"OpenAI response received: {redact_sensitive_data(str(response))}")
                print("\n[OPENAI COMPLETIONS RESPONSE]", redact_sensitive_data(str(response)))
                return response
            except asyncio.TimeoutError:
                logger.warning(f"[OPENAI COMPLETIONS TIMEOUT] Attempt {attempt+1}/{max_retries}")
                if attempt == max_retries - 1:
                    logger.error(f"[OPENAI COMPLETIONS TIMEOUT] Final attempt failed after {timeout_seconds}s.")
                    raise
                await asyncio.sleep(2 * (attempt+1))
            except httpx.HTTPStatusError as e:
                logger.warning(f"[OPENAI COMPLETIONS HTTP ERROR] {e} (Attempt {attempt+1}/{max_retries})")
                if attempt == max_retries - 1:
                    logger.error(f"[OPENAI COMPLETIONS HTTP ERROR] Final attempt failed: {e}")
                    raise
                await asyncio.sleep(2 * (attempt+1))
            except Exception as e:
                logger.warning(f"[OPENAI COMPLETIONS ERROR] {e} (Attempt {attempt+1}/{max_retries})")
                if attempt == max_retries - 1:
                    logger.error(f"[OPENAI COMPLETIONS ERROR] Final attempt failed: {e}")
                    raise
                await asyncio.sleep(2 * (attempt+1))

    # Add any other methods as needed for compatibility with your agent runner.
