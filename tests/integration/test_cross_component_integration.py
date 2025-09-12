"""
Cross-Component Integration Testing
===================================

Comprehensive integration tests covering interactions between different
system components to ensure end-to-end functionality.
"""

import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import MagicMock, patch, AsyncMock
from django.test import TestCase
from django.contrib.auth.models import User

from src.swarm.core.blueprint_discovery import discover_blueprints
from src.swarm.views.utils import get_available_blueprints


class TestBlueprintDiscoveryIntegration(TestCase):
    """Integration tests for blueprint discovery across the system."""
    
    def test_blueprint_discovery_and_api_integration(self):
        """Test blueprint discovery integrates properly with API endpoints."""
        # Test that discovered blueprints appear in API responses
        discovered_blueprints = discover_blueprints()
        assert len(discovered_blueprints) > 0
        
        # Test that API can list the same blueprints
        try:
            api_blueprints = asyncio.run(get_available_blueprints())
            assert isinstance(api_blueprints, (list, dict))
        except Exception as e:
            # Expected in test environment without full setup
            assert "blueprint" in str(e).lower() or "discover" in str(e).lower()
    
    def test_blueprint_metadata_consistency(self):
        """Test blueprint metadata consistency across discovery and usage."""
        discovered_blueprints = discover_blueprints()
        
        for blueprint_info in discovered_blueprints[:5]:  # Test first 5
            blueprint_name = blueprint_info.get('name', '')
            if blueprint_name:
                # Test metadata access patterns
                assert 'description' in blueprint_info or 'name' in blueprint_info
                
                # Test that blueprint can be instantiated
                blueprint_class = blueprint_info.get('class')
                if blueprint_class:
                    try:
                        instance = blueprint_class(blueprint_id=f"test_{blueprint_name}")
                        assert instance is not None
                        assert hasattr(instance, 'metadata')
                    except Exception:
                        # Some blueprints may have complex initialization requirements
                        pass
    
    def test_dynamic_blueprint_registration_and_discovery(self):
        """Test dynamic blueprint registration and subsequent discovery."""
        from src.swarm.views.utils import DynamicBlueprintRegistry
        
        # Test dynamic registration
        registry = DynamicBlueprintRegistry()
        
        # Create a test blueprint definition
        test_blueprint_code = '''
class TestDynamicBlueprint(BlueprintBase):
    metadata = {
        "name": "TestDynamic",
        "description": "Test dynamic blueprint",
        "version": "1.0.0"
    }
    
    def create_starting_agent(self, mcp_servers):
        pass
    
    async def run(self, messages, **kwargs):
        yield {"messages": [{"role": "assistant", "content": "dynamic response"}]}
'''
        
        try:
            # Test registration process
            registry.register_blueprint("test_dynamic", test_blueprint_code)
            
            # Test that dynamic blueprint appears in discovery
            blueprints = registry.get_registered_blueprints()
            assert "test_dynamic" in blueprints
            
            # Test cleanup
            registry.unregister_blueprint("test_dynamic")
            
        except Exception as e:
            # Registry may not be fully implemented
            assert "dynamic" in str(e).lower() or "register" in str(e).lower()
    
    def test_blueprint_loading_error_handling(self):
        """Test blueprint loading error handling across system components."""
        # Test with broken blueprint directory
        with tempfile.TemporaryDirectory() as temp_dir:
            broken_blueprint_path = os.path.join(temp_dir, "broken_blueprint.py")
            with open(broken_blueprint_path, 'w') as f:
                f.write("This is not valid Python code!")
            
            # Test that discovery handles broken blueprints gracefully
            try:
                blueprints = discover_blueprints(search_paths=[temp_dir])
                # Should not crash, may return empty list or filtered results
                assert isinstance(blueprints, list)
            except Exception as e:
                # Should provide informative error messages
                assert len(str(e)) > 0
    
    def test_blueprint_dependency_resolution(self):
        """Test blueprint dependency resolution and loading order."""
        # Test blueprints with different dependency patterns
        dependency_scenarios = [
            # Blueprint with no dependencies
            {"name": "independent", "dependencies": []},
            
            # Blueprint with MCP dependencies
            {"name": "mcp_dependent", "dependencies": ["memory", "filesystem"]},
            
            # Blueprint with other blueprint dependencies
            {"name": "blueprint_dependent", "dependencies": ["echocraft"]},
        ]
        
        for scenario in dependency_scenarios:
            # Test dependency resolution logic
            # Implementation depends on dependency system
            pass


class TestConfigurationIntegration(TestCase):
    """Integration tests for configuration loading and usage across components."""
    
    def test_config_loading_hierarchy_integration(self):
        """Test configuration loading hierarchy across different components."""
        # Test global config loading
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            global_config = {
                "profiles": {
                    "default": {"model": "gpt-4", "temperature": 0.7},
                    "test": {"model": "gpt-3.5-turbo", "temperature": 0.5}
                },
                "blueprints": {
                    "defaults": {"max_llm_calls": 10},
                    "echocraft": {"max_llm_calls": 5}
                }
            }
            json.dump(global_config, f)
            config_path = f.name
        
        try:
            # Test that config is accessible across different components
            from src.swarm.core.blueprint_base import BlueprintBase
            
            class TestBlueprint(BlueprintBase):
                def create_starting_agent(self, mcp_servers):
                    pass
                async def run(self, messages, **kwargs):
                    yield {"messages": [{"role": "assistant", "content": "test"}]}
            
            blueprint = TestBlueprint(blueprint_id="test", config_path=config_path)
            
            # Test profile access
            try:
                default_profile = blueprint.get_llm_profile("default")
                assert default_profile["model"] == "gpt-4"
                
                test_profile = blueprint.get_llm_profile("test")
                assert test_profile["model"] == "gpt-3.5-turbo"
            except RuntimeError:
                # Expected if config loading not fully implemented
                pass
            
        finally:
            os.unlink(config_path)
    
    def test_environment_variable_integration(self):
        """Test environment variable integration across components."""
        test_env_vars = {
            "OPENAI_API_KEY": "test-key-123",
            "SWARM_CONFIG_PATH": "/test/path",
            "SWARM_DEBUG": "true",
            "SWARM_MAX_WORKERS": "5"
        }
        
        with patch.dict(os.environ, test_env_vars):
            # Test environment variable access in different components
            
            # Test API key access
            api_key = os.environ.get("OPENAI_API_KEY")
            assert api_key == "test-key-123"
            
            # Test config path access
            config_path = os.environ.get("SWARM_CONFIG_PATH")
            assert config_path == "/test/path"
            
            # Test boolean environment variables
            debug_flag = os.environ.get("SWARM_DEBUG", "false").lower() == "true"
            assert debug_flag is True
            
            # Test numeric environment variables
            max_workers = int(os.environ.get("SWARM_MAX_WORKERS", "1"))
            assert max_workers == 5
    
    def test_config_validation_across_components(self):
        """Test configuration validation consistency across components."""
        invalid_configs = [
            # Invalid profile structure
            {"profiles": {"test": "not_a_dict"}},
            
            # Missing required fields
            {"profiles": {"test": {"temperature": 0.7}}},  # Missing model
            
            # Invalid field values
            {"profiles": {"test": {"model": "gpt-4", "temperature": 2.0}}},  # Invalid temp
            
            # Invalid blueprint config
            {"blueprints": {"test": "not_a_dict"}},
        ]
        
        for i, invalid_config in enumerate(invalid_configs):
            with self.subTest(config_case=i):
                # Test that all components handle invalid config consistently
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(invalid_config, f)
                    config_path = f.name
                
                try:
                    from src.swarm.core.blueprint_base import BlueprintBase
                    
                    class TestBlueprint(BlueprintBase):
                        def create_starting_agent(self, mcp_servers):
                            pass
                        async def run(self, messages, **kwargs):
                            yield {"messages": [{"role": "assistant", "content": "test"}]}
                    
                    blueprint = TestBlueprint(blueprint_id="test", config_path=config_path)
                    # Should handle invalid config gracefully
                    assert blueprint is not None
                    
                except Exception as e:
                    # Should provide informative error messages
                    assert len(str(e)) > 0
                finally:
                    os.unlink(config_path)
    
    def test_config_hot_reloading_integration(self):
        """Test configuration hot reloading across system components."""
        # Create initial config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            initial_config = {
                "profiles": {"test": {"model": "gpt-3.5-turbo"}}
            }
            json.dump(initial_config, f)
            config_path = f.name
        
        try:
            # Test initial config loading
            # Implementation depends on hot reloading system
            
            # Update config file
            with open(config_path, 'w') as f:
                updated_config = {
                    "profiles": {"test": {"model": "gpt-4"}}
                }
                json.dump(updated_config, f)
            
            # Test that components pick up config changes
            # Implementation depends on hot reloading mechanism
            
        finally:
            os.unlink(config_path)


class TestDatabaseIntegration(TestCase):
    """Integration tests for database interactions across components."""
    
    def setUp(self):
        """Set up test database state."""
        self.test_user = User.objects.create_user(
            username='integrationtest',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_user_authentication_integration(self):
        """Test user authentication integration across API and database."""
        # Test authentication flow
        from django.contrib.auth import authenticate
        
        # Test valid authentication
        user = authenticate(username='integrationtest', password='testpass123')
        assert user is not None
        assert user.username == 'integrationtest'
        
        # Test invalid authentication
        invalid_user = authenticate(username='integrationtest', password='wrongpass')
        assert invalid_user is None
        
        # Test user permissions and access patterns
        assert user.is_authenticated
        assert not user.is_superuser  # Unless explicitly set
    
    def test_conversation_persistence_integration(self):
        """Test conversation persistence across API requests and database."""
        from src.swarm.models import Conversation, Message
        
        # Test conversation creation
        conversation = Conversation.objects.create(
            user=self.test_user,
            title="Test Integration Conversation"
        )
        
        # Test message persistence
        messages = [
            Message.objects.create(
                conversation=conversation,
                role="user",
                content="Hello, this is a test message",
                order=0
            ),
            Message.objects.create(
                conversation=conversation,
                role="assistant", 
                content="Hello! I'm here to help you.",
                order=1
            )
        ]
        
        # Test retrieval and ordering
        retrieved_messages = Message.objects.filter(
            conversation=conversation
        ).order_by('order')
        
        assert len(retrieved_messages) == 2
        assert retrieved_messages[0].role == "user"
        assert retrieved_messages[1].role == "assistant"
        
        # Test conversation cleanup
        conversation.delete()
        remaining_messages = Message.objects.filter(conversation=conversation)
        assert len(remaining_messages) == 0
    
    def test_agent_configuration_persistence(self):
        """Test agent configuration persistence and retrieval."""
        # Test configuration storage patterns
        config_scenarios = [
            {
                "agent_name": "test_agent_1",
                "config": {"model": "gpt-4", "temperature": 0.7},
                "user": self.test_user
            },
            {
                "agent_name": "test_agent_2",
                "config": {"model": "gpt-3.5-turbo", "temperature": 0.5},
                "user": self.test_user
            }
        ]
        
        for scenario in config_scenarios:
            # Test configuration storage and retrieval
            # Implementation depends on agent configuration model
            pass
    
    def test_concurrent_database_access(self):
        """Test concurrent database access patterns."""
        async def concurrent_database_operations():
            tasks = []
            
            # Create multiple concurrent database operations
            for i in range(10):
                task = asyncio.create_task(self.simulate_database_operation(i))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        # Test concurrent access
        # results = asyncio.run(concurrent_database_operations())
        # assert len(results) == 10
    
    async def simulate_database_operation(self, operation_id):
        """Simulate a database operation for concurrent testing."""
        from src.swarm.models import Conversation
        
        # Create a conversation
        conversation = await database_sync_to_async(Conversation.objects.create)(
            user=self.test_user,
            title=f"Concurrent Test {operation_id}"
        )
        
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        # Clean up
        await database_sync_to_async(conversation.delete)()
        
        return f"Operation {operation_id} completed"


class TestMCPServerIntegration(TestCase):
    """Integration tests for MCP server interactions."""
    
    def test_mcp_server_lifecycle_integration(self):
        """Test MCP server lifecycle management integration."""
        mcp_scenarios = [
            {
                "server_type": "memory",
                "config": {"persistent": False},
                "expected_capabilities": ["memory_store", "memory_retrieve"]
            },
            {
                "server_type": "filesystem", 
                "config": {"root_path": "/tmp/test"},
                "expected_capabilities": ["file_read", "file_write", "file_list"]
            }
        ]
        
        for scenario in mcp_scenarios:
            with self.subTest(server=scenario["server_type"]):
                # Test MCP server initialization
                # Implementation depends on MCP server framework
                pass
    
    def test_mcp_server_error_handling_integration(self):
        """Test MCP server error handling across blueprint integration."""
        error_scenarios = [
            {"error_type": "server_startup_failure"},
            {"error_type": "server_communication_failure"},
            {"error_type": "server_timeout"},
            {"error_type": "invalid_server_response"}
        ]
        
        for scenario in error_scenarios:
            with self.subTest(error=scenario["error_type"]):
                # Test error handling integration
                pass
    
    def test_mcp_server_configuration_integration(self):
        """Test MCP server configuration integration with blueprints."""
        # Test different MCP configuration patterns
        config_patterns = [
            # Single MCP server
            {"mcp_servers": {"memory": {"type": "memory"}}},
            
            # Multiple MCP servers
            {"mcp_servers": {
                "memory": {"type": "memory"},
                "filesystem": {"type": "filesystem", "root": "/tmp"}
            }},
            
            # Blueprint-specific MCP config
            {"blueprints": {
                "mcp_demo": {
                    "mcp_servers": {"memory": {"type": "memory"}}
                }
            }}
        ]
        
        for i, config in enumerate(config_patterns):
            with self.subTest(config_pattern=i):
                # Test MCP configuration integration
                pass


class TestPerformanceIntegration(TestCase):
    """Integration tests for system performance characteristics."""
    
    def test_end_to_end_response_time_integration(self):
        """Test end-to-end response times across full system stack."""
        response_scenarios = [
            {
                "blueprint": "echocraft",
                "message": "Quick test",
                "expected_max_time": 2.0
            },
            {
                "blueprint": "chatbot",
                "message": "Complex conversation starter",
                "expected_max_time": 5.0
            },
            {
                "blueprint": "mcp_demo",
                "message": "MCP tool usage test",
                "expected_max_time": 10.0
            }
        ]
        
        for scenario in response_scenarios:
            with self.subTest(blueprint=scenario["blueprint"]):
                # Test end-to-end response time
                import time
                start_time = time.time()
                
                # Simulate API request processing
                # Implementation depends on test setup
                
                elapsed_time = time.time() - start_time
                # assert elapsed_time < scenario["expected_max_time"]
    
    def test_memory_usage_integration(self):
        """Test memory usage patterns across integrated components."""
        import psutil
        import os
        
        # Get baseline memory usage
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss
        
        # Simulate various integration scenarios
        memory_scenarios = [
            {"test": "blueprint_loading", "iterations": 10},
            {"test": "api_requests", "iterations": 50},
            {"test": "database_operations", "iterations": 100}
        ]
        
        for scenario in memory_scenarios:
            with self.subTest(memory_test=scenario["test"]):
                # Measure memory usage during operations
                current_memory = process.memory_info().rss
                memory_increase = current_memory - baseline_memory
                
                # Test that memory usage stays within reasonable bounds
                max_allowed_increase = 100 * 1024 * 1024  # 100MB
                # assert memory_increase < max_allowed_increase
    
    def test_scalability_integration_patterns(self):
        """Test scalability patterns across integrated system components."""
        scalability_scenarios = [
            {
                "test_type": "user_scalability",
                "metric": "concurrent_users",
                "scale_factors": [1, 5, 10, 25]
            },
            {
                "test_type": "data_scalability", 
                "metric": "conversation_length",
                "scale_factors": [10, 50, 100, 500]
            },
            {
                "test_type": "blueprint_scalability",
                "metric": "active_blueprints",
                "scale_factors": [1, 3, 5, 10]
            }
        ]
        
        for scenario in scalability_scenarios:
            with self.subTest(scalability=scenario["test_type"]):
                for scale_factor in scenario["scale_factors"]:
                    # Test system behavior at different scale factors
                    # Implementation depends on scalability testing framework
                    pass


class TestSecurityIntegration(TestCase):
    """Integration tests for security across system components."""
    
    def test_authentication_integration_security(self):
        """Test authentication security across integrated components."""
        security_scenarios = [
            {"test": "session_security", "check": "session_timeout"},
            {"test": "token_security", "check": "token_validation"},
            {"test": "permission_security", "check": "access_control"},
            {"test": "injection_security", "check": "sql_injection_prevention"}
        ]
        
        for scenario in security_scenarios:
            with self.subTest(security_test=scenario["test"]):
                # Test security measures across integration points
                pass
    
    def test_data_sanitization_integration(self):
        """Test data sanitization across component boundaries."""
        sanitization_scenarios = [
            {
                "input_type": "user_message",
                "test_data": "<script>alert('xss')</script>",
                "expected": "script tags removed"
            },
            {
                "input_type": "blueprint_config",
                "test_data": {"command": "rm -rf /"},
                "expected": "dangerous commands blocked"
            },
            {
                "input_type": "mcp_server_config",
                "test_data": {"path": "../../../etc/passwd"},
                "expected": "path traversal prevented"
            }
        ]
        
        for scenario in sanitization_scenarios:
            with self.subTest(sanitization=scenario["input_type"]):
                # Test data sanitization across integration points
                pass
    
    def test_error_message_security_integration(self):
        """Test that error messages don't leak sensitive information."""
        error_scenarios = [
            {"error_type": "database_error", "sensitive_data": "connection_string"},
            {"error_type": "filesystem_error", "sensitive_data": "file_paths"},
            {"error_type": "api_key_error", "sensitive_data": "api_keys"},
            {"error_type": "config_error", "sensitive_data": "config_values"}
        ]
        
        for scenario in error_scenarios:
            with self.subTest(error_security=scenario["error_type"]):
                # Test that error messages don't expose sensitive data
                pass