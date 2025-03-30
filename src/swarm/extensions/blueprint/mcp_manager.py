import asyncio
import logging
import os
import shlex
import shutil
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.mcp import MCPServer, MCPServerStdio

# Import necessary utility from config_loader
from .config_loader import _substitute_env_vars

logger = logging.getLogger("swarm.mcp")

async def start_mcp_server_instance(
    stack: AsyncExitStack,
    server_name: str,
    server_config: Dict[str, Any],
    project_root: Path,
    default_startup_timeout: float,
    base_env: Optional[Dict[str, str]] = None
) -> Optional[MCPServer]:
    """
    Starts a single MCP server instance based on configuration.

    Args:
        stack (AsyncExitStack): The context stack to manage the server lifecycle.
        server_name (str): The unique name of the server (e.g., "slack", "git").
        server_config (Dict[str, Any]): The configuration dictionary for this server.
        project_root (Path): The root directory of the project.
        default_startup_timeout (float): The default timeout if not specified in config.
        base_env (Optional[Dict[str, str]]): Base environment variables (usually os.environ.copy()).

    Returns:
        Optional[MCPServer]: The started MCPServer instance, or None if startup failed.
    """
    if not server_config:
        logger.error(f"[{server_name}] Config is empty or None.")
        return None

    base_environment = base_env if base_env is not None else os.environ.copy()

    # --- Command Parsing ---
    command_list_or_str = server_config.get("command")
    if not command_list_or_str:
        logger.error(f"[{server_name}] Command missing in config.")
        return None

    additional_args = _substitute_env_vars(server_config.get("args", []))
    if not isinstance(additional_args, list):
        logger.error(f"[{server_name}] Config 'args' must be a list.")
        return None

    executable_name: str = ""
    base_args: List[str] = []
    try:
        if isinstance(command_list_or_str, str):
            cmd_str_expanded = _substitute_env_vars(command_list_or_str)
            cmd_parts = shlex.split(cmd_str_expanded)
            if not cmd_parts: raise ValueError("Empty 'command' string after expansion")
            executable_name = cmd_parts[0]
            base_args = cmd_parts[1:]
        elif isinstance(command_list_or_str, list):
            cmd_parts = [_substitute_env_vars(p) for p in command_list_or_str]
            if not cmd_parts: raise ValueError("Empty 'command' list after expansion")
            executable_name = cmd_parts[0]
            base_args = cmd_parts[1:]
        else:
            raise TypeError("'command' must be a string or a list")
        full_args = base_args + additional_args
    except Exception as e:
        logger.error(f"[{server_name}] Command/Args parsing error: {e}", exc_info=logger.level <= logging.DEBUG)
        return None

    # --- Find Executable Path ---
    cmd_path = shutil.which(executable_name)
    # Check in virtual environment if not found globally
    if not cmd_path and sys.prefix != sys.base_prefix:
        for bindir in ['bin', 'Scripts']: # Common venv bin directories
            venv_path = Path(sys.prefix) / bindir / executable_name
            if venv_path.is_file():
                cmd_path = str(venv_path)
                logger.debug(f"[{server_name}] Found executable in venv: {cmd_path}")
                break
    if not cmd_path:
        logger.error(f"[{server_name}] Executable '{executable_name}' not found in PATH or virtual environment.")
        return None

    # --- Environment Variables ---
    process_env = base_environment.copy()
    custom_env_config = server_config.get("env", {})
    if not isinstance(custom_env_config, dict):
        logger.error(f"[{server_name}] Config 'env' must be a dictionary.")
        return None
    custom_env_substituted = _substitute_env_vars(custom_env_config)
    process_env.update(custom_env_substituted)
    logger.debug(f"[{server_name}] Custom Env Vars Merged: {list(custom_env_substituted.keys())}")

    # --- Working Directory ---
    cwd = _substitute_env_vars(server_config.get("cwd"))
    cwd_path: Optional[str] = None
    if cwd:
        try:
            cwd_path_obj = Path(cwd)
            if not cwd_path_obj.is_absolute():
                # Resolve relative to project root
                cwd_path_obj = (project_root / cwd_path_obj).resolve()
            else:
                # Verify absolute path exists
                cwd_path_obj = cwd_path_obj.resolve(strict=True)

            if cwd_path_obj.is_dir():
                cwd_path = str(cwd_path_obj)
            else:
                logger.warning(f"[{server_name}] Invalid CWD specified: '{cwd_path_obj}' is not a directory.")
        except FileNotFoundError:
            logger.warning(f"[{server_name}] CWD '{cwd_path_obj}' not found.")
        except Exception as e:
            logger.warning(f"[{server_name}] Error resolving CWD '{cwd}': {e}.")
            # Continue without setting cwd if resolution fails

    # --- Prepare MCP Parameters ---
    mcp_params: Dict[str, Any] = {"command": cmd_path, "args": full_args, "env": process_env}
    if cwd_path:
        mcp_params["cwd"] = cwd_path
    if "encoding" in server_config:
        mcp_params["encoding"] = server_config["encoding"]
    if "encoding_error_handler" in server_config:
        mcp_params["encoding_error_handler"] = server_config["encoding_error_handler"]
    logger.debug(f"[{server_name}] Path:{cmd_path}, Args:{full_args}, CWD:{cwd_path or 'Default'}")

    # --- Startup Timeout ---
    startup_timeout = default_startup_timeout
    try:
        config_timeout = server_config.get("startup_timeout")
        if config_timeout is not None:
            parsed_timeout = float(config_timeout)
            if parsed_timeout > 0:
                startup_timeout = parsed_timeout
            else:
                logger.warning(f"[{server_name}] Invalid startup_timeout ({config_timeout}), using default: {default_startup_timeout}s")
    except (ValueError, TypeError):
        logger.warning(f"[{server_name}] Invalid startup_timeout value ('{server_config.get('startup_timeout')}'), using default: {default_startup_timeout}s")

    # --- Start Server ---
    logger.info(f"[{server_name}] Starting (timeout {startup_timeout:.1f}s): {' '.join(shlex.quote(p) for p in [cmd_path] + full_args)}")
    try:
        server_instance = MCPServerStdio(name=server_name, params=mcp_params)
        # Wrap the context manager entry with asyncio.wait_for
        started_server = await asyncio.wait_for(
            stack.enter_async_context(server_instance),
            timeout=startup_timeout
        )
        logger.info(f"[{server_name}] Started successfully.")
        return started_server
    except asyncio.TimeoutError:
        logger.error(f"[{server_name}] Failed: Startup timed out after {startup_timeout:.1f} seconds.")
        # AsyncExitStack will handle cleanup (__aexit__) attempt
        return None
    except Exception as e:
        logger.error(f"[{server_name}] Failed start/connect: {e}", exc_info=logger.level <= logging.DEBUG)
        # AsyncExitStack will handle cleanup (__aexit__) attempt
        return None
