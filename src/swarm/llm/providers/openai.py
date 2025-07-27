from agents.models.interface import Model
from openai import OpenAI  # Changed from AsyncOpenAI to sync client


class OpenAIChatCompletionsModel(Model):
    def __init__(self, model: str, openai_client: OpenAI):
        super().__init__()
        self.model = model
        self.client = openai_client

    from collections.abc import AsyncIterator

    from agents.models.interface import ModelResponse, TResponseStreamEvent

    async def get_response(self,
                         system_instructions: str,
                         user_query: str,
                         temperature: float = 0.7,
                         max_tokens: int = 1000,
                         **kwargs) -> ModelResponse:
        """Get response from the model."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_query}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return ModelResponse(
            content=response.choices[0].message.content,
            model=self.model,
            usage=response.usage.dict()
        )

    async def stream_response(self,
                            system_instructions: str,
                            user_query: str,
                            temperature: float = 0.7,
                            max_tokens: int = 1000,
                            **kwargs) -> AsyncIterator[TResponseStreamEvent]:
        """Stream response from the model."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_query}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs
        )
        async for chunk in response:
            yield {
                "content": chunk.choices[0].delta.content or "",
                "finished": chunk.choices[0].finish_reason is not None
            }
