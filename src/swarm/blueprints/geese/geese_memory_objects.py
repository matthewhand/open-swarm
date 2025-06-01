import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class StoryElement:
    """Base class for elements of a story, like a scene or character note."""
    element_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StoryOutlineAct:
    """Represents a single act in a story outline."""
    act_number: int
    summary: str
    key_scenes: List[str] = field(default_factory=list)
    # You could add more structured fields like characters_introduced, setting_changes, etc.

@dataclass
class StoryOutline:
    """Represents the overall outline of the story."""
    title: str
    logline: Optional[str] = None
    themes: List[str] = field(default_factory=list)
    acts: List[StoryOutlineAct] = field(default_factory=list) # Changed from List[Dict] to List[StoryOutlineAct]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'StoryOutline':
        data = json.loads(json_str)
        # Reconstruct StoryOutlineAct instances if acts are just dicts
        if 'acts' in data and data['acts'] and isinstance(data['acts'][0], dict):
            data['acts'] = [StoryOutlineAct(**act_data) for act_data in data['acts']]
        return cls(**data)


@dataclass
class StoryContext:
    """Holds the evolving context of the story being generated."""
    user_prompt: str
    current_iteration: int = 0
    outline: Optional[StoryOutline] = None
    story_elements: List[StoryElement] = field(default_factory=list) # e.g., character bios, world details
    working_draft_parts: Dict[str, str] = field(default_factory=dict) # e.g., {"act_1_scene_1": "text..."}
    feedback_log: List[str] = field(default_factory=list)

@dataclass
class StoryOutput:
    """Represents the final output of the story generation process."""
    title: str
    final_story: str
    outline_json: Optional[str] = None # JSON string of the StoryOutline
    word_count: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict) # e.g., generation time, model used

    def to_dict(self) -> Dict[str, Any]:
        """Converts the StoryOutput to a dictionary, useful for AgentInteraction data."""
        return asdict(self)

