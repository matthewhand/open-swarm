"""
Secure subprocess execution utilities

This module provides secure alternatives to subprocess.run with shell=True,
which is vulnerable to command injection attacks.
"""

import shlex
import subprocess
from typing import List, Optional, Tuple


def execute_command_safe(
    command: List[str] | str,
    timeout: Optional[int] = None,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False
) -> subprocess.CompletedProcess:
    """
    Execute a command safely without shell=True vulnerability.
    
    Args:
        command: Command as list of arguments or string to parse
        timeout: Timeout in seconds
        capture_output: Capture stdout and stderr
        text: Return output as string (True) or bytes (False)
        check: Raise CalledProcessError if command fails
        
    Returns:
        CompletedProcess with result
        
    Raises:
        ValueError: If command is empty or invalid
        subprocess.TimeoutExpired: If command times out
        subprocess.CalledProcessError: If check=True and command fails
    """
    # Validate command
    if not command:
        raise ValueError("Command cannot be empty")
    
    # Convert string command to list using shlex for safe parsing
    if isinstance(command, str):
        try:
            command_list = shlex.split(command)
        except ValueError as e:
            raise ValueError(f"Invalid command syntax: {e}") from e
    else:
        command_list = command
    
    # Validate command list
    if not command_list:
        raise ValueError("Command list cannot be empty after parsing")
    
    # Execute with shell=False for security
    result = subprocess.run(
        command_list,
        shell=False,  # CRITICAL: Prevents command injection
        capture_output=capture_output,
        text=text,
        timeout=timeout,
        check=check
    )
    
    return result


def execute_command_with_fallback(
    command: List[str] | str,
    timeout: Optional[int] = None,
    capture_output: bool = True,
    text: bool = True
) -> Tuple[subprocess.CompletedProcess, bool]:
    """
    Execute command with fallback for compatibility.
    
    Args:
        command: Command as list or string
        timeout: Timeout in seconds
        capture_output: Capture stdout and stderr
        text: Return output as string
        
    Returns:
        Tuple of (result, used_fallback)
        
    Note:
        First tries safe execution, falls back to shell=True only if necessary
        for compatibility with complex shell features (not recommended)
    """
    try:
        # Try safe execution first
        result = execute_command_safe(
            command,
            timeout=timeout,
            capture_output=capture_output,
            text=text,
            check=False
        )
        return result, False  # False = did not use fallback
    except (ValueError, subprocess.CalledProcessError) as e:
        # Only use shell=True as last resort for compatibility
        # This should be rare and documented
        result = subprocess.run(
            command if isinstance(command, str) else " ".join(command),
            shell=True,  # Fallback - document why this is needed
            capture_output=capture_output,
            text=text,
            timeout=timeout
        )
        return result, True  # True = used fallback


def validate_command_safety(command: List[str] | str) -> bool:
    """
    Validate command for security best practices.
    
    Args:
        command: Command to validate
        
    Returns:
        True if command appears safe, False if potential issues found
    """
    if not command:
        return False
    
    # Convert to list for analysis
    if isinstance(command, str):
        try:
            command_list = shlex.split(command)
        except ValueError:
            return False
    else:
        command_list = command
    
    # Check for suspicious patterns
    suspicious_patterns = [';', '&&', '||', '|', '>', '<', '`', '$(', '${']
    
    for arg in command_list:
        # Check for command injection patterns
        for pattern in suspicious_patterns:
            if pattern in arg:
                return False
    
    # Check for dangerous commands
    dangerous_commands = ['rm', 'mv', 'chmod', 'chown', 'dd', 'mkfs']
    if command_list[0] in dangerous_commands:
        return False
    
    return True


def sanitize_environment(env: Optional[dict] = None) -> dict:
    """
    Sanitize environment variables for subprocess execution.
    
    Args:
        env: Optional environment dict to sanitize
        
    Returns:
        Sanitized environment dictionary
    """
    if env is None:
        env = {}
    
    # Remove potentially dangerous environment variables
    dangerous_vars = ['PATH', 'LD_PRELOAD', 'LD_LIBRARY_PATH']
    
    for var in dangerous_vars:
        if var in env:
            # Keep only known-safe paths
            safe_paths = ["/usr/bin", "/bin", "/usr/local/bin"]
            if var == "PATH":
                env[var] = ":".join(safe_paths)
            else:
                del env[var]
    
    return env


class SecureCommandExecutor:
    """
    Context manager for secure command execution.
    
    Provides additional safety checks and logging.
    """
    
    def __init__(self, timeout: Optional[int] = None):
        self.timeout = timeout
        self.last_command = None
        self.last_result = None
        self.used_fallback = False
    
    def execute(self, command: List[str] | str, **kwargs) -> subprocess.CompletedProcess:
        """Execute command with security checks."""
        # Validate before execution
        if not validate_command_safety(command):
            raise ValueError(f"Unsafe command detected: {command}")
        
        # Execute with safety
        result, used_fallback = execute_command_with_fallback(
            command,
            timeout=self.timeout,
            **kwargs
        )
        
        self.last_command = command
        self.last_result = result
        self.used_fallback = used_fallback
        
        if used_fallback:
            logger.warning(f"Used shell=True fallback for: {command}")
        
        return result
    
    def get_last_command(self) -> Optional[List[str] | str]:
        """Get last executed command."""
        return self.last_command
    
    def get_last_result(self) -> Optional[subprocess.CompletedProcess]:
        """Get last execution result."""
        return self.last_result
    
    def did_use_fallback(self) -> bool:
        """Check if fallback was used."""
        return self.used_fallback


# Import at module level for convenience
import logging
logger = logging.getLogger(__name__)
