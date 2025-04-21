import os
import json
import click
from pathlib import Path
import glob
import importlib.util
import inspect

CONFIG_DEFAULT_PATH = os.environ.get("SWARM_CONFIG_PATH", "swarm_config.json")

# --- Utility functions ---
def load_config(config_path=None):
    path = Path(config_path or CONFIG_DEFAULT_PATH)
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)

def save_config(data, config_path=None):
    path = Path(config_path or CONFIG_DEFAULT_PATH)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

# --- CLI ---
@click.group()
def cli():
    """Swarm CLI for config management."""
    pass

@cli.group()
def config():
    """Manage Swarm configuration."""
    pass

@config.group()
def llm():
    """Manage LLM configs."""
    pass

@llm.command()
@click.option('--name', required=True)
@click.option('--provider', required=True)
@click.option('--model', required=True)
@click.option('--api-key', required=False)
@click.option('--base-url', required=False)
@click.option('--config-path', required=False)
def create(name, provider, model, api_key, base_url, config_path):
    data = load_config(config_path)
    data.setdefault('llms', {})
    if name in data['llms']:
        click.echo(f"LLM config '{name}' already exists.", err=True)
        exit(1)
    data['llms'][name] = {
        'provider': provider,
        'model': model,
        'api_key': api_key,
        'base_url': base_url
    }
    save_config(data, config_path)
    click.echo(f"LLM config '{name}' created.")

@llm.command()
@click.option('--name', required=True)
@click.option('--config-path', required=False)
def read(name, config_path):
    data = load_config(config_path)
    llm = data.get('llms', {}).get(name)
    if not llm:
        click.echo(f"LLM config '{name}' not found.", err=True)
        exit(1)
    click.echo(json.dumps(llm, indent=2))

@llm.command()
@click.option('--name', required=True)
@click.option('--model', required=False)
@click.option('--provider', required=False)
@click.option('--api-key', required=False)
@click.option('--base-url', required=False)
@click.option('--config-path', required=False)
def update(name, model, provider, api_key, base_url, config_path):
    data = load_config(config_path)
    llms = data.get('llms', {})
    if name not in llms:
        click.echo(f"LLM config '{name}' not found.", err=True)
        exit(1)
    if model:
        llms[name]['model'] = model
    if provider:
        llms[name]['provider'] = provider
    if api_key:
        llms[name]['api_key'] = api_key
    if base_url:
        llms[name]['base_url'] = base_url
    save_config(data, config_path)
    click.echo(f"LLM config '{name}' updated.")

@llm.command()
@click.option('--name', required=True)
@click.option('--config-path', required=False)
def delete(name, config_path):
    data = load_config(config_path)
    if name not in data.get('llms', {}):
        click.echo(f"LLM config '{name}' not found.", err=True)
        exit(1)
    del data['llms'][name]
    save_config(data, config_path)
    click.echo(f"LLM config '{name}' deleted.")

@llm.command()
@click.option('--config-path', required=False)
def list(config_path):
    data = load_config(config_path)
    llms = data.get('llms', {})
    for name, llm in llms.items():
        click.echo(f"{name}: {llm['provider']} {llm['model']}")

# --- Blueprint Metadata Loader (from class property) ---
def load_blueprint_metadata():
    blueprint_modules = glob.glob("src/swarm/blueprints/*/blueprint_*.py")
    blueprints = []
    for mod_path in blueprint_modules:
        module_name = mod_path.replace("/", ".").rstrip(".py")
        try:
            spec = importlib.util.spec_from_file_location(module_name, mod_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            # Find the blueprint class (first class with a 'metadata' property)
            for name, obj in inspect.getmembers(mod, inspect.isclass):
                if hasattr(obj, "metadata") and isinstance(getattr(obj, "metadata"), dict):
                    meta = getattr(obj, "metadata").copy()
                    # Docstring fallback for description
                    if not meta.get("description"):
                        doc = inspect.getdoc(obj)
                        if doc:
                            meta["description"] = doc.split("\n")[0]  # Use first line of docstring
                    blueprints.append(meta)
        except Exception as e:
            continue
    return blueprints

@click.group()
def blueprint():
    """Discover and get info about available blueprints."""
    pass

@blueprint.command()
def list():
    """List available blueprints with emoji and description."""
    blueprints = load_blueprint_metadata()
    click.echo("\nAvailable Blueprints:")
    for bp in blueprints:
        click.echo(f"  {bp.get('emoji','')}  {bp.get('name',''):<20}  {bp.get('description','')}")
    click.echo("\nRun 'swarm-cli blueprint info <name>' for details and examples.")

@blueprint.command()
@click.argument('name')
def info(name):
    """Show onboarding info, emoji, and example commands for a blueprint."""
    blueprints = load_blueprint_metadata()
    bp = next((b for b in blueprints if b.get('name') == name), None)
    if not bp:
        click.echo(f"Blueprint '{name}' not found.", err=True)
        return
    click.echo(f"\n{bp.get('emoji','')}  \033[1m{name}\033[0m — {bp.get('description','')}")
    click.echo("\nUnified Search & Analysis UX:")
    click.echo(f"  • {bp.get('branding','')}")
    click.echo(f"  • Try these commands: {', '.join(bp.get('commands', []))}")
    click.echo("\nExample Commands:")
    for ex in bp.get('examples', []):
        click.echo(f"  {ex}")
    click.echo("\nSee README for more onboarding tips and a full quickstart table.")

@blueprint.command()
def lint():
    """Validate blueprint metadata for all blueprints."""
    blueprints = load_blueprint_metadata()
    required_fields = ["name", "emoji", "description", "examples", "commands", "branding"]
    failed = False
    for bp in blueprints:
        missing = [f for f in required_fields if not bp.get(f)]
        if missing:
            click.echo(f"❌ {bp.get('name','<unknown>')}: Missing fields: {', '.join(missing)}", err=True)
            failed = True
        if not bp.get("description"):
            click.echo(f"⚠️  {bp.get('name','<unknown>')}: No description. Consider adding a class docstring.", err=True)
    if not blueprints:
        click.echo("❌ No blueprints found!", err=True)
        failed = True
    if not failed:
        click.echo("✅ All blueprints have valid metadata.")
    else:
        exit(1)

cli.add_command(blueprint)

if __name__ == "__main__":
    cli()
