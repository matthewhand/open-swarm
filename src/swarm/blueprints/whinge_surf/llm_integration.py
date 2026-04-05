"""
LLM Integration for Whinge-Surf Blueprint

Provides LLM backend integration for code generation and analysis.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, List

# Setup logger
logger = logging.getLogger(__name__)


class WhingeSurfLLMBackend:
    """
    LLM backend integration for Whinge-Surf blueprint.
    
    Handles code generation, analysis, and self-update functionality.
    """
    
    def __init__(self, blueprint):
        """Initialize LLM backend with blueprint reference."""
        self.blueprint = blueprint
        self.llm_client = None
        self.model = "gpt-4o"  # Default model
    
    async def initialize(self):
        """Initialize LLM client."""
        try:
            # Import LLM client based on configuration
            from src.swarm.core.llm_client import LLMClient
            self.llm_client = LLMClient(
                model=self.model,
                temperature=0.3,
                max_tokens=2048
            )
            logger.info(f"Initialized LLM backend with model: {self.model}")
            return True
        except ImportError as e:
            logger.error(f"Failed to import LLM client: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize LLM backend: {e}")
            return False
    
    async def generate_code_from_prompt(
        self,
        prompt: str,
        src_file: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate code using LLM backend based on prompt and context.
        
        Args:
            prompt: Description of desired code changes
            src_file: Source file path for context
            context: Additional context (e.g., function names, classes)
            
        Returns:
            Generated code as string
        """
        if not self.llm_client:
            await self.initialize()
            if not self.llm_client:
                # Fallback to current behavior if LLM not available
                with open(src_file) as f:
                    return f.read()
        
        # Read current code for context
        try:
            with open(src_file) as f:
                current_code = f.read()
        except Exception as e:
            logger.error(f"Failed to read source file {src_file}: {e}")
            with open(src_file) as f:
                return f.read()
        
        # Build LLM prompt with context
        system_prompt = """
        You are an expert Python developer assisting with code generation for the Whinge-Surf blueprint.
        Follow these guidelines:
        1. Generate complete, working Python code
        2. Follow existing code style and conventions
        3. Include proper error handling
        4. Add comprehensive docstrings
        5. Ensure the code integrates well with the existing codebase
        """
        
        user_prompt = f"""
        Current code from {src_file}:
        ```python
        {current_code[:2000]}...  # truncated for brevity
        ```
        
        Request: {prompt}
        
        Additional context: {context if context else 'None'}
        
        Generate the complete updated code:
        """
        
        try:
            # Use LLM to generate code
            response = await self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="code"
            )
            
            # Extract code from response
            generated_code = self._extract_code_from_response(response)
            
            # Validate generated code
            if self._validate_generated_code(generated_code):
                return generated_code
            else:
                logger.warning("Generated code validation failed, falling back to original")
                return current_code
                
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return current_code
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract code block from LLM response."""
        # Try to extract code between ```python and ```
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # Try to extract code between ``` and ```
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # Return full response as fallback
        return response.strip()
    
    def _validate_generated_code(self, code: str) -> bool:
        """Basic validation of generated code."""
        if not code:
            return False
        
        # Check for common issues
        if "TODO" in code or "FIXME" in code:
            return False
        
        # Check for syntax errors (basic check)
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            logger.error(f"Syntax error in generated code: {e}")
            return False
    
    async def analyze_code_quality(
        self,
        code: str,
        criteria: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze code quality using LLM.
        
        Args:
            code: Code to analyze
            criteria: List of quality criteria to check
            
        Returns:
            Dictionary with analysis results
        """
        if not self.llm_client:
            await self.initialize()
            if not self.llm_client:
                return {c: "Not available (LLM not initialized)" for c in criteria}
        
        try:
            criteria_str = ", ".join(criteria)
            prompt = f"""
            Analyze the following Python code for these criteria: {criteria_str}
            
            Code:
            ```python
            {code[:1500]}...  # truncated
            ```
            
            Provide scores (1-10) and brief explanations for each criterion.
            Use JSON format: {{"criterion": "score (1-10)", "explanation": "..."}}
            """
            
            response = await self.llm_client.generate(
                system_prompt="You are a Python code quality expert.",
                user_prompt=prompt,
                response_format="json"
            )
            
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {c: "Analysis failed" for c in criteria}
                
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return {c: "Analysis failed" for c in criteria}
    
    async def generate_self_update(
        self,
        current_code: str,
        requirements: List[str]
    ) -> str:
        """
        Generate self-update code based on requirements.
        
        Args:
            current_code: Current implementation
            requirements: List of update requirements
            
        Returns:
            Updated code as string
        """
        if not self.llm_client:
            await self.initialize()
            if not self.llm_client:
                return current_code
        
        requirements_str = "\n".join(f"- {req}" for req in requirements)
        
        prompt = f"""
        Current Whinge-Surf implementation:
        ```python
        {current_code[:2000]}...  # truncated
        ```
        
        Update requirements:
        {requirements_str}
        
        Generate the complete updated implementation:
        """
        
        try:
            response = await self.llm_client.generate(
                system_prompt="You are updating the Whinge-Surf blueprint. Maintain backward compatibility.",
                user_prompt=prompt,
                response_format="code"
            )
            
            generated_code = self._extract_code_from_response(response)
            if self._validate_generated_code(generated_code):
                return generated_code
            return current_code
            
        except Exception as e:
            logger.error(f"Self-update generation failed: {e}")
            return current_code


class MockLLMBackend(WhingeSurfLLMBackend):
    """Mock LLM backend for testing without actual LLM calls."""
    
    def __init__(self, blueprint):
        super().__init__(blueprint)
        self.mock_responses = {}
    
    async def initialize(self):
        """Mock initialization - always succeeds."""
        return True
    
    async def generate_code_from_prompt(
        self,
        prompt: str,
        src_file: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Mock code generation - returns current code."""
        with open(src_file) as f:
            return f.read()
    
    def set_mock_response(self, prompt_key: str, response: str):
        """Set mock response for testing."""
        self.mock_responses[prompt_key] = response


# Utility function for blueprint integration
def get_llm_backend(blueprint) -> WhingeSurfLLMBackend:
    """Get LLM backend instance for blueprint."""
    if not hasattr(blueprint, '_llm_backend'):
        blueprint._llm_backend = WhingeSurfLLMBackend(blueprint)
    return blueprint._llm_backend
