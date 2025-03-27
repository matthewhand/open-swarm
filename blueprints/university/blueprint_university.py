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
import asyncio

# --- Apply nest_asyncio patch ---
import nest_asyncio
nest_asyncio.apply()
# ---------------------------------

logger = logging.getLogger(__name__)
# Configure logger if needed
if not logger.handlers:
    stream_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    # logger.setLevel(logging.DEBUG)

try:
    import django
    from django.apps import apps
    if not os.environ.get('DJANGO_SETTINGS_MODULE') or not apps.ready:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
        django.setup()
except Exception as e:
    logger.warning(f"Django setup failed: {e}. Proceeding without Django context.")

from swarm.types import Agent, Response, ChatMessage
from swarm.extensions.blueprint.blueprint_base import BlueprintBase as Blueprint
from asgiref.sync import sync_to_async # Import sync_to_async here as well

# Ensure model_queries functions are correctly imported (async versions)
from blueprints.university.model_queries import (
    search_courses, search_students, search_teaching_units, search_topics,
    search_learning_objectives, search_subtopics, search_enrollments,
    search_assessment_items, extended_comprehensive_search, comprehensive_search
)

# Attempt to import models
try:
    from blueprints.university.models import Topic, LearningObjective, Subtopic, Course, TeachingUnit
    MODELS_AVAILABLE = True
except Exception as e:
    from django.core.exceptions import AppRegistryNotReady
    if isinstance(e, AppRegistryNotReady):
        logger.warning("Django AppRegistryNotReady caught during model import. Setup might be incomplete.")
    else:
        logger.error(f"Failed to import Django models: {e}. Running without database access.")
    Topic = LearningObjective = Subtopic = Course = TeachingUnit = None
    MODELS_AVAILABLE = False


class UniversitySupportBlueprint(Blueprint):
    def register_blueprint_urls(self):
        logger.debug("UniversitySupportBlueprint: register_blueprint_urls called (no-op)")
        pass

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "University Support System",
            "description": "A multi-agent system for university support, using LLM-driven responses, SQLite tools, and Canvas metadata with graceful failure.",
            "required_mcp_servers": [],
            "cli_name": "uni",
            "env_vars": ["SUPPORT_EMAIL"],
            "django_modules": {
                "models": "blueprints.university.models",
                "views": "blueprints.university.views",
                "urls": "blueprints.university.urls",
                "serializers": "blueprints.university.serializers"
            },
            "url_prefix": "v1/university/"
        }

    def extract_metadata(self, context_variables: dict, messages: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
        logger.debug(f"Extracting metadata. Context keys: {list(context_variables.keys()) if context_variables else 'None'}")
        channel_id: Optional[str] = None
        user_name: Optional[str] = None
        try:
            payload = context_variables or {}
            channel_id = jmespath.search("metadata.channelInfo.channelId", payload) or jmespath.search("channel_id", payload)
            user_name = jmespath.search("metadata.userInfo.userName", payload) or jmespath.search("user_name", payload)
            logger.debug(f"Initial metadata extraction: channel_id={channel_id}, user_name={user_name}")
            # Add fallback logic if needed
        except Exception as e:
            logger.error(f"Metadata extraction failed unexpectedly: {str(e)}", exc_info=True)
        logger.debug(f"Final extracted metadata: channel_id={channel_id}, user_name={user_name}")
        return channel_id, user_name

    async def get_teaching_prompt(self, channel_id: Optional[str]) -> str:
        logger.debug(f"Async fetching teaching prompt for channel_id: {channel_id}")
        prompt_parts = []
        try:
            if not isinstance(channel_id, (str, type(None))):
                logger.warning(f"Invalid channel_id type: {type(channel_id)}. Using None.")
                channel_id = None

            units = await search_teaching_units(channel_id=channel_id)
            if not units:
                 units = await search_teaching_units(channel_id=None)

            if not units and MODELS_AVAILABLE:
                 @sync_to_async
                 def get_all_units_sync():
                      return list(TeachingUnit.objects.all().values("id", "name", "teaching_prompt"))
                 try:
                      units = await get_all_units_sync()
                      logger.debug(f"Fetched all units as fallback: {len(units)} units")
                 except Exception as db_err:
                      logger.error(f"Error fetching all teaching units: {db_err}")
                      units = [{"error": str(db_err)}]


            if not units: return "No teaching units found for this context."

            for unit in units:
                 if isinstance(unit, dict) and 'error' in unit:
                      logger.error(f"Error retrieving teaching unit data: {unit['error']}")
                 elif isinstance(unit, dict) and unit.get("teaching_prompt"):
                     prompt_parts.append(f"- **Teaching Unit ({unit.get('name', 'Unnamed')}):** {unit['teaching_prompt']}")

            final_prompt = "\n".join(prompt_parts) if prompt_parts else "No specific teaching prompts found for relevant units."
            logger.debug(f"Constructed teaching prompt (preview): {final_prompt[:100]}...")
            return final_prompt
        except Exception as e:
            logger.error(f"Failed to fetch teaching prompt: {str(e)}", exc_info=True)
            return "Error: Failed to retrieve teaching prompt."

    async def get_related_prompts(self, channel_id: Optional[str]) -> str:
        logger.debug(f"Async fetching related prompts for channel_id: {channel_id}")
        all_prompts = []
        teaching_unit_ids = set()
        try:
            if not isinstance(channel_id, (str, type(None))): channel_id = None

            teaching_units = await search_teaching_units(channel_id=channel_id)
            if not teaching_units: teaching_units = await search_teaching_units(channel_id=None)

            unit_ids_to_query = set()
            for unit in teaching_units:
                if isinstance(unit, dict) and "id" in unit:
                    unit_ids_to_query.add(unit["id"])
                elif isinstance(unit, dict) and 'error' in unit:
                    logger.error(f"Error retrieving teaching unit ID: {unit['error']}")

            # Fallback if no specific units found
            if not unit_ids_to_query and MODELS_AVAILABLE:
                 @sync_to_async
                 def get_all_unit_ids_sync():
                      return list(TeachingUnit.objects.all().values_list("id", flat=True))
                 try:
                      unit_ids_to_query.update(await get_all_unit_ids_sync())
                      logger.debug(f"Using all unit IDs as fallback: {len(unit_ids_to_query)}")
                 except Exception as db_err:
                      logger.error(f"Error fetching all teaching unit IDs: {db_err}")


            if not unit_ids_to_query: return "No relevant teaching units found to get related prompts."

            @sync_to_async
            def get_related_data_sync(unit_ids: List[int]):
                 prompts = []
                 if not MODELS_AVAILABLE: return prompts
                 try:
                     course_qs = Course.objects.filter(teaching_units__id__in=unit_ids).only("name", "teaching_prompt")
                     prompts.extend([f"- **Course: {c.name}**: {c.teaching_prompt}" for c in course_qs if c.teaching_prompt])

                     topic_qs = Topic.objects.filter(teaching_unit__id__in=unit_ids).only("id", "name", "teaching_prompt")
                     topic_ids = [t.id for t in topic_qs]
                     prompts.extend([f"- **Topic: {t.name}**: {t.teaching_prompt}" for t in topic_qs if t.teaching_prompt])

                     if topic_ids:
                         subtopic_qs = Subtopic.objects.filter(topic_id__in=topic_ids).only("name", "teaching_prompt")
                         prompts.extend([f"  - **Subtopic: {s.name}**: {s.teaching_prompt}" for s in subtopic_qs if s.teaching_prompt])
                 except Exception as inner_e:
                      logger.error(f"Error during sync related data fetch: {inner_e}")
                 return prompts

            try:
                related_prompts_list = await get_related_data_sync(list(unit_ids_to_query))
                all_prompts.extend(related_prompts_list)
            except Exception as e:
                 logger.error(f"Error awaiting related data fetch: {e}")

            if not all_prompts: return "No related teaching content found."

            formatted_prompts = "\n".join(all_prompts)
            logger.debug(f"Final related prompts (preview): {formatted_prompts[:100]}...")
            return formatted_prompts
        except Exception as e:
            logger.error(f"Failed to fetch related prompts: {str(e)}", exc_info=True)
            return "Error: Failed to retrieve related information."

    async def get_learning_objectives(self, channel_id: Optional[str]) -> str:
        logger.debug(f"Async fetching learning objectives for channel_id: {channel_id}")
        teaching_unit_ids = set()
        try:
            if not isinstance(channel_id, (str, type(None))): channel_id = None

            teaching_units = await search_teaching_units(channel_id=channel_id)
            if not teaching_units: teaching_units = await search_teaching_units(channel_id=None)

            unit_ids_to_query = set()
            for unit in teaching_units:
                 if isinstance(unit, dict) and "id" in unit:
                     unit_ids_to_query.add(unit["id"])
                 elif isinstance(unit, dict) and 'error' in unit:
                     logger.error(f"Error retrieving teaching unit ID for LOs: {unit['error']}")

            # Fallback if no specific units found
            if not unit_ids_to_query and MODELS_AVAILABLE:
                 @sync_to_async
                 def get_all_unit_ids_sync():
                      return list(TeachingUnit.objects.all().values_list("id", flat=True))
                 try:
                      unit_ids_to_query.update(await get_all_unit_ids_sync())
                      logger.debug(f"Using all unit IDs for LOs as fallback: {len(unit_ids_to_query)}")
                 except Exception as db_err:
                      logger.error(f"Error fetching all teaching unit IDs for LOs: {db_err}")


            if not unit_ids_to_query: return "No relevant teaching units found to get learning objectives."

            @sync_to_async
            def get_los_for_units_sync(unit_ids: List[int]):
                lo_texts = []
                if not MODELS_AVAILABLE: return lo_texts
                try:
                    topic_ids = list(Topic.objects.filter(teaching_unit__id__in=unit_ids).values_list('id', flat=True))
                    if topic_ids:
                        related_los = LearningObjective.objects.filter(topic_id__in=topic_ids).only("description")
                        lo_texts = [f"  - **Learning Objective:** {lo.description}" for lo in related_los if lo.description]
                except Exception as inner_e:
                     logger.error(f"Error during sync LO fetch: {inner_e}")
                return lo_texts

            learning_objectives_text = []
            try:
                learning_objectives_text = await get_los_for_units_sync(list(unit_ids_to_query))
                logger.debug(f"Found {len(learning_objectives_text)} learning objectives.")
            except Exception as e:
                 logger.error(f"Error awaiting LO fetch: {e}")

            if not learning_objectives_text: return "No learning objectives found for this context."

            formatted_objectives = "\n".join(learning_objectives_text)
            logger.debug(f"Final learning objectives (preview): {formatted_objectives[:100]}...")
            return formatted_objectives
        except Exception as e:
            logger.error(f"Failed to fetch learning objectives: {str(e)}", exc_info=True)
            return "Error: Failed to retrieve learning objectives."

    def create_agents(self) -> Dict[str, Agent]:
        logger.debug("Creating agents for UniversitySupportBlueprint")
        agents = {}
        support_email = os.getenv("SUPPORT_EMAIL", "support@example.com")

        def handoff_to_support() -> Agent:
            logger.debug("Handoff to SupportAgent initiated")
            return agents.get("SupportAgent", agents["TriageAgent"])

        def handoff_to_learning() -> Agent:
            logger.debug("Handoff to LearningAgent initiated")
            return agents.get("LearningAgent", agents["TriageAgent"])

        def handoff_to_triage() -> Agent:
            logger.debug("Handoff back to TriageAgent initiated")
            return agents["TriageAgent"]

        async def build_instructions_async(agent_specific_instructions: str, context: dict) -> str:
            channel_id, user_name = self.extract_metadata(context, [])
            greeting = f"Hello {user_name}. " if user_name else ""
            try:
                # Gather async results concurrently
                teaching_prompt, related_prompts, learning_objectives = await asyncio.gather(
                    self.get_teaching_prompt(channel_id),
                    self.get_related_prompts(channel_id),
                    self.get_learning_objectives(channel_id),
                    return_exceptions=True # Return exceptions instead of raising immediately
                )

                # Handle potential errors from gather
                if isinstance(teaching_prompt, Exception):
                     logger.error(f"Error getting teaching prompt for instructions: {teaching_prompt}")
                     teaching_prompt = "[Error retrieving teaching prompt]"
                if isinstance(related_prompts, Exception):
                     logger.error(f"Error getting related prompts for instructions: {related_prompts}")
                     related_prompts = "[Error retrieving related prompts]"
                if isinstance(learning_objectives, Exception):
                     logger.error(f"Error getting learning objectives for instructions: {learning_objectives}")
                     learning_objectives = "[Error retrieving learning objectives]"

            except Exception as gather_err:
                 logger.error(f"Unexpected error during asyncio.gather in build_instructions_async: {gather_err}")
                 teaching_prompt = "[Error gathering context]"
                 related_prompts = "[Error gathering context]"
                 learning_objectives = "[Error gathering context]"


            base_instructions = (
               "You are a university support agent. Use the context provided below (teaching prompts, related content, learning objectives) "
               "which is dynamically retrieved based on the current conversation channel. Greet the user by name if available. "
               "Answer questions comprehensively using all available sections. If a section is missing, rely on others. "
               "Respond professionally without contractions (e.g., use 'do not' instead of 'don't')."
            )

            full_prompt = (
                f"{greeting}{agent_specific_instructions}\n\n"
                f"**Base Instructions:**\n{base_instructions}\n\n"
                f"**Context for Channel '{channel_id or 'Default'}':**\n"
                f"Teaching Prompts:\n{teaching_prompt}\n\n"
                f"Related Content (Courses, Topics, Subtopics):\n{related_prompts}\n\n"
                f"Learning Objectives:\n{learning_objectives}"
            )
            # logger.debug(f"Built instructions preview: {full_prompt[:200]}...")
            return full_prompt

        # --- Agent Definitions ---
        # Use the asyncio.run wrapper within the lambda, now enabled by nest_asyncio
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
            instructions=lambda context: asyncio.run(build_instructions_async(triage_instructions_specific, context)),
            functions=[ handoff_to_support, handoff_to_learning ],
            tools=[ search_courses, search_teaching_units ], # Async tools
            model="default"
        )

        support_instructions_specific = (
            "You are SupportAgent. Handle general queries (courses, schedules, students, enrollments) using your tools. "
            "If data is missing, provide general advice based on the context below. "
            "Delegate learning/assessment queries using handoff_to_learning(). "
            "Delegate coordination tasks using handoff_to_triage()."
        )
        agents["SupportAgent"] = Agent(
            name="SupportAgent",
            instructions=lambda context: asyncio.run(build_instructions_async(support_instructions_specific, context)),
            functions=[ handoff_to_triage, handoff_to_learning ],
            tools=[
                search_courses, search_teaching_units, search_students,
                search_enrollments, search_assessment_items, comprehensive_search
            ], # Async tools
             model="default"
        )

        learning_instructions_specific = (
            "You are LearningAgent. Specialize in learning objectives and assessments using your tools. "
            "Delegate general academic queries using handoff_to_support(). "
            "Delegate coordination tasks using handoff_to_triage()."
        )
        agents["LearningAgent"] = Agent(
            name="LearningAgent",
            instructions=lambda context: asyncio.run(build_instructions_async(learning_instructions_specific, context)),
            functions=[ handoff_to_triage, handoff_to_support ],
            tools=[
                search_learning_objectives, search_topics, search_subtopics,
                extended_comprehensive_search
            ], # Async tools
             model="default"
        )

        logger.info(f"Agents created: {list(agents.keys())}")
        self.set_starting_agent(agents["TriageAgent"])
        return agents


# --- Main Execution Block ---
if __name__ == "__main__":
    # This block is executed only when the script is run directly
    logger.info("Running UniversitySupportBlueprint main (script execution)...")
    try:
        # BlueprintBase.main() handles argument parsing, setup, and running
        UniversitySupportBlueprint.main()
        logger.info("UniversitySupportBlueprint main finished.")
    except Exception as e:
        logger.critical(f"Error running UniversitySupportBlueprint.main: {e}", exc_info=True)
        print(f"Critical Error in __main__: {e}", file=sys.stderr)

