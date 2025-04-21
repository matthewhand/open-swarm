from dataclasses import dataclass

from agents import Agent, Runner


@dataclass
class JudgeResult:
    success: bool
    reason: str

class LLMTestJudgeBlueprint:
    def __init__(self, blueprint_id: str = None, **kwargs):
        self.agent = Agent(
            name="llm_test_judge",
            instructions=(
                "You are an impartial judge. Given a prompt and a candidate response, "
                "decide if the response is meaningful and correct. "
                "Return only a structured answer as JSON conforming to this schema: "
                "{\"success\": true/false, \"reason\": \"<short explanation>\"}. "
                "Be strict: only return true if the answer is genuinely meaningful."
            ),
            output_type=JudgeResult,
        )

    async def run(self, prompt: str, response: str, **kwargs) -> JudgeResult:
        # Compose the judging prompt for the LLM
        judge_prompt = f"""
        PROMPT: {prompt}
        RESPONSE: {response}
        Is the response meaningful and correct for the prompt above? 
        Respond only with the required structured output.
        """
        result = await Runner.run(self.agent, [{"role": "user", "content": judge_prompt}])
        return result.final_output
