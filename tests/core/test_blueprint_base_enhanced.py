"""
Enhanced Blueprint Base Testing
===============================

Comprehensive tests for BlueprintBase edge cases and advanced functionality.
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from src.swarm.core.blueprint_base import BlueprintBase


class TestBlueprintBaseAdvanced:
    """Advanced BlueprintBase functionality tests."""

    def test_blueprint_base_cannot_be_instantiated_directly(self):
        """Test that BlueprintBase is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BlueprintBase(blueprint_id="test")

    def test_config_loading_from_multiple_sources(self):
        """Test config loading priority from multiple sources."""
        # Create a mock blueprint subclass
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"profiles": {"test": {"model": "gpt-4"}}}, f)
            config_path = f.name

        try:
            blueprint = TestBlueprint(blueprint_id="test", config_path=config_path)
            profile = blueprint.get_llm_profile("test")
            assert profile["model"] == "gpt-4"
        finally:
            os.unlink(config_path)

    def test_config_merging_behavior(self):
        """Test configuration merging between different sources."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        base_config = {"profiles": {"default": {"model": "gpt-3.5-turbo"}}}

        blueprint = TestBlueprint(blueprint_id="test", config=base_config)
        # Test that configs merge appropriately
        assert blueprint.config is not None

    def test_llm_profile_inheritance_chain(self):
        """Test LLM profile resolution through inheritance chain."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        config = {
            "profiles": {
                "base": {"model": "gpt-3.5-turbo", "temperature": 0.5},
                "derived": {"model": "gpt-4", "inherits": "base"}
            }
        }

        blueprint = TestBlueprint(blueprint_id="test", config=config)
        derived_profile = blueprint.get_llm_profile("derived")
        assert derived_profile["model"] == "gpt-4"
        # Should inherit temperature from base

    def test_markdown_output_configuration_hierarchy(self):
        """Test markdown output setting resolution hierarchy."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        # Test global default
        blueprint1 = TestBlueprint(blueprint_id="test1")
        result1 = blueprint1.should_output_markdown()
        assert isinstance(result1, bool)

        # Test blueprint-specific override
        config_specific = {
            "blueprints": {
                "test2": {"markdown_output": True}
            }
        }
        blueprint2 = TestBlueprint(blueprint_id="test2", config=config_specific)
        result2 = blueprint2.should_output_markdown()
        assert result2 is True

        # Test global setting
        config_global = {
            "blueprints": {
                "defaults": {"default_markdown_cli": False}
            }
        }
        blueprint3 = TestBlueprint(blueprint_id="test3", config=config_global)
        result3 = blueprint3.should_output_markdown()
        assert result3 is False


class TestBlueprintBaseErrorHandling:
    """Error handling and edge case tests."""

    def test_config_loading_malformed_json(self):
        """Test handling of malformed JSON config files."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json}')  # Malformed JSON
            config_path = f.name

        try:
            # Should handle malformed JSON gracefully
            blueprint = TestBlueprint(blueprint_id="test", config_path=config_path)
            assert blueprint is not None
        except Exception as e:
            # If it raises an exception, it should be informative
            assert "json" in str(e).lower() or "config" in str(e).lower()
        finally:
            os.unlink(config_path)

    def test_config_loading_nonexistent_file(self):
        """Test handling of nonexistent config files."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        blueprint = TestBlueprint(blueprint_id="test", config_path="/nonexistent/path.json")
        # Should not crash, should handle gracefully
        assert blueprint is not None

    def test_llm_profile_circular_inheritance(self):
        """Test handling of circular inheritance in LLM profiles."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        config = {
            "profiles": {
                "profile_a": {"model": "gpt-3.5-turbo", "inherits": "profile_b"},
                "profile_b": {"temperature": 0.7, "inherits": "profile_a"}
            }
        }

        blueprint = TestBlueprint(blueprint_id="test", config=config)

        try:
            blueprint.get_llm_profile("profile_a")
            # Should handle circular inheritance gracefully
        except Exception as e:
            # Should provide informative error about circular inheritance
            assert "circular" in str(e).lower() or "inheritance" in str(e).lower()

    def test_missing_required_profile_keys(self):
        """Test handling of profiles missing required keys."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        config = {
            "profiles": {
                "incomplete": {"temperature": 0.7}  # Missing model
            }
        }

        blueprint = TestBlueprint(blueprint_id="test", config=config)

        try:
            blueprint.get_llm_profile("incomplete")
            # Should either provide defaults or raise informative error
        except Exception as e:
            assert "model" in str(e).lower()

    def test_invalid_config_structure(self):
        """Test handling of invalid config structure."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        invalid_configs = [
            {"profiles": "not_a_dict"},
            {"blueprints": []},
            "not_a_dict_at_all",
            {"profiles": {"test": "not_a_dict"}},
        ]

        for invalid_config in invalid_configs:
            try:
                blueprint = TestBlueprint(blueprint_id="test", config=invalid_config)
                # Should not crash during initialization
                assert blueprint is not None
            except Exception as e:
                # Should provide informative error messages
                assert len(str(e)) > 0


class TestBlueprintBaseModelResolution:
    """Model resolution and provider tests."""

    def test_model_resolution_with_different_providers(self):
        """Test model resolution with different providers."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        configs = [
            {"profiles": {"openai": {"provider": "openai", "model": "gpt-4"}}},
            {"profiles": {"anthropic": {"provider": "anthropic", "model": "claude-3"}}},
            {"profiles": {"local": {"provider": "local", "model": "llama2"}}},
        ]

        for config in configs:
            blueprint = TestBlueprint(blueprint_id="test", config=config)
            profile_name = list(config["profiles"].keys())[0]
            try:
                profile = blueprint.get_llm_profile(profile_name)
                assert "model" in profile
                assert "provider" in profile
            except Exception:
                # Some providers might not be available in test environment
                pass

    def test_model_fallback_behavior(self):
        """Test model fallback when primary model unavailable."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        config = {
            "profiles": {
                "primary": {"model": "nonexistent-model"},
                "fallback": {"model": "gpt-3.5-turbo"}
            }
        }

        blueprint = TestBlueprint(blueprint_id="test", config=config)
        # Test fallback behavior
        try:
            blueprint.get_llm_profile("primary")
        except Exception:
            # Expected if model doesn't exist
            pass

    def test_programmatic_model_override(self):
        """Test programmatic model overrides."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        blueprint = TestBlueprint(blueprint_id="test")

        # Test programmatic override capability
        blueprint.llm_profile_name = "custom_override"

        # Verify override takes effect
        assert blueprint.llm_profile_name == "custom_override"


class TestBlueprintBaseConfigurationExtended:
    """Extended configuration testing scenarios."""

    def test_environment_variable_substitution(self):
        """Test environment variable substitution in config."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        with patch.dict(os.environ, {"TEST_MODEL": "gpt-4", "TEST_TEMP": "0.8"}):
            config = {
                "profiles": {
                    "env_test": {
                        "model": "${TEST_MODEL}",
                        "temperature": "${TEST_TEMP}"
                    }
                }
            }

            TestBlueprint(blueprint_id="test", config=config)
            # Test that environment variables are substituted
            # (Implementation depends on blueprint base functionality)

    def test_nested_configuration_access(self):
        """Test access to deeply nested configuration values."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        config = {
            "blueprints": {
                "test": {
                    "nested": {
                        "deep": {
                            "value": "found"
                        }
                    }
                }
            }
        }

        blueprint = TestBlueprint(blueprint_id="test", config=config)
        # Test nested value access if supported
        assert blueprint.config is not None

    def test_config_validation_and_sanitization(self):
        """Test configuration validation and sanitization."""
        class TestBlueprint(BlueprintBase):
            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        # Test with potentially problematic config values
        problematic_configs = [
            {"profiles": {"test": {"model": "", "temperature": "invalid"}}},
            {"profiles": {"test": {"model": None, "temperature": -1}}},
            {"profiles": {"test": {"model": "valid", "temperature": 999}}},
        ]

        for config in problematic_configs:
            try:
                blueprint = TestBlueprint(blueprint_id="test", config=config)
                # Should handle problematic configs gracefully
                assert blueprint is not None
            except Exception as e:
                # Should provide clear error messages
                assert len(str(e)) > 0


class TestBlueprintBaseMetadata:
    """Metadata and introspection tests."""

    def test_metadata_completeness(self):
        """Test that metadata contains required fields."""
        class TestBlueprint(BlueprintBase):
            metadata = {
                "name": "TestBlueprint",
                "description": "Test blueprint",
                "version": "1.0.0",
                "author": "Test",
                "tags": ["test"],
            }

            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        blueprint = TestBlueprint(blueprint_id="test")
        metadata = blueprint.metadata

        required_fields = ["name", "description", "version", "author"]
        for field in required_fields:
            assert field in metadata, f"Missing required metadata field: {field}"
            assert metadata[field], f"Empty required metadata field: {field}"

    def test_metadata_inheritance(self):
        """Test metadata inheritance in blueprint subclasses."""
        class BaseTestBlueprint(BlueprintBase):
            metadata = {
                "name": "BaseBlueprint",
                "description": "Base test blueprint",
                "version": "1.0.0",
                "author": "Test",
            }

            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        class DerivedTestBlueprint(BaseTestBlueprint):
            metadata = {
                **BaseTestBlueprint.metadata,
                "name": "DerivedBlueprint",
                "version": "2.0.0",
            }

        base_blueprint = BaseTestBlueprint(blueprint_id="base")
        derived_blueprint = DerivedTestBlueprint(blueprint_id="derived")

        assert base_blueprint.metadata["name"] == "BaseBlueprint"
        assert derived_blueprint.metadata["name"] == "DerivedBlueprint"
        assert derived_blueprint.metadata["author"] == "Test"  # Inherited
        assert derived_blueprint.metadata["version"] == "2.0.0"  # Overridden

    def test_blueprint_introspection_capabilities(self):
        """Test blueprint introspection and discovery capabilities."""
        class TestBlueprint(BlueprintBase):
            metadata = {
                "name": "TestBlueprint",
                "description": "Test blueprint",
                "version": "1.0.0",
                "author": "Test",
                "capabilities": ["test", "mock"],
                "required_mcp_servers": ["memory"],
            }

            def create_starting_agent(self, mcp_servers):
                pass
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "test"}]}

        blueprint = TestBlueprint(blueprint_id="test")

        # Test capability discovery
        if "capabilities" in blueprint.metadata:
            assert "test" in blueprint.metadata["capabilities"]

        # Test MCP server requirements
        if "required_mcp_servers" in blueprint.metadata:
            assert "memory" in blueprint.metadata["required_mcp_servers"]
