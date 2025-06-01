import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

@dataclass
class ToolCallRequest:
    """Represents a tool call requested by an agent."""
    id: str # Unique ID for this tool call, to match with response
    tool_name: str
    tool_args: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolCallResponse:
    """Represents the result of a tool call."""
    id: str # ID matching the ToolCallRequest
    tool_name: str
    tool_result: Any
    is_error: bool = False
    error_message: Optional[str] = None

@dataclass
class AgentInteraction:
    """
    Represents a unit of interaction or output from an agent or blueprint.
    This structure is typically what's yielded from an agent's run method.
    """
    type: str = "message"  # Common types: "message", "tool_request", "tool_response", "error", "progress", "thought"
    
    # For 'message' type
    role: Optional[str] = None # e.g., "assistant", "user", "system", "tool" (for tool responses)
    content: Optional[Union[str, List[Dict[str, Any]]]] = None # Text content or structured content (e.g., for multimodal)
    
    # For 'tool_request' type
    tool_calls: Optional[List[ToolCallRequest]] = None
    
    # For 'tool_response' type (though often part of a 'message' with role 'tool')
    # tool_call_id: Optional[str] = None # ID of the tool call this is a response to
    # tool_name: Optional[str] = None
    # tool_content: Optional[str] = None # Result of the tool call as a string

    # General metadata
    final: bool = False  # Is this the final interaction in a sequence for the current turn?
    data: Optional[Dict[str, Any]] = None  # For additional structured data, metadata, or alternative representations
    
    # For 'error' type
    error_message: Optional[str] = None
    error_type: Optional[str] = None # e.g., "ValueError", "APIError"

    # For 'progress' type
    progress_message: Optional[str] = None
    progress_percent: Optional[float] = None

    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the AgentInteraction to a dictionary."""
        d = {
            "type": self.type,
            "final": self.final,
            "timestamp": self.timestamp,
        }
        if self.role is not None: d["role"] = self.role
        if self.content is not None: d["content"] = self.content
        if self.tool_calls is not None: d["tool_calls"] = [tc.__dict__ for tc in self.tool_calls]
        # if self.tool_call_id is not None: d["tool_call_id"] = self.tool_call_id
        # if self.tool_name is not None: d["tool_name"] = self.tool_name
        # if self.tool_content is not None: d["tool_content"] = self.tool_content
        if self.data is not None: d["data"] = self.data
        if self.error_message is not None: d["error_message"] = self.error_message
        if self.error_type is not None: d["error_type"] = self.error_type
        if self.progress_message is not None: d["progress_message"] = self.progress_message
        if self.progress_percent is not None: d["progress_percent"] = self.progress_percent
        return d

