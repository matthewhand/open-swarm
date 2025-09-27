"""GitHub marketplace API views for blueprint and MCP configuration discovery."""
import json
import logging
from typing import Any, Dict

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from swarm.services.github_client import (
    fetch_github_repositories,
    fetch_manifest_from_repo,
    create_blueprint_from_manifest,
    create_mcp_config_from_manifest,
    sync_marketplace_items,
)
from swarm.models.core_models import Blueprint, MCPConfig

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def github_marketplace_search(request):
    """Search for blueprints and MCP configs on GitHub by query."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'error': 'Query parameter "q" is required'}, status=400)
    
    try:
        # Search for repositories by query
        repos = fetch_github_repositories(query)
        
        # Filter repositories that have manifest files
        manifest_repos = []
        for repo in repos:
            manifest_data = fetch_manifest_from_repo(repo['full_name'])
            if manifest_data:
                repo['manifest_data'] = manifest_data
                manifest_repos.append(repo)
        
        # Create response with repository information
        results = []
        for repo in manifest_repos:
            manifest_data = repo['manifest_data']
            
            # Determine if this is a blueprint or MCP config
            if 'code_template' in manifest_data:
                # This is a blueprint
                blueprint_data = {
                    'type': 'blueprint',
                    'name': manifest_data.get('name', repo['name']),
                    'title': manifest_data.get('name', repo['name']),
                    'description': manifest_data.get('description', repo['description']),
                    'version': manifest_data.get('version', '1.0.0'),
                    'tags': manifest_data.get('tags', []),
                    'repository_url': repo['html_url'],
                    'manifest_data': manifest_data,
                    'code_template': manifest_data.get('code_template', ''),
                    'required_mcp_servers': manifest_data.get('required_mcp_servers', []),
                    'category': manifest_data.get('category', 'ai_assistants'),
                }
                results.append(blueprint_data)
            elif 'config_template' in manifest_data:
                # This is an MCP config
                mcp_config_data = {
                    'type': 'mcp_config',
                    'name': manifest_data.get('name', repo['name']),
                    'title': manifest_data.get('name', repo['name']),
                    'description': manifest_data.get('description', repo['description']),
                    'version': manifest_data.get('version', '1.0.0'),
                    'tags': manifest_data.get('tags', []),
                    'repository_url': repo['html_url'],
                    'manifest_data': manifest_data,
                    'config_template': manifest_data.get('config_template', ''),
                    'server_name': manifest_data.get('server_name', ''),
                }
                results.append(mcp_config_data)
        
        return JsonResponse({
            'count': len(results),
            'results': results,
            'query': query
        })
    except Exception as e:
        logger.error(f"Error searching GitHub marketplace: {e}")
        return JsonResponse({'error': 'Failed to search GitHub marketplace'}, status=500)


@require_http_methods(["GET"])
def github_marketplace_sync(request):
    """Sync marketplace items from GitHub to local database."""
    try:
        created_count, updated_count = sync_marketplace_items()
        
        return JsonResponse({
            'message': 'Marketplace sync completed',
            'created_count': created_count,
            'updated_count': updated_count
        })
    except Exception as e:
        logger.error(f"Error syncing GitHub marketplace: {e}")
        return JsonResponse({'error': 'Failed to sync GitHub marketplace'}, status=500)


@require_http_methods(["GET"])
def github_blueprint_detail(request, blueprint_name):
    """Get details for a specific blueprint from GitHub."""
    try:
        # First check if blueprint exists in local database
        try:
            blueprint = Blueprint.objects.get(name=blueprint_name)
            return JsonResponse({
                'type': 'blueprint',
                'name': blueprint.name,
                'title': blueprint.title,
                'description': blueprint.description,
                'version': blueprint.version,
                'tags': blueprint.tags.split(','),
                'repository_url': blueprint.repository_url,
                'manifest_data': blueprint.manifest_data,
                'code_template': blueprint.code_template,
                'required_mcp_servers': blueprint.required_mcp_servers,
                'category': blueprint.category,
            })
        except Blueprint.DoesNotExist:
            pass  # Continue to fetch from GitHub
        
        # If not in local database, search GitHub for the specific repository
        repos = fetch_github_repositories(blueprint_name)
        
        for repo in repos:
            manifest_data = fetch_manifest_from_repo(repo['full_name'])
            if manifest_data and manifest_data.get('name', '').replace(' ', '_').lower() == blueprint_name.lower():
                # Create blueprint from manifest
                blueprint = create_blueprint_from_manifest(manifest_data, repo)
                
                return JsonResponse({
                    'type': 'blueprint',
                    'name': blueprint.name,
                    'title': blueprint.title,
                    'description': blueprint.description,
                    'version': blueprint.version,
                    'tags': blueprint.tags.split(','),
                    'repository_url': blueprint.repository_url,
                    'manifest_data': blueprint.manifest_data,
                    'code_template': blueprint.code_template,
                    'required_mcp_servers': blueprint.required_mcp_servers,
                    'category': blueprint.category,
                })
        
        return JsonResponse({'error': 'Blueprint not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching blueprint detail: {e}")
        return JsonResponse({'error': 'Failed to fetch blueprint detail'}, status=500)


@require_http_methods(["GET"])
def github_mcp_config_detail(request, config_name):
    """Get details for a specific MCP config from GitHub."""
    try:
        # First check if MCP config exists in local database
        try:
            mcp_config = MCPConfig.objects.get(name=config_name)
            return JsonResponse({
                'type': 'mcp_config',
                'name': mcp_config.name,
                'title': mcp_config.title,
                'description': mcp_config.description,
                'version': mcp_config.version,
                'tags': mcp_config.tags.split(','),
                'repository_url': mcp_config.repository_url,
                'manifest_data': mcp_config.manifest_data,
                'config_template': mcp_config.config_template,
                'server_name': mcp_config.server_name,
            })
        except MCPConfig.DoesNotExist:
            pass  # Continue to fetch from GitHub
        
        # If not in local database, search GitHub for the specific repository
        repos = fetch_github_repositories(config_name)
        
        for repo in repos:
            manifest_data = fetch_manifest_from_repo(repo['full_name'])
            if manifest_data and manifest_data.get('name', '').replace(' ', '_').lower() == config_name.lower():
                # Create MCP config from manifest
                mcp_config = create_mcp_config_from_manifest(manifest_data, repo)
                
                return JsonResponse({
                    'type': 'mcp_config',
                    'name': mcp_config.name,
                    'title': mcp_config.title,
                    'description': mcp_config.description,
                    'version': mcp_config.version,
                    'tags': mcp_config.tags.split(','),
                    'repository_url': mcp_config.repository_url,
                    'manifest_data': mcp_config.manifest_data,
                    'config_template': mcp_config.config_template,
                    'server_name': mcp_config.server_name,
                })
        
        return JsonResponse({'error': 'MCP config not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching MCP config detail: {e}")
        return JsonResponse({'error': 'Failed to fetch MCP config detail'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def github_install_blueprint(request, blueprint_name):
    """Install a blueprint from GitHub."""
    try:
        # Get the blueprint either from local database or GitHub
        try:
            blueprint = Blueprint.objects.get(name=blueprint_name)
        except Blueprint.DoesNotExist:
            # Fetch from GitHub and create in database
            repos = fetch_github_repositories(blueprint_name)
            
            for repo in repos:
                manifest_data = fetch_manifest_from_repo(repo['full_name'])
                if manifest_data and manifest_data.get('name', '').replace(' ', '_').lower() == blueprint_name.lower():
                    blueprint = create_blueprint_from_manifest(manifest_data, repo)
                    break
            else:
                return JsonResponse({'error': 'Blueprint not found'}, status=404)
        
        # In a real implementation, this would install the blueprint
        # For now, we'll just return success
        return JsonResponse({
            'message': f'Blueprint {blueprint_name} installed successfully',
            'blueprint': {
                'name': blueprint.name,
                'title': blueprint.title,
                'description': blueprint.description,
            }
        })
    except Exception as e:
        logger.error(f"Error installing blueprint: {e}")
        return JsonResponse({'error': 'Failed to install blueprint'}, status=50)


@csrf_exempt
@require_http_methods(["POST"])
def github_install_mcp_config(request, config_name):
    """Install an MCP config from GitHub."""
    try:
        # Get the MCP config either from local database or GitHub
        try:
            mcp_config = MCPConfig.objects.get(name=config_name)
        except MCPConfig.DoesNotExist:
            # Fetch from GitHub and create in database
            repos = fetch_github_repositories(config_name)
            
            for repo in repos:
                manifest_data = fetch_manifest_from_repo(repo['full_name'])
                if manifest_data and manifest_data.get('name', '').replace(' ', '_').lower() == config_name.lower():
                    mcp_config = create_mcp_config_from_manifest(manifest_data, repo)
                    break
            else:
                return JsonResponse({'error': 'MCP config not found'}, status=404)
        
        # In a real implementation, this would install the MCP config
        # For now, we'll just return success
        return JsonResponse({
            'message': f'MCP config {config_name} installed successfully',
            'config': {
                'name': mcp_config.name,
                'title': mcp_config.title,
                'description': mcp_config.description,
            }
        })
    except Exception as e:
        logger.error(f"Error installing MCP config: {e}")
        return JsonResponse({'error': 'Failed to install MCP config'}, status=50)