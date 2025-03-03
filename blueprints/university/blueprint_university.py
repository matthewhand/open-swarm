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
from blueprints.university.model_queries import (
    search_courses, search_students, search_teaching_units, search_topics,
    search_learning_objectives, search_subtopics, search_enrollments,
    search_assessment_items, extended_comprehensive_search, comprehensive_search
)

try:
    from blueprints.university.models import Topic, LearningObjective, Subtopic, Course, TeachingUnit
except Exception as e:
    from django.core.exceptions import AppRegistryNotReady
    if isinstance(e, AppRegistryNotReady):
        import django
        django.setup()
        try:
            from blueprints.university.models import Topic, LearningObjective, Subtopic, Course, TeachingUnit
        except Exception as e2:
            logger.warning("Django models unavailable after setup—running without database access.")
            Topic = LearningObjective = Subtopic = Course = TeachingUnit = None
    else:
        logger.warning("Django models unavailable—running without database access.")
        Topic = LearningObjective = Subtopic = Course = TeachingUnit = None

class UniversitySupportBlueprint(Blueprint):
    @property
    def metadata(self) -> Dict[str, Any]:
        logger.debug("Fetching metadata")
        return {
            "title": "University Support System",
            "description": "A multi-agent system for university support, using LLM-driven responses, SQLite tools, and Canvas metadata with graceful failure.",
            "required_mcp_servers": ["sqlite"],
            "cli_name": "uni",
            "env_vars": ["SQLITE_DB_PATH", "SUPPORT_EMAIL"],
            "urls_module": "blueprints.university.urls",
            "url_prefix": "v1/university/"
        }

    def run_with_context(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        logger.debug(f"Running with context. Messages: {json.dumps(messages, indent=2) if messages else 'None'}, Context: {json.dumps(context_variables, indent=2) if context_variables else 'None'}")
        try:
            if not isinstance(messages, list):
                logger.error(f"Invalid messages type: {type(messages)}. Expected list.")
                raise ValueError("Messages must be a list")
            if not isinstance(context_variables, dict):
                logger.error(f"Invalid context_variables type: {type(context_variables)}. Expected dict.")
                raise ValueError("context_variables must be a dictionary")

            channel_id, user_name = self.extract_metadata(context_variables, messages)
            context_variables["channel_id"] = channel_id
            context_variables["user_name"] = user_name
            logger.debug(f"Set context variables: channel_id={channel_id}, user_name={user_name}")

            result = super().run_with_context(messages, context_variables)
            logger.debug(f"run_with_context completed successfully, result type: {type(result)}")
            return result
        except Exception as e:
            logger.error(f"Failed in run_with_context: {str(e)}", exc_info=True)
            return {"error": f"Failed to process request: {str(e)}"}

    def extract_metadata(self, context_variables: dict, messages: List[Dict[str, Any]]) -> Tuple[str, Optional[str]]:
        """Extract channel_id and user_name with robust fallback."""
        logger.debug(f"Extracting metadata. Context: {json.dumps(context_variables, indent=2) if context_variables else 'None'}")
        default_channel_id = None
        default_user_name = None

        try:
            payload = context_variables or {}
            channel_id = jmespath.search("metadata.channelInfo.channelId", payload) or default_channel_id
            user_name = jmespath.search("metadata.userInfo.userName", payload) or default_user_name
            logger.debug(f"JMESPath search results: channel_id={channel_id}, user_name={user_name}")

            if channel_id != default_channel_id and user_name is not None:
                logger.debug("Metadata extracted from top-level context")
                return channel_id, user_name

            if not messages or not isinstance(messages, list):
                logger.debug("No valid messages provided for fallback extraction")
                return channel_id, user_name

            for message in messages:
                if not isinstance(message, dict):
                    logger.warning(f"Skipping invalid message format: {type(message)}")
                    continue
                if message.get("role") == "assistant" and "tool_calls" in message:
                    for tool_call in message.get("tool_calls", []):
                        if not isinstance(tool_call, dict) or tool_call.get("type") != "function":
                            continue
                        func_name = tool_call.get("function", {}).get("name")
                        if func_name == "get_learning_objectives":
                            try:
                                args = json.loads(tool_call["function"].get("arguments", "{}"))
                                channel_id = args.get("channelId", channel_id)
                                logger.debug(f"Extracted channel_id from tool call: {channel_id}")
                            except (json.JSONDecodeError, KeyError) as e:
                                logger.warning(f"Failed to parse channel_id from tool call: {str(e)}")
                        elif func_name == "get_student_metadata":
                            try:
                                args = json.loads(tool_call["function"].get("arguments", "{}"))
                                user_name = args.get("username", user_name)
                                logger.debug(f"Extracted user_name from tool call: {user_name}")
                            except (json.JSONDecodeError, KeyError) as e:
                                logger.warning(f"Failed to parse user_name from tool call: {str(e)}")

            logger.debug(f"Final metadata: channel_id={channel_id}, user_name={user_name}")
            return channel_id, user_name
        except Exception as e:
            logger.error(f"Metadata extraction failed: {str(e)}", exc_info=True)
            return default_channel_id, default_user_name

    def get_teaching_prompt(self, channel_id: str) -> str:
        """Retrieve teaching prompt for units, focusing on teaching_prompt field."""
        logger.debug(f"Fetching teaching prompt for channel_id: {channel_id}")
        try:
            if not isinstance(channel_id, str):
                logger.warning(f"Invalid channel_id type: {type(channel_id)}. Using None as fallback.")
                channel_id = None

            units = search_teaching_units(channel_id)
            logger.debug(f"Search results for channel_id {channel_id}: {units}")
            if not units or not isinstance(units, list):
                logger.debug("No units found, attempting null channel_id fallback")
                units = search_teaching_units(None)
                if not units or not isinstance(units, list):
                    logger.debug("No units with NULL channel_id, falling back to all units")
                    if TeachingUnit and hasattr(TeachingUnit, 'objects'):
                        units = TeachingUnit.objects.all().values("code", "name", "channel_id", "teaching_prompt", "id")
                        units = list(units)
                    else:
                        units = []

            all_prompts = []
            teaching_unit_ids = []
            for unit in units:
                if not isinstance(unit, dict):
                    logger.warning(f"Skipping invalid unit format: {type(unit)}")
                    continue
                prompt = unit.get("teaching_prompt")
                name = unit.get("name", "Unnamed Unit")
                unit_id = unit.get("id")
                if prompt:
                    all_prompts.append(f"- **Teaching Unit ({name}):** {prompt}")
                else:
                    logger.debug(f"No teaching_prompt for unit: {name}")
                if unit_id:
                    teaching_unit_ids.append(unit_id)

            prompt = "\n".join(all_prompts) if all_prompts else "No specific teaching prompts found."
            logger.debug(f"Constructed teaching prompt: {prompt}")
            return prompt
        except Exception as e:
            logger.error(f"Failed to fetch teaching prompt: {str(e)}", exc_info=True)
            return "Failed to retrieve teaching prompt due to an unexpected error."

    def get_related_prompts(self, channel_id: str) -> str:
        """Retrieve related prompts (courses, topics, subtopics) with enhanced durability."""
        logger.debug(f"Fetching related prompts for channel_id: {channel_id}")
        try:
            if not isinstance(channel_id, str):
                logger.warning(f"Invalid channel_id type: {type(channel_id)}. Using None as fallback.")
                channel_id = None

            teaching_units = search_teaching_units(channel_id)
            logger.debug(f"Teaching units for channel_id {channel_id}: {teaching_units}")
            if not teaching_units or not isinstance(teaching_units, list):
                logger.debug("No units found, attempting null channel_id fallback")
                teaching_units = search_teaching_units(None)
                if not teaching_units or not isinstance(teaching_units, list):
                    logger.debug("No units with NULL channel_id, falling back to all units")
                    if TeachingUnit and hasattr(TeachingUnit, 'objects'):
                        teaching_units = TeachingUnit.objects.all().values("code", "name", "channel_id", "teaching_prompt", "id")
                        teaching_units = list(teaching_units)
                    else:
                        teaching_units = []

            all_prompts = []
            for teaching_unit in teaching_units:
                if not isinstance(teaching_unit, dict) or "id" not in teaching_unit:
                    logger.warning(f"Skipping invalid teaching unit format: {teaching_unit}")
                    continue
                teaching_unit_id = teaching_unit["id"]
                logger.debug(f"Processing teaching unit ID: {teaching_unit_id}")

                # Courses
                if Course and hasattr(Course, 'objects'):
                    related_courses = Course.objects.filter(teaching_units__id=teaching_unit_id)
                    courses_prompts = [
                        f"- **Course: {course.name}**: {course.teaching_prompt}"
                        for course in related_courses if hasattr(course, "teaching_prompt") and course.teaching_prompt
                    ]
                    all_prompts.extend(courses_prompts)
                    logger.debug(f"Courses for unit {teaching_unit_id}: {len(courses_prompts)} found")
                else:
                    logger.debug("Course model unavailable—skipping course prompts")

                # Topics
                if Topic and hasattr(Topic, 'objects'):
                    related_topics = Topic.objects.filter(teaching_unit__id=teaching_unit_id)
                    topics_prompts = [
                        f"- **Topic: {topic.name}**: {topic.teaching_prompt}"
                        for topic in related_topics if hasattr(topic, "teaching_prompt") and topic.teaching_prompt
                    ]
                    all_prompts.extend(topics_prompts)
                    logger.debug(f"Topics for unit {teaching_unit_id}: {len(topics_prompts)} found")
                else:
                    logger.debug("Topic model unavailable—skipping topic prompts")

                # Subtopics
                if Subtopic and hasattr(Subtopic, 'objects') and Topic:
                    related_subtopics = Subtopic.objects.filter(topic__in=related_topics)
                    subtopics_prompts = [
                        f"  - **Subtopic: {subtopic.name}**: {subtopic.teaching_prompt}"
                        for subtopic in related_subtopics if hasattr(subtopic, "teaching_prompt") and subtopic.teaching_prompt
                    ]
                    all_prompts.extend(subtopics_prompts)
                    logger.debug(f"Subtopics for unit {teaching_unit_id}: {len(subtopics_prompts)} found")
                else:
                    logger.debug("Subtopic model unavailable—skipping subtopic prompts")

            if not all_prompts:
                logger.warning("No related prompts constructed across all units")
                return "No related teaching content (courses, topics, subtopics) found."
            formatted_prompts = "\n".join(all_prompts)
            logger.debug(f"Final related prompts: {formatted_prompts}")
            return formatted_prompts
        except Exception as e:
            logger.error(f"Failed to fetch related prompts: {str(e)}", exc_info=True)
            return "Failed to retrieve related information due to an unexpected error."

    def get_learning_objectives(self, channel_id: str) -> str:
        """Retrieve learning objectives separately for explicit inclusion in agent instructions."""
        logger.debug(f"Fetching learning objectives for channel_id: {channel_id}")
        try:
            if not isinstance(channel_id, str):
                logger.warning(f"Invalid channel_id type: {type(channel_id)}. Using None as fallback.")
                channel_id = None

            units = search_teaching_units(channel_id)
            logger.debug(f"Teaching units for channel_id {channel_id}: {units}")
            if not units or not isinstance(units, list):
                logger.debug("No units found, attempting null channel_id fallback")
                units = search_teaching_units(None)
                if not units or not isinstance(units, list):
                    logger.debug("No units with NULL channel_id, falling back to all units")
                    if TeachingUnit and hasattr(TeachingUnit, 'objects'):
                        units = TeachingUnit.objects.all().values("code", "name", "channel_id", "teaching_prompt", "id")
                        units = list(units)
                    else:
                        units = []

            teaching_unit_ids = [unit.get("id") for unit in units if isinstance(unit, dict) and "id" in unit]
            logger.debug(f"Extracted teaching unit IDs: {teaching_unit_ids}")
            if not teaching_unit_ids:
                logger.warning("No valid teaching unit IDs found")
                return "No learning objectives found."

            if LearningObjective and Topic and hasattr(LearningObjective, 'objects') and hasattr(Topic, 'objects'):
                related_topics = Topic.objects.filter(teaching_unit__id__in=teaching_unit_ids)
                related_learning_objectives = LearningObjective.objects.filter(topic__in=related_topics)
                learning_objectives_text = [
                    f"  - **Learning Objective:** {objective.description}"
                    for objective in related_learning_objectives if hasattr(objective, "description")
                ]
            else:
                logger.debug("LearningObjective or Topic model unavailable—returning empty objectives")
                learning_objectives_text = []

            if not learning_objectives_text:
                logger.warning("No learning objectives constructed")
                return "No learning objectives found."
            formatted_objectives = "\n".join(learning_objectives_text)
            logger.debug(f"Final learning objectives: {formatted_objectives}")
            return formatted_objectives
        except Exception as e:
            logger.error(f"Failed to fetch learning objectives: {str(e)}", exc_info=True)
            return "Failed to retrieve learning objectives due to an unexpected error."

    def create_agents(self) -> Dict[str, Agent]:
        """Create agents with comprehensive instructions including base, teaching+related, and objectives."""
        logger.debug("Creating agents")
        agents = {}

        support_email = os.getenv("SUPPORT_EMAIL", "support@swarm-university")
        logger.debug(f"Support email set to: {support_email}")

        def handoff_to_support() -> Agent:
            logger.debug("Handoff to SupportAgent initiated")
            return agents.get("SupportAgent", agents["TriageAgent"])

        def handoff_to_learning() -> Agent:
            logger.debug("Handoff to LearningAgent initiated")
            return agents.get("LearningAgent", agents["TriageAgent"])

        def handoff_to_triage() -> Agent:
            logger.debug("Handoff to TriageAgent initiated")
            return agents["TriageAgent"]

        base_instructions = (
            "You are a university support agent with access to teaching prompts, related content (courses, topics, subtopics), "
            "and learning objectives retrieved dynamically from the database based on the current channel ID. Greet the user "
            "with their name (slackUser.userName) if available at the start of your response. Use all available content below "
            "to provide comprehensive answers. For queries about 'learning objectives' or 'objectives', include the specific "
            "learning objectives listed below. If any section lacks content, leverage the other sections to ensure a helpful "
            "response. Avoid using contractions in your responses for a professional tone. Respond using full words without contractions. "
            "For example, use \"do not\" instead of \"don't\", \"cannot\" instead of \"can't\", and \"will not\" instead of \"won't\"."
        )
        logger.debug("Base instructions defined")

        triage_instructions = (
            "You are TriageAgent, the coordinator for university support. Analyze student queries and preloaded metadata "
            "from the message history. For complex queries (over 50 words), urgent queries (contains 'urgent'), or requests "
            f"for human help ('help' or 'complex issue'), respond with 'Contact {support_email}'. For general academic "
            "queries (courses, schedules), delegate to SupportAgent by calling handoff_to_support(). For detailed "
            "learning/assessment queries beyond objectives, delegate to LearningAgent by calling handoff_to_learning(). "
            "When asked to list your functions or tools, respond with: 'My functions are: handoff_to_support, "
            "handoff_to_learning, search_courses, search_teaching_units'."
        )
        agents["TriageAgent"] = Agent(
            name="TriageAgent",
            instructions=lambda context: (
                f"{triage_instructions}\n\n"
                f"**Base Instructions:**\n{base_instructions}\n\n"
                f"**Teaching Prompts and Related Content (Courses, Topics, Subtopics):**\n"
                f"{self.get_teaching_prompt(context.get('channel_id', 'default'))}\n"
                f"{self.get_related_prompts(context.get('channel_id', 'default'))}\n\n"
                f"**Learning Objectives:**\n"
                f"{self.get_learning_objectives(context.get('channel_id', 'default'))}"
            ),
            functions=[
                handoff_to_support,
                handoff_to_learning,
                search_courses,
                search_teaching_units
            ]
        )
        logger.debug("TriageAgent created")

        support_instructions = (
            "You are SupportAgent, handling general university support. Answer queries about courses, schedules, enrollments, "
            "and student info using SQLite tools. If data is unavailable, say 'I could not access the latest info, but here is "
            "some advice...' and use the provided content below. For detailed learning/assessment queries, delegate to "
            "LearningAgent by calling handoff_to_learning(). For queries requiring coordination, delegate to TriageAgent "
            "by calling handoff_to_triage()."
        )
        agents["SupportAgent"] = Agent(
            name="SupportAgent",
            instructions=lambda context: (
                f"{support_instructions}\n\n"
                f"**Base Instructions:**\n{base_instructions}\n\n"
                f"**Teaching Prompts and Related Content (Courses, Topics, Subtopics):**\n"
                f"{self.get_teaching_prompt(context.get('channel_id', 'default'))}\n"
                f"{self.get_related_prompts(context.get('channel_id', 'default'))}\n\n"
                f"**Learning Objectives:**\n"
                f"{self.get_learning_objectives(context.get('channel_id', 'default'))}"
            ),
            functions=[
                handoff_to_triage,
                handoff_to_learning,
                search_courses,
                search_teaching_units,
                search_students,
                search_enrollments,
                search_assessment_items,
                comprehensive_search
            ]
        )
        logger.debug("SupportAgent created")

        learning_instructions = (
            "You are LearningAgent, specializing in learning objectives and assessments. For assessment-related queries beyond "
            "objectives, provide detailed support using available tools and the content below. For general academic queries "
            "(courses, schedules), delegate to SupportAgent by calling handoff_to_support(). For queries requiring coordination, "
            "delegate to TriageAgent by calling handoff_to_triage()."
        )
        agents["LearningAgent"] = Agent(
            name="LearningAgent",
            instructions=lambda context: (
                f"{learning_instructions}\n\n"
                f"**Base Instructions:**\n{base_instructions}\n\n"
                f"**Teaching Prompts and Related Content (Courses, Topics, Subtopics):**\n"
                f"{self.get_teaching_prompt(context.get('channel_id', 'default'))}\n"
                f"{self.get_related_prompts(context.get('channel_id', 'default'))}\n\n"
                f"**Learning Objectives:**\n"
                f"{self.get_learning_objectives(context.get('channel_id', 'default'))}"
            ),
            functions=[
                handoff_to_triage,
                handoff_to_support,
                search_learning_objectives,
                search_topics,
                search_subtopics,
                extended_comprehensive_search
            ]
        )
        logger.debug("LearningAgent created")

        self.set_starting_agent(agents["TriageAgent"])
        logger.info("Agents created successfully: TriageAgent, SupportAgent, LearningAgent")
        return agents

if __name__ == "__main__":
    logger.debug("Starting main execution")
    try:
        UniversitySupportBlueprint.main()
        logger.info("Blueprint execution completed")
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}", exc_info=True)

