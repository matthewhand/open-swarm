import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from dotenv import load_dotenv
from pathlib import Path
from typing import Any, Dict, Optional, Type

# Import BlueprintBase type hint carefully
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .blueprint_base import BlueprintBase

logger = logging.getLogger("swarm.cli")

# --- DEBUG PRINTS REMOVED BY CASCADE ---
# print(f"[DEBUG] CLI handler startup: sys.argv={sys.argv}")
# print(f"[DEBUG] CLI handler startup: LITELLM_MODEL={os.environ.get('LITELLM_MODEL')}, DEFAULT_LLM={os.environ.get('DEFAULT_LLM')}")

# --- FORCE LOAD .env EARLY for CLI/LLM ---
project_root = Path(__file__).parent.parent.parent.parent  # /home/chatgpt/open-swarm
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path=dotenv_path, override=True)
print("[DEBUG] LITELLM_API_KEY:", os.environ.get("LITELLM_API_KEY"))
# print(f"[DEBUG] Loaded .env from: {dotenv_path}")
# print(f"[DEBUG] LITELLM_MODEL={os.environ.get('LITELLM_MODEL')}")
# print(f"[DEBUG] LITELLM_BASE_URL={os.environ.get('LITELLM_BASE_URL')}")
# print(f"[DEBUG] LITELLM_API_KEY={'set' if os.environ.get('LITELLM_API_KEY') else 'NOT SET'}")

async def _run_blueprint_async_with_shutdown(blueprint: 'BlueprintBase', instruction: str):
    """Runs the blueprint's async method and handles graceful shutdown."""
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        print("\n[bold yellow]Shutdown signal received. Attempting graceful exit...[/bold yellow]", file=sys.stderr)
        logger.warning("Shutdown signal received.")
        stop_event.set()

    # Add signal handlers for SIGINT (Ctrl+C) and SIGTERM
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Fallback for Windows or environments where add_signal_handler is not supported
            try:
                # signal.signal must be called in the main thread
                signal.signal(sig, lambda s, f: loop.call_soon_threadsafe(signal_handler))
                logger.debug(f"Registered signal handler for {sig.name} using signal.signal fallback.")
            except ValueError as e:
                 logger.error(f"Could not set signal handler for {sig.name} using fallback: {e}. Graceful shutdown via signal might not work.")
            except Exception as e:
                 logger.error(f"Unexpected error setting fallback signal handler for {sig.name}: {e}", exc_info=True)

    # Instead of wrapping in a task and awaiting, use async for to support async generators
    try:
        # PATCH: Use blueprint.run instead of blueprint._run_non_interactive
        async for chunk in blueprint.run([
            {"role": "user", "content": instruction}
        ]):
            # Print the full JSON chunk
            print(json.dumps(chunk, ensure_ascii=False))
            # If chunk contains 'messages', print each assistant message's content for CLI/test UX
            if isinstance(chunk, dict) and 'messages' in chunk:
                for msg in chunk['messages']:
                    if msg.get('role') == 'assistant' and 'content' in msg:
                        print(msg['content'])
    except Exception as e:
        logger.critical(f"Blueprint execution failed with unhandled exception: {e}", exc_info=True)
        sys.exit(1)



def run_blueprint_cli(
    blueprint_cls: Type['BlueprintBase'],
    swarm_version: str,
    default_config_path: Path
):
    """
    Parses CLI arguments, instantiates, and runs a blueprint.

    Args:
        blueprint_cls (Type[BlueprintBase]): The blueprint class to run.
        swarm_version (str): The core swarm version string.
        default_config_path (Path): Default path to swarm_config.json.
    """
    # --- Argument Parsing ---
    metadata = getattr(blueprint_cls, 'metadata', {})
    parser = argparse.ArgumentParser(
        description=metadata.get("description", f"Run {blueprint_cls.__name__}"),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--config-path", type=str, default=None, help=f"Path to swarm_config.json (Default: {default_config_path})")
    parser.add_argument("--config", type=str, metavar="JSON_FILE_OR_STRING", default=None, help="JSON config overrides (file path or string). Merged last.")
    parser.add_argument("--profile", type=str, default=None, help="Configuration profile to use.")
    parser.add_argument("--debug", action="store_true", help="Enable DEBUG logging level.")
    parser.add_argument("--quiet", action="store_true", help="Suppress most logs and headers, print only final output.")
    parser.add_argument('--markdown', action=argparse.BooleanOptionalAction, default=None, help="Enable/disable markdown output (--markdown / --no-markdown). Overrides config/default.")
    parser.add_argument("--version", action="version", version=f"%(prog)s (BP: {metadata.get('name', 'N/A')} v{metadata.get('version', 'N/A')}, Core: {swarm_version})")
    parser.add_argument("instruction", nargs=argparse.REMAINDER, help="Instruction or prompt for the blueprint. All arguments after -- are treated as the prompt.")
    args = parser.parse_args()

    # Determine instruction string: if '--' is present, treat everything after as prompt
    instruction_args = args.instruction
    if instruction_args:
        # Remove leading '--' if present
        if instruction_args and instruction_args[0] == '--':
            instruction_args = instruction_args[1:]
        instruction = ' '.join(instruction_args).strip()
    else:
        instruction = ''

    if not instruction:
        parser.error("No instruction provided. Pass a prompt after -- or as positional arguments.")

    # --- Load CLI Config Overrides ---
    cli_config_overrides = {}
    if args.config:
        config_arg = args.config
        config_override_path = Path(config_arg)
        temp_logger = logging.getLogger("swarm.cli.config") # Temp logger for this part
        if config_override_path.is_file():
            temp_logger.info(f"Attempting to load CLI config overrides from file: {config_override_path}")
            try:
                with open(config_override_path, "r", encoding="utf-8") as f:
                    cli_config_overrides = json.load(f)
                temp_logger.debug(f"Loaded overrides keys: {list(cli_config_overrides.keys())}")
            except Exception as e:
                temp_logger.error(f"Failed to load --config file: {e}", exc_info=args.debug)
                sys.exit(f"Error reading config override file: {e}")
        else:
            temp_logger.info("Attempting to parse --config argument as JSON string.")
            try:
                cli_config_overrides = json.loads(config_arg)
                if not isinstance(cli_config_overrides, dict):
                    raise TypeError("--config JSON string must resolve to a dictionary.")
                temp_logger.debug(f"--config JSON string parsed successfully. Keys: {list(cli_config_overrides.keys())}")
            except Exception as e:
                temp_logger.error(f"Failed parsing --config JSON string: {e}")
                sys.exit(f"Error: Invalid --config value: {e}")

    # --- Instantiate and Run Blueprint ---
    blueprint_instance: Optional['BlueprintBase'] = None
    try:
        # Always provide a blueprint_id (use class name if not supplied by CLI args)
        blueprint_id = getattr(args, 'blueprint_id', None) or getattr(blueprint_cls, 'DEFAULT_BLUEPRINT_ID', None) or blueprint_cls.__name__
        # Instantiate the blueprint, passing necessary config/flags
        blueprint_instance = blueprint_cls(
            blueprint_id,
            config_path=args.config_path,

            # Pass necessary context if needed by __init__
            # default_config_path=default_config_path,
            # swarm_version=swarm_version
        )

        # Run the async part with shutdown handling
        asyncio.run(_run_blueprint_async_with_shutdown(blueprint_instance, instruction))

    except (ValueError, TypeError, FileNotFoundError) as config_err:
        logger.critical(f"[Initialization Error] Configuration problem: {config_err}", exc_info=args.debug)
        sys.exit(1)
    except ImportError as ie:
        # Catch potential issues if dependencies are missing
        logger.critical(f"[Import Error] Failed to import required module for {blueprint_cls.__name__}: {ie}. Please check dependencies.", exc_info=args.debug)
        sys.exit(1)
    except KeyboardInterrupt:
         logger.info("Execution interrupted by user (KeyboardInterrupt).")
         # Should be handled by signal handler now, but keep as fallback
         sys.exit(130) # Standard exit code for Ctrl+C
    except Exception as e:
        logger.critical(f"[Execution Error] An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.debug("Blueprint CLI execution finished.")
        # Any final cleanup outside the async loop (rarely needed here)
