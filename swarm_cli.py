import os
import json
import click
from pathlib import Path

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

if __name__ == "__main__":
    cli()
