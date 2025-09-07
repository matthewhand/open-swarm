"""
Web views for creating custom agents and teams with Python code validation
"""
import ast
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


class BlueprintCodeValidator:
    """Validates generated blueprint code using Python AST parsing and linting"""

    def __init__(self):
        self.required_imports = [
            'BlueprintBase',
            'AsyncGenerator',
            'Any'
        ]
        self.required_methods = ['run']
        self.required_attributes = ['metadata']

    def validate_syntax(self, code: str) -> tuple[bool, list[str]]:
        """Validate Python syntax using AST"""
        errors = []
        try:
            ast.parse(code)
            return True, []
        except SyntaxError as e:
            errors.append(f"Syntax Error: {e.msg} at line {e.lineno}")
            return False, errors

    def validate_structure(self, code: str) -> tuple[bool, list[str]]:
        """Validate blueprint structure requirements"""
        errors = []
        warnings = []

        try:
            tree = ast.parse(code)

            # Check for required imports
            imports_found = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.names:
                        for alias in node.names:
                            imports_found.append(alias.name)
                elif isinstance(node, ast.Import) and node.names:
                    for alias in node.names:
                        imports_found.append(alias.name)

            for required_import in self.required_imports:
                if not any(required_import in found for found in imports_found):
                    errors.append(f"Missing required import: {required_import}")

            # Check for blueprint class
            blueprint_class = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it inherits from BlueprintBase
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == 'BlueprintBase':
                            blueprint_class = node
                            break

            if not blueprint_class:
                errors.append("No class found that inherits from BlueprintBase")
                return False, errors

            # Check for required methods
            methods_found = []
            for node in blueprint_class.body:
                if isinstance(node, ast.AsyncFunctionDef):
                    methods_found.append(node.name)

            for required_method in self.required_methods:
                if required_method not in methods_found:
                    errors.append(f"Missing required async method: {required_method}")

            # Check for metadata attribute
            has_metadata = False
            for node in blueprint_class.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == 'metadata':
                            has_metadata = True
                            break

            if not has_metadata:
                warnings.append("Missing metadata attribute (recommended)")

            return len(errors) == 0, errors + warnings

        except Exception as e:
            errors.append(f"Structure validation error: {str(e)}")
            return False, errors

    def lint_code(self, code: str) -> tuple[bool, list[str]]:
        """Run flake8 on the code"""
        issues = []

        try:
            # Write code to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            # Run flake8 (lighter than pylint)
            result = subprocess.run(
                ['flake8', '--select=E,W,F', '--ignore=E501,W503', temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        # Parse flake8 output: filename:line:col: code message
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            issues.append(f"Line {parts[1]}: {parts[3].strip()}")

            # Clean up
            Path(temp_file).unlink()

            return len(issues) == 0, issues

        except subprocess.TimeoutExpired:
            issues.append("Code linting timed out")
            return False, issues
        except FileNotFoundError:
            # flake8 not installed, skip linting
            return True, ["Linting skipped (flake8 not available)"]
        except Exception as e:
            issues.append(f"Linting error: {str(e)}")
            return False, issues

    def validate_blueprint_code(self, code: str) -> dict[str, Any]:
        """Complete validation of blueprint code"""
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'syntax_valid': False,
            'structure_valid': False,
            'lint_clean': False
        }

        # 1. Syntax validation
        syntax_ok, syntax_errors = self.validate_syntax(code)
        results['syntax_valid'] = syntax_ok
        if not syntax_ok:
            results['valid'] = False
            results['errors'].extend(syntax_errors)
            return results  # Stop here if syntax is invalid

        # 2. Structure validation
        structure_ok, structure_issues = self.validate_structure(code)
        results['structure_valid'] = structure_ok
        if not structure_ok:
            results['valid'] = False

        # Separate errors and warnings
        for issue in structure_issues:
            if "Missing required" in issue:
                results['errors'].append(issue)
            else:
                results['warnings'].append(issue)

        # 3. Linting
        lint_ok, lint_issues = self.lint_code(code)
        results['lint_clean'] = lint_ok
        if lint_issues:
            results['warnings'].extend(lint_issues)

        return results


class AgentPersonaGenerator:
    """Generates agent persona code based on user specifications"""

    def __init__(self):
        self.base_template = '''"""
{description}
"""
from collections.abc import AsyncGenerator
from typing import Any
from swarm.core.blueprint_base import BlueprintBase

class {class_name}(BlueprintBase):
    """
    {description}
    """

    metadata = {{
        "name": "{name}",
        "description": "{description}",
        "version": "1.0.0",
        "author": "User Generated",
        "tags": {tags},
        "persona": {{
            "personality": "{personality}",
            "expertise": {expertise},
            "communication_style": "{communication_style}"
        }}
    }}

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        """
        Main execution method for the {name} agent.
        """
        # Get the user's message
        user_message = messages[-1].get("content", "") if messages else ""

        # Agent persona instructions
        persona_prompt = f\"\"\"
You are {name}, {description}

Personality: {personality}
Expertise: {expertise_str}
Communication Style: {communication_style}

Instructions: {instructions}

User Request: {{user_message}}
\"\"\"

        # Get LLM profile and make the call
        model_instance = self._get_model_instance(self.llm_profile_name)

        if not model_instance:
            yield {{
                "messages": [{{
                    "role": "assistant",
                    "content": "Error: Could not initialize model for {name} agent."
                }}]
            }}
            return

        try:
            # Stream the response
            system_message = {{"role": "system", "content": persona_prompt}}
            user_msg = {{"role": "user", "content": user_message}}

            async for chunk in model_instance.chat_completion_stream(
                messages=[system_message, user_msg]
            ):
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield {{
                            "messages": [{{
                                "role": "assistant",
                                "content": delta.content
                            }}]
                        }}
        except Exception as e:
            yield {{
                "messages": [{{
                    "role": "assistant",
                    "content": f"Error in {name} agent: {{str(e)}}"
                }}]
            }}
'''

    def generate_agent_code(self, agent_spec: dict[str, Any]) -> str:
        """Generate agent blueprint code from specification"""

        # Sanitize class name
        class_name = self._sanitize_class_name(agent_spec.get('name', 'CustomAgent'))

        # Format expertise
        expertise = agent_spec.get('expertise', ['general assistance'])
        if isinstance(expertise, list):
            expertise_str = ', '.join(expertise)
        else:
            expertise_str = str(expertise)

        return self.base_template.format(
            class_name=class_name,
            name=agent_spec.get('name', 'Custom Agent'),
            description=agent_spec.get('description', 'A custom AI agent'),
            personality=agent_spec.get('personality', 'helpful and professional'),
            expertise=repr(expertise),
            expertise_str=expertise_str,
            communication_style=agent_spec.get('communication_style', 'clear and concise'),
            instructions=agent_spec.get('instructions', 'Help the user with their request.'),
            tags=repr(agent_spec.get('tags', ['custom', 'user-generated']))
        )

    def _sanitize_class_name(self, name: str) -> str:
        """Convert name to valid Python class name"""
        import re
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
        words = clean_name.split()
        return ''.join(word.capitalize() for word in words) + 'Blueprint'


# Global instances
validator = BlueprintCodeValidator()
agent_generator = AgentPersonaGenerator()


@csrf_exempt
def agent_creator_page(request):
    """Render the agent creator interface"""
    if request.method == 'GET':
        context = {
            'page_title': 'Agent Creator',
            'form_data': {
                'personality_options': [
                    'helpful and professional', 'creative and enthusiastic',
                    'analytical and precise', 'friendly and casual', 'expert and authoritative'
                ],
                'expertise_options': [
                    'coding', 'writing', 'analysis', 'research', 'design',
                    'mathematics', 'science', 'business', 'education', 'general'
                ],
                'communication_options': [
                    'clear and concise', 'detailed and thorough', 'casual and conversational',
                    'formal and structured', 'creative and expressive'
                ]
            }
        }
        return render(request, 'agent_creator.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def generate_agent_code(request):
    """Generate agent code from form data"""
    try:
        data = json.loads(request.body)

        # Validate required fields
        required_fields = ['name', 'description', 'instructions']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }, status=400)

        # Generate the code
        generated_code = agent_generator.generate_agent_code(data)

        # Validate the generated code
        validation_result = validator.validate_blueprint_code(generated_code)

        return JsonResponse({
            'success': True,
            'code': generated_code,
            'validation': validation_result
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Code generation failed: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def validate_agent_code(request):
    """Validate user-provided agent code"""
    try:
        data = json.loads(request.body)
        code = data.get('code', '')

        if not code:
            return JsonResponse({
                'success': False,
                'error': 'No code provided'
            }, status=400)

        # Validate the code
        validation_result = validator.validate_blueprint_code(code)

        return JsonResponse({
            'success': True,
            'validation': validation_result
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Validation failed: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_custom_agent(request):
    """Save a custom agent blueprint"""
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        agent_name = data.get('name', '')

        if not code or not agent_name:
            return JsonResponse({
                'success': False,
                'error': 'Missing code or agent name'
            }, status=400)

        # Validate the code first
        validation_result = validator.validate_blueprint_code(code)
        if not validation_result['valid']:
            return JsonResponse({
                'success': False,
                'error': 'Code validation failed',
                'validation': validation_result
            }, status=400)

        # Save to user_blueprints directory
        user_blueprints_dir = Path('user_blueprints')
        agent_dir = user_blueprints_dir / agent_name.lower().replace(' ', '_')
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Write the blueprint file
        blueprint_file = agent_dir / f'blueprint_{agent_name.lower().replace(" ", "_")}.py'
        blueprint_file.write_text(code)

        # Create README
        readme_content = f"""# {agent_name}

Custom agent blueprint created via the Agent Creator.

## Description
{data.get('description', 'Custom AI agent')}

## Usage
```bash
swarm-cli launch {agent_name.lower().replace(' ', '_')}
```
"""
        readme_file = agent_dir / 'README.md'
        readme_file.write_text(readme_content)

        return JsonResponse({
            'success': True,
            'message': f'Agent "{agent_name}" saved successfully',
            'path': str(blueprint_file)
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Save failed: {str(e)}'
        }, status=500)


@csrf_exempt
def team_creator_page(request):
    """Render the team creator interface"""
    if request.method == 'GET':
        context = {
            'page_title': 'Team Creator',
            'existing_agents': _get_available_agents()
        }
        return render(request, 'team_creator.html', context)


def _get_available_agents():
    """Get list of available agents for team creation"""
    # This would scan for existing blueprints
    agents = []

    # Add built-in agents
    builtin_agents = [
        {'name': 'codey', 'description': 'Code analysis and generation'},
        {'name': 'jeeves', 'description': 'General purpose assistant'},
        {'name': 'chatbot', 'description': 'Conversational agent'}
    ]
    agents.extend(builtin_agents)

    # Add user-created agents
    user_blueprints_dir = Path('user_blueprints')
    if user_blueprints_dir.exists():
        for agent_dir in user_blueprints_dir.iterdir():
            if agent_dir.is_dir():
                agents.append({
                    'name': agent_dir.name,
                    'description': f'Custom agent: {agent_dir.name}'
                })

    return agents
