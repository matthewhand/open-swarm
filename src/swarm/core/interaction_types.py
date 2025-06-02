import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field # Import Pydantic BaseModel and Field

@dataclass
class ToolCallRequest:
    """Represents a tool call requested by an agent."""
    id: str 
    tool_name: str
    tool_args: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolCallResponse:
    """Represents the result of a tool call."""
    id: str 
    tool_name: str
    tool_result: Any
    is_error: bool = False
    error_message: Optional[str] = None

@dataclass
class AgentInteraction:
    """
    Represents a unit of interaction or output from an agent or blueprint.
    """
    type: str = "message"
    role: Optional[str] = None 
    content: Optional[Union[str, List[Dict[str, Any]]]] = None
    tool_calls: Optional[List[ToolCallRequest]] = None
    final: bool = False
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    progress_message: Optional[str] = None
    progress_percent: Optional[float] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the AgentInteraction to a dictionary."""
        # Note: If tool_calls contains Pydantic models, their .model_dump() might be preferred
        # For dataclasses, __dict__ is okay but might not handle nested Pydantic models correctly.
        tool_calls_data = None
        if self.tool_calls:
            tool_calls_data = []
            for tc in self.tool_calls:
                if hasattr(tc, 'model_dump'): # Pydantic model
                    tool_calls_data.append(tc.model_dump())
                elif hasattr(tc, '__dict__'): # Dataclass
                    tool_calls_data.append(tc.__dict__)
                else: # Fallback
                    tool_calls_data.append(str(tc))

        d = {
            "type": self.type,
            "final": self.final,
            "timestamp": self.timestamp,
        }
        if self.role is not None: d["role"] = self.role
        if self.content is not None: d["content"] = self.content
        if tool_calls_data is not None: d["tool_calls"] = tool_calls_data
        if self.data is not None: d["data"] = self.data
        if self.error_message is not None: d["error_message"] = self.error_message
        if self.error_type is not None: d["error_type"] = self.error_type
        if self.progress_message is not None: d["progress_message"] = self.progress_message
        if self.progress_percent is not None: d["progress_percent"] = self.progress_percent
        return d

class StoryOutput(BaseModel):
    """
    Represents the structured output of a story generation process, like from GeeseBlueprint.
    """
    title: str
    final_story: str
    outline_json: str 
    word_count: int
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

