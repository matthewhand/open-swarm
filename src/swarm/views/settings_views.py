"""
Settings Views for Open Swarm
Web views for displaying and managing configuration settings
"""
import os
import sys

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .settings_manager import settings_manager

# Ensure module aliasing so tests patching either path work consistently
# Some tests reference this module as 'src.swarm.views.settings_views' while
# Django imports it as 'swarm.views.settings_views'. Create a sys.modules alias
# so both names resolve to the same module object, allowing patches to apply.
_this_mod = sys.modules.get(__name__)
if _this_mod is not None:
    if __name__.startswith("swarm."):
        sys.modules.setdefault(f"src.{__name__}", _this_mod)
    elif __name__.startswith("src."):
        sys.modules.setdefault(__name__[4:], _this_mod)


@csrf_exempt
def settings_dashboard(request):
    """Render the comprehensive settings dashboard"""
    try:
        all_settings = settings_manager.collect_all_settings()

        # Calculate statistics
        total_settings = sum(len(group['settings']) for group in all_settings.values())
        configured_settings = sum(
            1 for group in all_settings.values()
            for setting in group['settings'].values()
            if setting['value'] not in ['Not Set', None, '']
        )
        sensitive_settings = sum(
            1 for group in all_settings.values()
            for setting in group['settings'].values()
            if setting.get('sensitive', False)
        )

        context = {
            'page_title': 'Settings Dashboard',
            'settings_groups': all_settings,
            'stats': {
                'total': total_settings,
                'configured': configured_settings,
                'sensitive': sensitive_settings,
                'completion_rate': round((configured_settings / total_settings) * 100) if total_settings > 0 else 0
            }
        }

        return render(request, 'settings_dashboard.html', context)

    except Exception as e:
        return HttpResponse(f"Error loading settings: {str(e)}", status=500)


@csrf_exempt
@require_http_methods(["GET"])
def settings_api(request):
    """API endpoint to get all settings as JSON"""
    try:
        all_settings = settings_manager.collect_all_settings()

        # Remove sensitive values for API response
        safe_settings = {}
        for group_name, group_data in all_settings.items():
            safe_settings[group_name] = {
                'title': group_data['title'],
                'description': group_data['description'],
                'icon': group_data['icon'],
                'settings': {}
            }

            for setting_name, setting_data in group_data['settings'].items():
                safe_setting = setting_data.copy()
                if setting_data.get('sensitive', False):
                    safe_setting['value'] = '***HIDDEN***'
                safe_settings[group_name]['settings'][setting_name] = safe_setting

        return JsonResponse({
            'success': True,
            'settings': safe_settings
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def environment_variables(request):
    """Get all environment variables related to Open Swarm"""
    try:
        # Collect all environment variables that might be relevant
        relevant_prefixes = [
            'DJANGO_', 'SWARM_', 'API_', 'ENABLE_', 'OPENAI_',
            'ANTHROPIC_', 'OLLAMA_', 'REDIS_', 'LOG'
        ]

        env_vars = {}
        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in relevant_prefixes):
                # Hide sensitive values
                if any(sensitive in key.lower() for sensitive in ['key', 'token', 'secret', 'password']):
                    env_vars[key] = '***SET***' if value else 'Not Set'
                else:
                    env_vars[key] = value

        return JsonResponse({
            'success': True,
            'environment_variables': env_vars,
            'count': len(env_vars)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
