"""
University Support Blueprint

A multi-agent system providing university support using LLM-driven responses, SQLite-backed tools,
and Canvas metadata integration, with graceful failure for all operations.
"""

import os
import sys
import logging
import json
import jmespath
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    stream_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

try:
    import django
    from django.apps import apps
    if not os.environ.get('DJANGO_SETTINGS_MODULE') or not apps.ready:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
        django.setup()
except Exception as e:
    logger.warning(f"Django setup failed: {e}. Proceeding without Django context.")

from swarm.types import Agent
from swarm.extensions.blueprint.blueprint_base import BlueprintBase as Blueprint
# Ensure model_queries functions are correctly imported
from blueprints.university.model_queries import (
    search_courses, search_students, search_teaching_units, search_topics,
    search_learning_objectives, search_subtopics, search_enrollments,
    search_assessment_items, extended_comprehensive_search, comprehensive_search
)

# Attempt to import models with error handling for Django setup issues
try:
    from blueprints.university.models import Topic, LearningObjective, Subtopic, Course, TeachingUnit
except Exception as e:
    # Catch potential Django AppRegistryNotReady error
    from django.core.exceptions import AppRegistryNotReady
    if isinstance(e, AppRegistryNotReady):
        logger.warning("Django AppRegistryNotReady caught. Attempting django.setup() again.")
        try:
            import django
            django.setup()
            # Retry import after setup
            from blueprints.university.models import Topic, LearningObjective, Subtopic, Course, TeachingUnit
        except Exception as e2:
            logger.error(f"Django models still unavailable after retry: {e2}. Running without database access.")
            Topic = LearningObjective = Subtopic = Course = TeachingUnit = None
    else:
        logger.error(f"Failed to import Django models: {e}. Running without database access.")
        Topic = LearningObjective = Subtopic = Course = TeachingUnit = None

class UniversitySupportBlueprint(Blueprint):
    def register_blueprint_urls(self):
        # Placeholder: Implement Django URL registration if needed by this blueprint
        logger.debug("UniversitySupportBlueprint: register_blueprint_urls called (no-op)")
        pass

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "University Support System",
            "description": "A multi-agent system for university support, using LLM-driven responses, SQLite tools, and Canvas metadata with graceful failure.",
            "required_mcp_servers": ["sqlite"], # Assuming sqlite is handled via Django ORM
            "cli_name": "uni",
            "env_vars": ["SQLITE_DB_PATH", "SUPPORT_EMAIL"], # SQLITE_DB_PATH might be implicit via Django settings
            "django_modules": {
                "models": "blueprints.university.models",
                "views": "blueprints.university.views",
                "urls": "blueprints.university.urls",
                "serializers": "blueprints.university.serializers"
            },
            "url_prefix": "v1/university/"
        }

    def run_with_context(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        # Ensure context variables are updated before calling super() or running logic
        logger.debug(f"Running UniversitySupportBlueprint with context. Messages: {len(messages)}, Context keys: {list(context_variables.keys())}")
        try:
            if not isinstance(messages, list):
                logger.error(f"Invalid messages type: {type(messages)}. Expected list.")
                raise ValueError("Messages must be a list")
            if not isinstance(context_variables, dict):
                logger.error(f"Invalid context_variables type: {type(context_variables)}. Expected dict.")
                raise ValueError("context_variables must be a dictionary")

            # Extract metadata and update context *before* potentially calling super().run_with_context
            channel_id, user_name = self.extract_metadata(context_variables, messages)
            context_variables["channel_id"] = channel_id
            context_variables["user_name"] = user_name
            logger.debug(f"Updated context variables: channel_id={channel_id}, user_name={user_name}")

            # Now call the parent class's run_with_context, passing the updated context
            result = super().run_with_context(messages, context_variables)
            logger.debug(f"super().run_with_context completed successfully, result type: {type(result)}")
            return result
        except Exception as e:
            logger.error(f"Failed in UniversitySupportBlueprint run_with_context: {str(e)}", exc_info=True)
            # Return a structured error response
            return {"error": f"Failed to process request: {str(e)}"}

    def extract_metadata(self, context_variables: dict, messages: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
        """Extract channel_id and user_name with robust fallback."""
        logger.debug(f"Extracting metadata. Context: {json.dumps(context_variables, indent=2) if context_variables else 'None'}")
        channel_id: Optional[str] = None
        user_name: Optional[str] = None

        try:
            payload = context_variables or {}
            # Attempt to extract from top-level context first
            channel_id = jmespath.search("metadata.channelInfo.channelId", payload)
            user_name = jmespath.search("metadata.userInfo.userName", payload)
            logger.debug(f"JMESPath search results: channel_id={channel_id}, user_name={user_name}")

            # Fallback to searching messages if not found in context
            if (channel_id is None or user_name is None) and messages and isinstance(messages, list):
                logger.debug("Metadata not fully found in context, searching messages...")
                for message in reversed(messages): # Search recent messages first
                    if not isinstance(message, dict): continue

                    # Example: Check tool calls for specific arguments
                    if message.get("role") == "assistant" and "tool_calls" in message:
                        for tool_call in message.get("tool_calls", []):
                            if not isinstance(tool_call, dict) or tool_call.get("type") != "function": continue
                            func_name = tool_call.get("function", {}).get("name")
                            try:
                                args = json.loads(tool_call["function"].get("arguments", "{}"))
                                if channel_id is None and func_name == "get_learning_objectives": # Example function name
                                    channel_id = args.get("channelId", channel_id)
                                    if channel_id: logger.debug(f"Extracted channel_id from tool call: {channel_id}")
                                if user_name is None and func_name == "get_student_metadata": # Example function name
                                    user_name = args.get("username", user_name)
                                    if user_name: logger.debug(f"Extracted user_name from tool call: {user_name}")
                            except (json.JSONDecodeError, KeyError, TypeError) as e:
                                logger.warning(f"Failed to parse args or extract metadata from tool call ({func_name}): {e}")
                    # Stop searching if both found
                    if channel_id is not None and user_name is not None:
                        break

            logger.debug(f"Final extracted metadata: channel_id={channel_id}, user_name={user_name}")
            return channel_id, user_name
        except Exception as e:
            logger.error(f"Metadata extraction failed unexpectedly: {str(e)}", exc_info=True)
            return None, None # Return None on error

    def get_teaching_prompt(self, channel_id: Optional[str]) -> str:
        """Retrieve teaching prompt for units, handling potential None channel_id."""
        logger.debug(f"Fetching teaching prompt for channel_id: {channel_id}")
        prompt_parts = []
        try:
            # Ensure channel_id is str or None
            if not isinstance(channel_id, (str, type(None))):
                logger.warning(f"Invalid channel_id type: {type(channel_id)}. Using None.")
                channel_id = None

            # Use the imported search function
            units = search_teaching_units(channel_id=channel_id) # Pass explicitly
            logger.debug(f"Search results for channel_id '{channel_id}': {len(units)} units")

            if not units: # If no units found for the specific channel_id, try with None
                 logger.debug(f"No units found for channel_id '{channel_id}', trying channel_id=None")
                 units = search_teaching_units(channel_id=None)
                 logger.debug(f"Search results for channel_id=None: {len(units)} units")

            # If still no units, maybe fetch all as a last resort (or return specific message)
            if not units and TeachingUnit and hasattr(TeachingUnit, 'objects'):
                 logger.debug("No units found for specific or None channel_id, fetching all units.")
                 units_qs = TeachingUnit.objects.all().values("id", "name", "teaching_prompt")
                 units = list(units_qs) # Convert QuerySet to list of dicts
                 logger.debug(f"Fetched all units: {len(units)} units")


            if not units:
                 return "No teaching units found for this context."

            for unit in units:
                 if isinstance(unit, dict) and unit.get("teaching_prompt"):
                     prompt_parts.append(f"- **Teaching Unit ({unit.get('name', 'Unnamed')}):** {unit['teaching_prompt']}")
                 elif isinstance(unit, dict):
                     logger.debug(f"Teaching unit '{unit.get('name', 'Unnamed')}' has no teaching_prompt.")
                 else:
                      logger.warning(f"Skipping invalid unit data: {unit}")

            final_prompt = "\n".join(prompt_parts) if prompt_parts else "No specific teaching prompts found for relevant units."
            logger.debug(f"Constructed teaching prompt:\n{final_prompt}")
            return final_prompt

        except Exception as e:
            logger.error(f"Failed to fetch teaching prompt: {str(e)}", exc_info=True)
            return "Error: Failed to retrieve teaching prompt."

    def get_related_prompts(self, channel_id: Optional[str]) -> str:
        """Retrieve related prompts (courses, topics, subtopics), handling potential None channel_id."""
        logger.debug(f"Fetching related prompts for channel_id: {channel_id}")
        all_prompts = []
        teaching_unit_ids = set() # Use set for efficiency

        try:
            if not isinstance(channel_id, (str, type(None))):
                logger.warning(f"Invalid channel_id type: {type(channel_id)}. Using None.")
                channel_id = None

            # Get relevant teaching units (specific, None, or all as fallback)
            teaching_units = search_teaching_units(channel_id=channel_id)
            if not teaching_units:
                 teaching_units = search_teaching_units(channel_id=None)
            # Add fallback to all units only if models are available
            if not teaching_units and TeachingUnit and hasattr(TeachingUnit, 'objects'):
                 units_qs = TeachingUnit.objects.all().values("id")
                 teaching_units = list(units_qs)

            if not teaching_units:
                 return "No relevant teaching units found to get related prompts."

            # Collect IDs from valid units
            for unit in teaching_units:
                 if isinstance(unit, dict) and "id" in unit:
                     teaching_unit_ids.add(unit["id"])

            if not teaching_unit_ids:
                return "No valid teaching unit IDs found."

            logger.debug(f"Processing related prompts for teaching unit IDs: {teaching_unit_ids}")

            # Fetch related items based on collected unit IDs
            related_courses = []
            if Course and hasattr(Course, 'objects'):
                 try:
                     related_courses = Course.objects.filter(teaching_units__id__in=list(teaching_unit_ids)).only("name", "teaching_prompt")
                     course_prompts = [f"- **Course: {c.name}**: {c.teaching_prompt}" for c in related_courses if c.teaching_prompt]
                     all_prompts.extend(course_prompts)
                     logger.debug(f"Found {len(course_prompts)} course prompts.")
                 except Exception as e:
                      logger.error(f"Error fetching courses: {e}")
            else: logger.debug("Course model unavailable.")

            related_topics = []
            topic_ids = []
            if Topic and hasattr(Topic, 'objects'):
                 try:
                     related_topics = Topic.objects.filter(teaching_unit__id__in=list(teaching_unit_ids)).only("id", "name", "teaching_prompt")
                     topic_ids = [t.id for t in related_topics]
                     topic_prompts = [f"- **Topic: {t.name}**: {t.teaching_prompt}" for t in related_topics if t.teaching_prompt]
                     all_prompts.extend(topic_prompts)
                     logger.debug(f"Found {len(topic_prompts)} topic prompts.")
                 except Exception as e:
                      logger.error(f"Error fetching topics: {e}")
            else: logger.debug("Topic model unavailable.")

            if Subtopic and hasattr(Subtopic, 'objects') and topic_ids: # Check if topic_ids were found
                 try:
                     related_subtopics = Subtopic.objects.filter(topic_id__in=topic_ids).only("name", "teaching_prompt")
                     subtopic_prompts = [f"  - **Subtopic: {s.name}**: {s.teaching_prompt}" for s in related_subtopics if s.teaching_prompt]
                     all_prompts.extend(subtopic_prompts)
                     logger.debug(f"Found {len(subtopic_prompts)} subtopic prompts.")
                 except Exception as e:
                      logger.error(f"Error fetching subtopics: {e}")
            elif not topic_ids: logger.debug("No topics found, skipping subtopic search.")
            else: logger.debug("Subtopic model unavailable.")

            if not all_prompts:
                return "No related teaching content (courses, topics, subtopics) found."

            formatted_prompts = "\n".join(all_prompts)
            logger.debug(f"Final related prompts:\n{formatted_prompts}")
            return formatted_prompts

        except Exception as e:
            logger.error(f"Failed to fetch related prompts: {str(e)}", exc_info=True)
            return "Error: Failed to retrieve related information."


    def get_learning_objectives(self, channel_id: Optional[str]) -> str:
        """Retrieve learning objectives, handling potential None channel_id."""
        logger.debug(f"Fetching learning objectives for channel_id: {channel_id}")
        teaching_unit_ids = set()

        try:
            if not isinstance(channel_id, (str, type(None))):
                logger.warning(f"Invalid channel_id type: {type(channel_id)}. Using None.")
                channel_id = None

            # Get relevant teaching units (specific, None, or all)
            teaching_units = search_teaching_units(channel_id=channel_id)
            if not teaching_units:
                teaching_units = search_teaching_units(channel_id=None)
            if not teaching_units and TeachingUnit and hasattr(TeachingUnit, 'objects'):
                 units_qs = TeachingUnit.objects.all().values("id")
                 teaching_units = list(units_qs)

            if not teaching_units:
                 return "No relevant teaching units found to get learning objectives."

            for unit in teaching_units:
                 if isinstance(unit, dict) and "id" in unit:
                     teaching_unit_ids.add(unit["id"])

            if not teaching_unit_ids:
                return "No valid teaching unit IDs found for learning objectives."

            logger.debug(f"Processing learning objectives for teaching unit IDs: {teaching_unit_ids}")

            # Fetch objectives based on unit IDs
            learning_objectives_text = []
            if LearningObjective and Topic and hasattr(LearningObjective, 'objects') and hasattr(Topic, 'objects'):
                 try:
                     # Find topics linked to the relevant teaching units
                     topic_ids = list(Topic.objects.filter(teaching_unit__id__in=list(teaching_unit_ids)).values_list('id', flat=True))
                     if topic_ids:
                         # Find learning objectives linked to those topics
                         related_los = LearningObjective.objects.filter(topic_id__in=topic_ids).only("description")
                         learning_objectives_text = [f"  - **Learning Objective:** {lo.description}" for lo in related_los if lo.description]
                         logger.debug(f"Found {len(learning_objectives_text)} learning objectives.")
                     else:
                         logger.debug("No topics found for the relevant teaching units.")
                 except Exception as e:
                      logger.error(f"Error fetching learning objectives: {e}")
            else:
                logger.debug("LearningObjective or Topic model unavailable.")

            if not learning_objectives_text:
                return "No learning objectives found for this context."

            formatted_objectives = "\n".join(learning_objectives_text)
            logger.debug(f"Final learning objectives:\n{formatted_objectives}")
            return formatted_objectives

        except Exception as e:
            logger.error(f"Failed to fetch learning objectives: {str(e)}", exc_info=True)
            return "Error: Failed to retrieve learning objectives."

    def create_agents(self) -> Dict[str, Agent]:
        """Create agents with instructions dynamically fetching context."""
        logger.debug("Creating agents for UniversitySupportBlueprint")
        agents = {}
        support_email = os.getenv("SUPPORT_EMAIL", "support@example.com") # Use a default placeholder

        # Define handoff functions (which are AgentFunctions)
        def handoff_to_support() -> Agent:
            logger.debug("Handoff to SupportAgent initiated")
            return agents.get("SupportAgent", agents["TriageAgent"]) # Fallback to Triage

        def handoff_to_learning() -> Agent:
            logger.debug("Handoff to LearningAgent initiated")
            return agents.get("LearningAgent", agents["TriageAgent"]) # Fallback to Triage

        def handoff_to_triage() -> Agent:
            logger.debug("Handoff back to TriageAgent initiated")
            return agents["TriageAgent"]

        # Base instructions (static part)
        base_instructions = (
            "You are a university support agent. Use the context provided below (teaching prompts, related content, learning objectives) "
            "which is dynamically retrieved based on the current conversation channel. Greet the user by name (context variable 'user_name') if available. "
            "Answer questions comprehensively using all available sections. If a section is missing, rely on others. "
            "Respond professionally without contractions (e.g., use 'do not' instead of 'don't')."
        )

        # Dynamic instruction builder using context
        def build_instructions(agent_specific_instructions: str, context: dict) -> str:
            channel_id = context.get('channel_id') # Get channel_id from context passed by Swarm/BlueprintBase
            user_name = context.get('user_name') # Get user_name
            greeting = f"Hello {user_name}. " if user_name else ""

            teaching_prompt = self.get_teaching_prompt(channel_id)
            related_prompts = self.get_related_prompts(channel_id)
            learning_objectives = self.get_learning_objectives(channel_id)

            return (
                f"{greeting}{agent_specific_instructions}\n\n"
                f"**Base Instructions:**\n{base_instructions}\n\n"
                f"**Teaching Prompts:**\n{teaching_prompt}\n\n"
                f"**Related Content (Courses, Topics, Subtopics):**\n{related_prompts}\n\n"
                f"**Learning Objectives:**\n{learning_objectives}"
            )

        # Triage Agent Definition
        triage_instructions_specific = (
            "You are TriageAgent, the coordinator. Analyze queries and metadata. "
            f"For complex/urgent issues or requests for human help, respond with 'Contact {support_email}'. "
            "For general academic queries, delegate using handoff_to_support(). "
            "For detailed learning/assessment queries, delegate using handoff_to_learning(). "
            "Use your tools (search_courses, search_teaching_units) for initial information gathering if needed. "
            "List functions/tools available: handoff_to_support, handoff_to_learning, search_courses, search_teaching_units."
        )
        agents["TriageAgent"] = Agent(
            name="TriageAgent",
            instructions=lambda context: build_instructions(triage_instructions_specific, context),
            functions=[ # Handoffs are functions
                handoff_to_support,
                handoff_to_learning,
            ],
            tools=[ # Database searches are tools
                search_courses,
                search_teaching_units
            ]
            # mcp_servers can be added if needed, e.g., for memory
        )

        # Support Agent Definition
        support_instructions_specific = (
            "You are SupportAgent. Handle general queries (courses, schedules, students, enrollments) using your tools. "
            "If data is missing, provide general advice based on the context below. "
            "Delegate learning/assessment queries using handoff_to_learning(). "
            "Delegate coordination tasks using handoff_to_triage()."
        )
        agents["SupportAgent"] = Agent(
            name="SupportAgent",
            instructions=lambda context: build_instructions(support_instructions_specific, context),
            functions=[ # Handoffs
                handoff_to_triage,
                handoff_to_learning,
            ],
            tools=[ # Database searches
                search_courses, search_teaching_units, search_students,
                search_enrollments, search_assessment_items, comprehensive_search
            ]
        )

        # Learning Agent Definition
        learning_instructions_specific = (
            "You are LearningAgent. Specialize in learning objectives and assessments using your tools. "
            "Delegate general academic queries using handoff_to_support(). "
            "Delegate coordination tasks using handoff_to_triage()."
        )
        agents["LearningAgent"] = Agent(
            name="LearningAgent",
            instructions=lambda context: build_instructions(learning_instructions_specific, context),
            functions=[ # Handoffs
                handoff_to_triage,
                handoff_to_support,
            ],
            tools=[ # Database searches
                search_learning_objectives, search_topics, search_subtopics,
                extended_comprehensive_search
            ]
        )

        logger.info("Agents created: TriageAgent, SupportAgent, LearningAgent")
        self.set_starting_agent(agents["TriageAgent"])
        return agents

if __name__ == "__main__":
    logger.info("Running UniversitySupportBlueprint main...")
    try:
        # Instantiate and run using the class method
        UniversitySupportBlueprint.main()
        logger.info("UniversitySupportBlueprint main finished.")
    except Exception as e:
        logger.critical(f"Error running UniversitySupportBlueprint.main: {e}", exc_info=True)
