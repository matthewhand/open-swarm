from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)
from typing import List, Callable, Union, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict

# AgentFunction = Callable[[], Union[str, "Agent", dict]]
AgentFunction = Callable[..., Union[str, "Agent", dict]]

class Agent(BaseModel):
    # model_config = ConfigDict(arbitrary_types_allowed=True)  # Allow non-Pydantic types (for nemo guardrails instance)

    name: str = "Agent"
    model: str = "default"
    instructions: Union[str, Callable[[], str]] = "You are a helpful agent."
    functions: List[AgentFunction] = []
    resources: List[Dict[str, Any]] = []  # New attribute for static and MCP-discovered resources
    tool_choice: str = None
    # parallel_tool_calls: bool = True  # Commented out as in your version
    parallel_tool_calls: bool = False
    mcp_servers: Optional[List[str]] = None  # List of MCP server names
    env_vars: Optional[Dict[str, str]] = None  # Environment variables required
    response_format: Optional[Dict[str, Any]] = None  # Structured Output

class Response(BaseModel):
    id: Optional[str] = None  # id needed for REST
    messages: List = []  # Adjusted to allow any list (flexible for messages)
    agent: Optional[Agent] = None
    context_variables: dict = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Automatically generate an ID if not provided
        if not self.id:
            import uuid
            self.id = f"response-{uuid.uuid4()}"

class Result(BaseModel):
    """
    Encapsulates the possible return values for an agent function.

    Attributes:
        value (str): The result value as a string.
        agent (Agent): The agent instance, if applicable.
        context_variables (dict): A dictionary of context variables.
    """
    value: str = ""
    agent: Optional[Agent] = None
    context_variables: dict = {}

class Tool:
    def __init__(
        self,
        name: str,
        func: Callable,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
        dynamic: bool = False,
    ):
        """
        Initialize a Tool object.

        :param name: Name of the tool.
        :param func: The callable associated with this tool.
        :param description: A brief description of the tool.
        :param input_schema: Schema defining the inputs the tool accepts.
        :param dynamic: Whether this tool is dynamically generated.
        """
        self.name = name
        self.func = func
        self.description = description
        self.input_schema = input_schema or {}
        self.dynamic = dynamic

    @property
    def __name__(self):
        return self.name

    @property
    def __code__(self):
        # Return the __code__ of the actual function, or a mock object if missing
        return getattr(self.func, "__code__", None)

    def __call__(self, *args, **kwargs):
        """
        Make the Tool instance callable.
        """
        return self.func(*args, **kwargs)
