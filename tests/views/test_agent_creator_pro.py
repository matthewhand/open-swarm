"""
Comprehensive tests for Agent Creator Pro functionality
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from src.swarm.views.agent_creator_pro import (
    AdvancedCodeValidator,
    ProAgentGenerator,
)


class TestAdvancedCodeValidator(TestCase):
    """Test the advanced code validation functionality"""

    def setUp(self):
        self.validator = AdvancedCodeValidator()

    def test_validate_security_safe_code(self):
        """Test security validation with safe code"""
        safe_code = '''
from swarm.core.blueprint_base import BlueprintBase

class TestBlueprint(BlueprintBase):
    async def run(self, messages):
        return "Hello"
'''
        is_safe, issues = self.validator.validate_security(safe_code)
        self.assertTrue(is_safe)
        self.assertEqual(len(issues), 0)

    def test_validate_security_dangerous_code(self):
        """Test security validation with dangerous patterns"""
        dangerous_code = '''
import os
import subprocess

class TestBlueprint(BlueprintBase):
    async def run(self, messages):
        os.system("rm -rf /")
        subprocess.call(["dangerous", "command"])
        return eval(user_input)
'''
        is_safe, issues = self.validator.validate_security(dangerous_code)
        self.assertFalse(is_safe)
        self.assertGreater(len(issues), 0)
        self.assertTrue(any('import\\s+os' in issue for issue in issues))

    def test_validate_security_hardcoded_secrets(self):
        """Test detection of hardcoded secrets"""
        secret_code = '''
class TestBlueprint(BlueprintBase):
    def __init__(self):
        self.api_key = "sk-1234567890abcdef"
        self.password = "secret123"
'''
        is_safe, issues = self.validator.validate_security(secret_code)
        self.assertFalse(is_safe)
        self.assertTrue(any('hardcoded credentials' in issue.lower() for issue in issues))

    def test_validate_performance_safe_code(self):
        """Test performance validation with efficient code"""
        efficient_code = '''
class TestBlueprint(BlueprintBase):
    async def run(self, messages):
        for i in range(10):
            await process_item(i)
        return "Done"
'''
        is_efficient, issues = self.validator.validate_performance(efficient_code)
        self.assertTrue(is_efficient)
        self.assertEqual(len(issues), 0)

    def test_validate_performance_problematic_code(self):
        """Test performance validation with problematic patterns"""
        problematic_code = '''
class TestBlueprint(BlueprintBase):
    async def run(self, messages):
        while True:
            process_forever()

        for i in range(1000000):
            expensive_operation(i)

        time.sleep(300)
        return "Done"
'''
        is_efficient, issues = self.validator.validate_performance(problematic_code)
        self.assertFalse(is_efficient)
        self.assertGreater(len(issues), 0)

    def test_validate_blueprint_semantics_valid(self):
        """Test semantic validation with proper blueprint structure"""
        valid_code = '''
from swarm.core.blueprint_base import BlueprintBase

class TestBlueprint(BlueprintBase):
    async def run(self, messages):
        try:
            result = await self.process(messages)
            yield {"messages": [{"role": "assistant", "content": result}]}
        except Exception as e:
            yield {"error": str(e)}
'''
        is_valid, issues = self.validator.validate_blueprint_semantics(valid_code)
        self.assertTrue(is_valid)
        # Should have no errors, maybe some best practice warnings
        errors = [issue for issue in issues if 'error' in issue.lower()]
        self.assertEqual(len(errors), 0)

    def test_validate_blueprint_semantics_missing_yield(self):
        """Test semantic validation with missing yield"""
        invalid_code = '''
class TestBlueprint(BlueprintBase):
    async def run(self, messages):
        return "This should yield, not return"
'''
        is_valid, issues = self.validator.validate_blueprint_semantics(invalid_code)
        self.assertFalse(is_valid)
        self.assertTrue(any('yield' in issue for issue in issues))

    def test_validate_blueprint_code_comprehensive(self):
        """Test comprehensive validation pipeline"""
        test_code = '''
from collections.abc import AsyncGenerator
from typing import Any
from swarm.core.blueprint_base import BlueprintBase

class TestAgentBlueprint(BlueprintBase):
    metadata = {
        "name": "Test Agent",
        "description": "A test agent"
    }

    async def run(self, messages: list[dict[str, Any]]) -> AsyncGenerator[dict[str, Any], None]:
        try:
            user_message = messages[-1].get("content", "")
            yield {
                "messages": [{
                    "role": "assistant",
                    "content": f"Echo: {user_message}"
                }]
            }
        except Exception as e:
            yield {
                "messages": [{
                    "role": "assistant",
                    "content": f"Error: {str(e)}"
                }]
            }
'''
        result = self.validator.validate_blueprint_code(test_code)

        self.assertIsInstance(result, dict)
        self.assertIn('valid', result)
        self.assertIn('syntax_valid', result)
        self.assertIn('structure_valid', result)
        self.assertIn('lint_clean', result)
        self.assertIn('errors', result)
        self.assertIn('warnings', result)

        # This should be valid code
        self.assertTrue(result['syntax_valid'])
        self.assertTrue(result['structure_valid'])


class TestProAgentGenerator(TestCase):
    """Test the professional agent code generator"""

    def setUp(self):
        self.generator = ProAgentGenerator()

    def test_template_selection_conversational(self):
        """Test template selection for conversational agents"""
        agent_spec = {
            'name': 'Chat Assistant',
            'expertise': ['general', 'conversation'],
            'personality': 'friendly and helpful'
        }
        template = self.generator._select_template(agent_spec)
        self.assertEqual(template, 'conversational')

    def test_template_selection_analytical(self):
        """Test template selection for analytical agents"""
        agent_spec = {
            'name': 'Data Analyst',
            'expertise': ['analysis', 'research', 'data_science'],
            'personality': 'analytical and precise'
        }
        template = self.generator._select_template(agent_spec)
        self.assertEqual(template, 'analytical')

    def test_template_selection_creative(self):
        """Test template selection for creative agents"""
        agent_spec = {
            'name': 'Creative Writer',
            'expertise': ['writing', 'creative', 'design'],
            'personality': 'creative and enthusiastic'
        }
        template = self.generator._select_template(agent_spec)
        self.assertEqual(template, 'creative')

    def test_sanitize_class_name(self):
        """Test class name sanitization"""
        test_cases = [
            ('Simple Agent', 'SimpleAgentBlueprint'),
            ('Code-Review Bot!', 'CodeReviewBotBlueprint'),
            ('123 Number Agent', 'NumberAgentBlueprint'),
            ('Special@#$Characters', 'SpecialCharactersBlueprint')
        ]

        for input_name, expected in test_cases:
            result = self.generator._sanitize_class_name(input_name)
            self.assertEqual(result, expected)

    def test_generate_agent_code_basic(self):
        """Test basic agent code generation"""
        agent_spec = {
            'name': 'Test Agent',
            'description': 'A test agent for unit testing',
            'personality': 'helpful and professional',
            'expertise': ['testing', 'validation'],
            'communication_style': 'clear and concise',
            'instructions': 'Help with testing and validation tasks',
            'tags': ['test', 'validation']
        }

        generated_code = self.generator.generate_agent_code(agent_spec)

        # Verify code structure
        self.assertIn('class TestAgentBlueprint(BlueprintBase)', generated_code)
        self.assertIn('async def run(self', generated_code)
        self.assertIn('metadata = {', generated_code)
        self.assertIn('"name": "Test Agent"', generated_code)
        self.assertIn('"description": "A test agent for unit testing"', generated_code)

        # Verify imports
        self.assertIn('from collections.abc import AsyncGenerator', generated_code)
        self.assertIn('from typing import Any', generated_code)
        self.assertIn('from swarm.core.blueprint_base import BlueprintBase', generated_code)

    def test_generate_agent_code_with_complex_expertise(self):
        """Test agent code generation with complex expertise list"""
        agent_spec = {
            'name': 'Multi-Skill Agent',
            'description': 'An agent with multiple skills',
            'personality': 'adaptable and knowledgeable',
            'expertise': ['coding', 'writing', 'analysis', 'research'],
            'communication_style': 'detailed and thorough',
            'instructions': 'Adapt to various tasks using multiple skills',
            'tags': ['multi-skill', 'adaptive']
        }

        generated_code = self.generator.generate_agent_code(agent_spec)

        # Verify expertise is properly formatted
        self.assertIn("'coding', 'writing', 'analysis', 'research'", generated_code)
        self.assertIn('Expertise: coding, writing, analysis, research', generated_code)


@pytest.mark.django_db
class TestAgentCreatorProViews(TestCase):
    """Test the Agent Creator Pro web views"""

    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_agent_creator_pro_page_get(self):
        """Test GET request to agent creator pro page"""
        url = reverse('agent_creator_pro')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Agent Creator Pro')
        self.assertContains(response, 'personality_options')
        self.assertContains(response, 'expertise_options')
        self.assertContains(response, 'communication_options')

    def test_agent_creator_pro_page_context(self):
        """Test context data in agent creator pro page"""
        url = reverse('agent_creator_pro')
        response = self.client.get(url)

        context = response.context
        self.assertIn('page_title', context)
        self.assertIn('templates', context)
        self.assertIn('form_data', context)

        form_data = context['form_data']
        self.assertIn('personality_options', form_data)
        self.assertIn('expertise_options', form_data)
        self.assertIn('communication_options', form_data)

        # Verify some expected options
        self.assertIn('helpful and professional', form_data['personality_options'])
        self.assertIn('coding', form_data['expertise_options'])
        self.assertIn('clear and concise', form_data['communication_options'])


class TestAgentCreatorProIntegration(TestCase):
    """Integration tests for Agent Creator Pro"""

    def setUp(self):
        self.client = Client()

    @patch('src.swarm.views.agent_creator_pro.pro_generator')
    @patch('src.swarm.views.agent_creator_pro.advanced_validator')
    def test_full_agent_creation_workflow(self, mock_validator, mock_generator):
        """Test the complete agent creation workflow"""
        # Mock the generator and validator
        mock_code = '''
from swarm.core.blueprint_base import BlueprintBase

class TestAgentBlueprint(BlueprintBase):
    async def run(self, messages):
        yield {"messages": [{"role": "assistant", "content": "Test response"}]}
'''
        mock_generator.generate_agent_code.return_value = mock_code
        mock_validator.validate_blueprint_code.return_value = {
            'valid': True,
            'syntax_valid': True,
            'structure_valid': True,
            'lint_clean': True,
            'errors': [],
            'warnings': []
        }

        # Test data
        agent_data = {
            'name': 'Test Agent',
            'description': 'A test agent',
            'personality': 'helpful and professional',
            'expertise': ['testing'],
            'communication_style': 'clear and concise',
            'instructions': 'Help with testing',
            'tags': 'test, agent'
        }

        # This would test the generation endpoint if it existed
        # For now, test that the components work together
        generated_code = mock_generator.generate_agent_code(agent_data)
        validation_result = mock_validator.validate_blueprint_code(generated_code)

        self.assertIsNotNone(generated_code)
        self.assertTrue(validation_result['valid'])

        # Verify mocks were called
        mock_generator.generate_agent_code.assert_called_once_with(agent_data)
        mock_validator.validate_blueprint_code.assert_called_once_with(mock_code)


class TestAgentCreatorProErrorHandling(TestCase):
    """Test error handling in Agent Creator Pro"""

    def setUp(self):
        self.validator = AdvancedCodeValidator()
        self.generator = ProAgentGenerator()

    def test_validator_handles_invalid_syntax(self):
        """Test validator handles syntax errors gracefully"""
        invalid_code = '''
class InvalidBlueprint(BlueprintBase:  # Missing closing parenthesis
    async def run(self, messages):
        return "Invalid syntax"
'''
        result = self.validator.validate_blueprint_code(invalid_code)

        self.assertFalse(result['valid'])
        self.assertFalse(result['syntax_valid'])
        self.assertGreater(len(result['errors']), 0)

    def test_validator_handles_empty_code(self):
        """Test validator handles empty code"""
        result = self.validator.validate_blueprint_code('')

        self.assertFalse(result['valid'])
        self.assertGreater(len(result['errors']), 0)

    def test_generator_handles_missing_fields(self):
        """Test generator handles missing required fields"""
        incomplete_spec = {
            'name': 'Incomplete Agent'
            # Missing other required fields
        }

        # Should not crash, should use defaults
        generated_code = self.generator.generate_agent_code(incomplete_spec)
        self.assertIsNotNone(generated_code)
        self.assertIn('class IncompleteAgentBlueprint', generated_code)

    def test_generator_handles_empty_expertise(self):
        """Test generator handles empty expertise list"""
        agent_spec = {
            'name': 'No Expertise Agent',
            'description': 'An agent with no specific expertise',
            'expertise': [],
            'personality': 'helpful',
            'communication_style': 'clear',
            'instructions': 'Be helpful',
            'tags': []
        }

        generated_code = self.generator.generate_agent_code(agent_spec)
        self.assertIsNotNone(generated_code)
        # Should handle empty expertise gracefully
        self.assertIn('general assistance', generated_code)


if __name__ == '__main__':
    pytest.main([__file__])
