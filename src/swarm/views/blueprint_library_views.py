"""
Blueprint Library Views for Open Swarm MCP Core.
Handles blueprint browsing, library management, and custom blueprint creation.
"""
import json
from pathlib import Path
from typing import Any

from django.conf import settings as dj_settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from swarm.core.blueprint_discovery import discover_blueprints
from swarm.core.paths import get_user_config_dir_for_swarm
from swarm.core.requirements import evaluate_mcp_compliance, load_active_config
from swarm.settings import BLUEPRINT_DIRECTORY
from swarm.utils.comfyui_client import comfyui_client
from swarm.utils.logger_setup import setup_logger

logger = setup_logger(__name__)

# Predefined blueprint categories and descriptions
BLUEPRINT_CATEGORIES = {
    "ai_assistants": {
        "name": "AI Assistants",
        "description": "Intelligent agents for various tasks",
        "icon": "🤖"
    },
    "code_helpers": {
        "name": "Code Helpers",
        "description": "Programming and development assistants",
        "icon": "💻"
    },
    "content_creators": {
        "name": "Content Creators",
        "description": "Writing, poetry, and content generation",
        "icon": "✍️"
    },
    "system_tools": {
        "name": "System Tools",
        "description": "System monitoring and management",
        "icon": "🔧"
    },
    "web_services": {
        "name": "Web Services",
        "description": "Web development and API tools",
        "icon": "🌐"
    }
}

# Avatar styles available for generation
AVATAR_STYLES = {
    "professional": "Professional headshot style",
    "cartoon": "Cartoon character style",
    "anime": "Anime character style",
    "realistic": "Realistic portrait style",
    "icon": "Simple icon style"
}

# Blueprint metadata for the library
BLUEPRINT_METADATA = {
    "codey": {
        "name": "Codey",
        "description": "AI-powered coding assistant that helps with programming tasks",
        "category": "code_helpers",
        "tags": ["coding", "programming", "debugging"],
        "author": "Open Swarm Team",
        "version": "1.0.0",
        "difficulty": "beginner"
    },
    "gawd": {
        "name": "GAWD",
        "description": "General AI assistant for various tasks and conversations",
        "category": "ai_assistants",
        "tags": ["general", "conversation", "assistant"],
        "author": "Open Swarm Team",
        "version": "1.0.0",
        "difficulty": "beginner"
    },
    "whinge_surf": {
        "name": "Whinge Surf",
        "description": "System monitoring and process management tool",
        "category": "system_tools",
        "tags": ["monitoring", "system", "processes"],
        "author": "Open Swarm Team",
        "version": "1.0.0",
        "difficulty": "intermediate"
    },
    "poets": {
        "name": "Poets",
        "description": "Creative writing and poetry generation assistant",
        "category": "content_creators",
        "tags": ["poetry", "writing", "creative"],
        "author": "Open Swarm Team",
        "version": "1.0.0",
        "difficulty": "beginner"
    },
    "echocraft": {
        "name": "EchoCraft",
        "description": "Message mirroring and UX demonstration tool",
        "category": "ai_assistants",
        "tags": ["demo", "echo", "ux"],
        "author": "Open Swarm Team",
        "version": "1.0.0",
        "difficulty": "beginner"
    },
    "family_ties": {
        "name": "Family Ties",
        "description": "WordPress content management with agent team coordination",
        "category": "web_services",
        "tags": ["wordpress", "cms", "team"],
        "author": "Open Swarm Team",
        "version": "1.0.0",
        "difficulty": "advanced"
    },
    "mission_improbable": {
        "name": "Mission Improbable",
        "description": "Database-driven mission management system",
        "category": "system_tools",
        "tags": ["database", "missions", "management"],
        "author": "Open Swarm Team",
        "version": "1.0.0",
        "difficulty": "intermediate"
    },
    "zeus": {
        "name": "Zeus",
        "description": "Powerful command-line interface for system operations",
        "category": "system_tools",
        "tags": ["cli", "system", "commands"],
        "author": "Open Swarm Team",
        "version": "1.0.0",
        "difficulty": "intermediate"
    },
    "chatbot": {
        "name": "Chatbot",
        "description": "General conversation and chat assistant",
        "category": "ai_assistants",
        "tags": ["chat", "conversation", "assistant"],
        "author": "Open Swarm Team",
        "version": "1.0.0",
        "difficulty": "beginner"
    },
    "omniplex": {
        "name": "Omniplex",
        "description": "Multi-agent coordination and task management",
        "category": "ai_assistants",
        "tags": ["multi-agent", "coordination", "tasks"],
        "author": "Open Swarm Team",
        "version": "1.0.0",
        "difficulty": "advanced"
    }
}

def get_user_blueprint_library() -> dict[str, Any]:
    """Get the user's personal blueprint library."""
    user_config_dir = get_user_config_dir_for_swarm()
    library_file = user_config_dir / "blueprint_library.json"

    if library_file.exists():
        try:
            with open(library_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading blueprint library: {e}")

    return {"installed": [], "custom": []}

def save_user_blueprint_library(library: dict[str, Any]) -> bool:
    """Save the user's blueprint library."""
    try:
        user_config_dir = get_user_config_dir_for_swarm()
        library_file = user_config_dir / "blueprint_library.json"

        # Ensure directory exists
        library_file.parent.mkdir(parents=True, exist_ok=True)

        with open(library_file, 'w') as f:
            json.dump(library, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving blueprint library: {e}")
        return False

@csrf_exempt
def blueprint_library(request):
    """Main blueprint library page - browse and manage blueprints."""
    try:
        # Get available blueprints
        discovered_metadata = discover_blueprints(BLUEPRINT_DIRECTORY)
        available_blueprints = list(discovered_metadata.keys())

        # Get user's library
        user_library = get_user_blueprint_library()
        installed_blueprints = user_library.get("installed", [])
        custom_blueprints = user_library.get("custom", [])

        # Prepare blueprint data with metadata
        blueprint_data = []
        for bp_name in available_blueprints:
            metadata = BLUEPRINT_METADATA.get(bp_name, {
                "name": bp_name.replace("_", " ").title(),
                "description": f"Blueprint for {bp_name}",
                "category": "ai_assistants",
                "tags": [],
                "author": "Open Swarm Team",
                "version": "1.0.0",
                "difficulty": "beginner"
            })

            blueprint_data.append({
                "id": bp_name,
                "name": metadata["name"],
                "description": metadata["description"],
                "category": metadata["category"],
                "category_info": BLUEPRINT_CATEGORIES.get(metadata["category"], {}),
                "tags": metadata["tags"],
                "author": metadata["author"],
                "version": metadata["version"],
                "difficulty": metadata["difficulty"],
                "installed": bp_name in installed_blueprints,
                "available": True
            })

        # Group by category
        blueprints_by_category = {}
        for bp in blueprint_data:
            category = bp["category"]
            if category not in blueprints_by_category:
                blueprints_by_category[category] = []
            blueprints_by_category[category].append(bp)

        context = {
            "blueprints_by_category": blueprints_by_category,
            "categories": BLUEPRINT_CATEGORIES,
            "installed_count": len(installed_blueprints),
            "custom_count": len(custom_blueprints),
            "dark_mode": request.session.get('dark_mode', True),
            "github_marketplace_enabled": getattr(dj_settings, 'ENABLE_GITHUB_MARKETPLACE', False),
        }

        return render(request, "blueprint_library.html", context)

    except Exception as e:
        logger.error(f"Error loading blueprint library: {e}")
        return HttpResponse("Error loading blueprint library", status=500)

@csrf_exempt
def blueprint_requirements_status(_request):
    """Return JSON with MCP requirements vs current configuration per blueprint."""
    try:
        discovered = discover_blueprints(BLUEPRINT_DIRECTORY)
        config = load_active_config()
        mcp_config = config.get("mcpServers", {}) if isinstance(config, dict) else {}

        results = []
        for key, info in discovered.items():
            metadata = info.get("metadata", {})
            required = metadata.get("required_mcp_servers") or []
            env_vars = metadata.get("env_vars") or []
            compliance = evaluate_mcp_compliance(required, mcp_config, blueprint_env_vars=env_vars)
            results.append({
                "id": key,
                "name": metadata.get("name", key),
                "required_mcp_servers": required,
                "env_vars": env_vars,
                "compliance": compliance,
            })

        return JsonResponse({"blueprints": results})
    except Exception as e:
        logger.error(f"Error generating blueprint requirements status: {e}", exc_info=True)
        return JsonResponse({"error": "Internal server error"}, status=500)

@csrf_exempt
def add_blueprint_to_library(request, blueprint_name):
    """Add a blueprint to the user's library."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        # Verify blueprint exists
        discovered_metadata = discover_blueprints(BLUEPRINT_DIRECTORY)
        if blueprint_name not in discovered_metadata:
            return JsonResponse({"error": "Blueprint not found"}, status=404)

        # Get current library
        library = get_user_blueprint_library()

        # Add to installed if not already there
        if blueprint_name not in library["installed"]:
            library["installed"].append(blueprint_name)

            # Save library
            if save_user_blueprint_library(library):
                return JsonResponse({
                    "success": True,
                    "message": f"Blueprint '{blueprint_name}' added to library"
                })
            else:
                return JsonResponse({"error": "Failed to save library"}, status=500)
        else:
            return JsonResponse({
                "success": True,
                "message": f"Blueprint '{blueprint_name}' already in library"
            })

    except Exception as e:
        logger.error(f"Error adding blueprint to library: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)

@csrf_exempt
def remove_blueprint_from_library(request, blueprint_name):
    """Remove a blueprint from the user's library."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        # Get current library
        library = get_user_blueprint_library()

        # Remove from installed
        if blueprint_name in library["installed"]:
            library["installed"].remove(blueprint_name)

            # Save library
            if save_user_blueprint_library(library):
                return JsonResponse({
                    "success": True,
                    "message": f"Blueprint '{blueprint_name}' removed from library"
                })
            else:
                return JsonResponse({"error": "Failed to save library"}, status=500)
        else:
            return JsonResponse({
                "success": True,
                "message": f"Blueprint '{blueprint_name}' not in library"
            })

    except Exception as e:
        logger.error(f"Error removing blueprint from library: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)

@csrf_exempt
def blueprint_creator(request):
    """LLM-powered blueprint creator form."""
    if request.method == "GET":
        context = {
            "categories": BLUEPRINT_CATEGORIES,
            "dark_mode": request.session.get('dark_mode', True),
        }
        return render(request, "blueprint_creator.html", context)

    elif request.method == "POST":
        try:
            # Get form data
            blueprint_name = request.POST.get("blueprint_name", "").strip()
            description = request.POST.get("description", "").strip()
            category = request.POST.get("category", "ai_assistants")
            tags = request.POST.get("tags", "").strip()
            requirements = request.POST.get("requirements", "").strip()

            # Validate required fields
            if not blueprint_name or not description:
                return JsonResponse({
                    "error": "Blueprint name and description are required"
                }, status=400)

            # Generate blueprint code using LLM (simplified for now)
            # In a real implementation, you'd call an LLM API here
            blueprint_code = generate_blueprint_code(
                blueprint_name, description, category, tags, requirements
            )

            # Generate avatar if requested and ComfyUI is available
            avatar_path = None
            avatar_style = request.POST.get("avatar_style", "professional")
            generate_avatar = request.POST.get("generate_avatar", "false").lower() == "true"

            if generate_avatar and comfyui_client.is_available():
                avatar_path = comfyui_client.generate_avatar(
                    blueprint_name, description, category, avatar_style
                )

            # Save to user's custom blueprints
            library = get_user_blueprint_library()

            custom_blueprint = {
                "id": blueprint_name.lower().replace(" ", "_"),
                "name": blueprint_name,
                "description": description,
                "category": category,
                "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
                "requirements": requirements,
                "code": blueprint_code,
                "avatar_path": avatar_path,
                "avatar_style": avatar_style if avatar_path else None,
                "created_at": str(Path().cwd()),
                "author": "User Generated"
            }

            library["custom"].append(custom_blueprint)

            if save_user_blueprint_library(library):
                return JsonResponse({
                    "success": True,
                    "message": f"Blueprint '{blueprint_name}' created successfully",
                    "blueprint": custom_blueprint
                })
            else:
                return JsonResponse({"error": "Failed to save blueprint"}, status=500)

        except Exception as e:
            logger.error(f"Error creating blueprint: {e}")
            return JsonResponse({"error": "Internal server error"}, status=500)

@csrf_exempt
def generate_avatar(request, blueprint_name):
    """Generate an avatar for an existing blueprint."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        # Get form data
        avatar_style = request.POST.get("avatar_style", "professional")

        # Get blueprint metadata
        metadata = BLUEPRINT_METADATA.get(blueprint_name)
        if not metadata:
            return JsonResponse({"error": "Blueprint not found"}, status=404)

        # Generate avatar
        avatar_path = comfyui_client.generate_avatar(
            metadata["name"],
            metadata["description"],
            metadata["category"],
            avatar_style
        )

        if avatar_path:
            return JsonResponse({
                "success": True,
                "message": f"Avatar generated successfully for {blueprint_name}",
                "avatar_path": avatar_path
            })
        else:
            return JsonResponse({
                "error": "Failed to generate avatar. Check ComfyUI configuration."
            }, status=500)

    except Exception as e:
        logger.error(f"Error generating avatar: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)

@csrf_exempt
def check_comfyui_status(_request):
    """Check if ComfyUI is available for avatar generation."""
    try:
        is_available = comfyui_client.is_available()
        return JsonResponse({
            "available": is_available,
            "enabled": comfyui_client.enabled,
            "styles": AVATAR_STYLES
        })
    except Exception as e:
        logger.error(f"Error checking ComfyUI status: {e}")
        return JsonResponse({
            "available": False,
            "enabled": False,
            "styles": AVATAR_STYLES
        })

def generate_blueprint_code(name: str, description: str, category: str, tags: list[str], _requirements: str) -> str:
    """Generate blueprint code using LLM (placeholder implementation)."""
    # This is a simplified template - in reality you'd call an LLM API
    template = f'''#!/usr/bin/env python3
"""
{name} Blueprint
{description}

Generated by Open Swarm Blueprint Creator
"""

import asyncio
from typing import Any, ClassVar
from swarm.core.blueprint_base import BlueprintBase

class {name.replace(" ", "")}Blueprint(BlueprintBase):
    """{description}"""

    metadata: ClassVar[dict[str, Any]] = {{
        "name": "{name}",
        "description": "{description}",
        "category": "{category}",
        "tags": {tags},
        "author": "User Generated",
        "version": "1.0.0"
    }}

    def __init__(self, blueprint_id: str = "{name.lower().replace(' ', '_')}", **kwargs):
        super().__init__(blueprint_id, **kwargs)

    async def run(self, messages: list[dict], **kwargs) -> None:
        """Main blueprint execution."""
        # Implementation: Process messages and execute blueprint-specific logic
        instruction = messages[-1].get("content", "") if messages else ""
        print(f"Executing {{self.blueprint_id}} with instruction: {{instruction}}")

        # Example logic based on instruction
        if "list" in instruction.lower():
            print("Available blueprints:")
            print("  - codey")
            print("  - poets")
            print("  - zeus")
        elif "execute" in instruction.lower():
            print("Executing custom blueprint logic...")
            print(f"Blueprint {{self.blueprint_id}} executed successfully.")
        else:
            print(f"Description: {{self.metadata['description']}}")
            print(f"Category: {{self.metadata['category']}}")
            print(f"Tags: {{', '.join(self.metadata['tags'])}}")
            print("Use 'list' to see available blueprints or 'execute <name>' to run one.")

        # Add your custom logic here based on specific requirements

if __name__ == "__main__":
    blueprint = {name.replace(" ", "")}Blueprint()
    asyncio.run(blueprint.run())
'''
    return template

@csrf_exempt
def my_blueprints(request):
    """Show user's installed and custom blueprints."""
    try:
        library = get_user_blueprint_library()
        installed = library.get("installed", [])
        custom = library.get("custom", [])

        # Get metadata for installed blueprints
        installed_data = []
        for bp_name in installed:
            metadata = BLUEPRINT_METADATA.get(bp_name, {
                "name": bp_name.replace("_", " ").title(),
                "description": f"Blueprint for {bp_name}",
                "category": "ai_assistants"
            })
            installed_data.append({
                "id": bp_name,
                "name": metadata["name"],
                "description": metadata["description"],
                "category": metadata["category"],
                "category_info": BLUEPRINT_CATEGORIES.get(metadata["category"], {}),
                "type": "installed"
            })

        context = {
            "installed_blueprints": installed_data,
            "custom_blueprints": custom,
            "dark_mode": request.session.get('dark_mode', True),
        }

        return render(request, "my_blueprints.html", context)

    except Exception as e:
        logger.error(f"Error loading my blueprints: {e}")
        return HttpResponse("Error loading blueprints", status=500)
