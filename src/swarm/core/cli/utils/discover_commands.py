import os
import importlib.util
import inspect

def discover_commands(commands_dir):
    commands = {}
    for filename in os.listdir(commands_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]
            module_path = os.path.join(commands_dir, filename)
            spec = importlib.util.spec_from_file_location(f'swarm.core.cli.commands.{module_name}', module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # Look for an 'execute' function
            if hasattr(module, 'execute'):
                desc = inspect.getdoc(module.execute) or f"Run {module_name} command."
                commands[module_name] = {"execute": module.execute, "description": desc}
    return commands
