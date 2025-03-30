import argparse
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Type

# Import BlueprintBase type hint carefully
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .blueprint_base import BlueprintBase

logger = logging.getLogger("swarm.cli")

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


    # Wrap the main execution in a task to allow cancellation
    main_task = loop.create_task(blueprint._run_non_interactive(instruction), name=f"BlueprintRun_{blueprint.__class__.__name__}")

    # Wait for either the main task or the stop event
    done, pending = await asyncio.wait(
        [main_task, loop.create_task(stop_event.wait(), name="ShutdownWatcher")],
        return_when=asyncio.FIRST_COMPLETED
    )

    # Cleanup signal handlers after wait returns
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.remove_signal_handler(sig)
        except NotImplementedError:
            try:
                signal.signal(sig, signal.SIG_DFL) # Restore default handler
            except Exception:
                pass # Ignore errors during cleanup

    # Check if the stop event was triggered
    if stop_event.is_set():
        logger.warning("Graceful shutdown initiated. Cancelling main task...")
        if not main_task.done():
            main_task.cancel()
            try:
                # Wait briefly for cancellation to propagate and cleanup within the task
                await asyncio.wait_for(main_task, timeout=10.0) # Increased timeout slightly
            except asyncio.CancelledError:
                logger.info("Main task successfully cancelled.")
            except asyncio.TimeoutError:
                logger.error("Main task did not cancel within timeout. Potential resource leak.")
            except Exception as e:
                logger.error(f"Error during task cancellation waiting: {e}", exc_info=True)
        else:
            logger.info("Main task already completed before cancellation request.")
        # The _run_non_interactive's AsyncExitStack should handle MCP cleanup
    else:
        # If the main task finished first, check for exceptions
        if main_task in done:
            try:
                main_task.result() # Raise exception if one occurred in the task
                logger.debug("Main task completed successfully.")
            except asyncio.CancelledError:
                 logger.info("Main task was cancelled externally (unexpected).")
            except Exception as e:
                # Error should have been logged within _run_non_interactive
                # We exit here because the main operation failed
                logger.critical(f"Blueprint execution failed with unhandled exception: {e}", exc_info=True)
                sys.exit(1) # Exit with error status if task failed


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
    parser.add_argument("--instruction", type=str, required=True, help="Initial instruction for the blueprint.")
    parser.add_argument("--config-path", type=str, default=None, help=f"Path to swarm_config.json (Default: {default_config_path})")
    parser.add_argument("--config", type=str, metavar="JSON_FILE_OR_STRING", default=None, help="JSON config overrides (file path or string). Merged last.")
    parser.add_argument("--profile", type=str, default=None, help="Configuration profile to use.")
    parser.add_argument("--debug", action="store_true", help="Enable DEBUG logging level.")
    parser.add_argument("--quiet", action="store_true", help="Suppress most logs and headers, print only final output.")
    parser.add_argument('--markdown', action=argparse.BooleanOptionalAction, default=None, help="Enable/disable markdown output (--markdown / --no-markdown). Overrides config/default.")
    parser.add_argument("--version", action="version", version=f"%(prog)s (BP: {metadata.get('name', 'N/A')} v{metadata.get('version', 'N/A')}, Core: {swarm_version})")
    args = parser.parse_args()

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
        # Instantiate the blueprint, passing necessary config/flags
        blueprint_instance = blueprint_cls(
            config_path_override=args.config_path,
            profile_override=args.profile,
            config_overrides=cli_config_overrides,
            debug=args.debug,
            quiet=args.quiet,
            force_markdown=args.markdown,
            # Pass necessary context if needed by __init__
            # default_config_path=default_config_path,
            # swarm_version=swarm_version
        )

        # Run the async part with shutdown handling
        asyncio.run(_run_blueprint_async_with_shutdown(blueprint_instance, args.instruction))

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

