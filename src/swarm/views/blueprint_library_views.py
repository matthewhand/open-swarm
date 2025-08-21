"""
Blueprint Library Views for Open Swarm MCP Core.
Handles blueprint browsing, library management, and custom blueprint creation.
"""
import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Any

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

from swarm.core.blueprint_discovery import discover_blueprints
from swarm.settings import BLUEPRINT_DIRECTORY
from swarm.utils.logger_setup import setup_logger
from swarm.core.paths import get_user_config_dir_for_swarm

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

def get_user_blueprint_library() -> Dict[str, Any]:
    """Get the user's personal blueprint library."""
    user_config_dir = get_user_config_dir_for_swarm()
    library_file = user_config_dir / "blueprint_library.json"
    
    if library_file.exists():
        try:
            with open(library_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading blueprint library: {e}")
    
    return {"installed": [], "custom": []}

def save_user_blueprint_library(library: Dict[str, Any]) -> bool:
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
        }
        
        return render(request, "blueprint_library.html", context)
        
    except Exception as e:
        logger.error(f"Error loading blueprint library: {e}")
        return HttpResponse("Error loading blueprint library", status=500)

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

def generate_blueprint_code(name: str, description: str, category: str, tags: List[str], requirements: str) -> str:
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
    
    async def run(self, args: list[str] = None) -> None:
        """Main blueprint execution."""
        # TODO: Implement blueprint logic based on requirements
        # {requirements}
        
        print(f"Running {{self.blueprint_id}} blueprint...")
        print(f"Description: {description}")
        print(f"Category: {category}")
        print(f"Tags: {', '.join(tags)}")
        
        # Add your custom logic here
        pass

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
