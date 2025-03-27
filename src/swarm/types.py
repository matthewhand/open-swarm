from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function as OpenAIFunction, # Renamed to avoid clash
)
from typing import List, Callable, Union, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import uuid
from enum import Enum

# --- Pydantic Settings for Swarm Core ---
class LogFormat(str, Enum):
    standard = "[%(levelname)s] %(asctime)s - %(name)s:%(lineno)d - %(message)s"
    simple = "[%(levelname)s] %(name)s - %(message)s"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='SWARM_', case_sensitive=False)

    log_level: str = Field(default='INFO', description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    log_format: LogFormat = Field(default=LogFormat.standard, description="Logging format")
    debug: bool = Field(default=False, description="Global debug flag")

# --- LLMConfig ---
class LLMConfig(BaseModel):
    """Configuration for a specific LLM profile."""
    provider: Optional[str] = "openai"
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: Optional[int] = None # Max tokens supported by model
    temperature: Optional[float] = 0.7
    cost: Optional[float] = None
    speed: Optional[float] = None
    intelligence: Optional[float] = None
    passthrough: Optional[bool] = False

    model_config = ConfigDict(extra='allow')

# --- Moved Tool Types Definition Higher ---
class ToolFunction(BaseModel):
    name: str
    arguments: str # Should be a JSON string

class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: ToolFunction

class ToolResult(BaseModel):
    tool_call_id: str
    role: str = "tool" # Added role for consistency
    name: Optional[str] = None # Name of the function that was called
    content: str
# --- End Tool Types ---

# AgentFunction needs Agent defined, so keep it below Agent
# AgentFunction = Callable[[], Union[str, "Agent", dict]]
AgentFunction = Callable[..., Union[str, "Agent", dict]]

class Agent(BaseModel):
    name: str = "Agent"
    model: str = "default" # LLM profile name to use
    instructions: Union[str, Callable[[], str]] = "You are a helpful agent."
    functions: List[AgentFunction] = []
    resources: List[Dict[str, Any]] = []
    tool_choice: Optional[str] = None
    parallel_tool_calls: bool = False
    mcp_servers: Optional[List[str]] = None
    env_vars: Optional[Dict[str, str]] = None
    response_format: Optional[Dict[str, Any]] = None

# --- ChatMessage Definition (Now ToolCall is defined) ---
class ChatMessage(BaseModel):
    """Represents a message in the chat history, potentially with tool calls."""
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None # For tool results
    name: Optional[str] = None # For tool results or function name
    sender: Optional[str] = None # Track the agent sending the message

    model_config = ConfigDict(extra="allow")
# --- End ChatMessage ---

class Response(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: f"response-{uuid.uuid4()}")
    messages: List[ChatMessage] = [] # Use ChatMessage type hint
    agent: Optional[Agent] = None
    context_variables: dict = {}

class Result(BaseModel):
    """
    Encapsulates the possible return values for an agent function.
    """
    value: str = ""
    agent: Optional[Agent] = None
    context_variables: dict = {}

# Re-defined Tool class
class Tool:
    def __init__(
        self,
        name: str,
        func: Callable,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
        dynamic: bool = False,
    ):
        self.name = name
        self.func = func
        self.description = description
        self.input_schema = input_schema or {"type": "object", "properties": {}} # Default schema
        self.dynamic = dynamic

    @property
    def __name__(self): return self.name
    @property
    def __code__(self): return getattr(self.func, "__code__", None)
    def __call__(self, *args, **kwargs): return self.func(*args, **kwargs)

# Type alias for tool definitions used in discovery
ToolDefinition = Dict[str, Any] # A dictionary representing a tool's schema
Resource = Dict[str, Any] # A dictionary representing a resource

