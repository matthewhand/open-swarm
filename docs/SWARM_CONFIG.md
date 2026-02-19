# swarm_config.json Documentation

## Purpose
`swarm_config.json` is the primary configuration file for the Open Swarm framework. It defines global settings, agent/blueprint registration, model defaults, environment variables, and other core options that control Swarm’s behavior.

## Typical Fields
- **agents**: List of agent/blueprint definitions, each with a unique ID, type, and configuration.
- **models**: Default LLM or model configuration (e.g., model name, provider, API key reference).
- **env**: Environment variables to be set for subprocesses or agent runs.
- **logging**: Logging level, output file, and format options.
- **blueprints**: (optional) Blueprint-specific overrides or registration.
- **other**: Any additional fields required for custom extensions or plugins.

## Example
```json
{
  "agents": [
    {"id": "jeeves", "type": "butler", "config": {"home_assistant_url": "http://..."}},
    {"id": "codey", "type": "coder", "config": {"model": "gpt-4"}}
  ],
  "models": {
    "default": "gpt-4",
    "providers": ["openai", "local"]
  },
  "env": {
    "OPENAI_API_KEY": "..."
  },
  "logging": {
    "level": "info",
    "file": "swarm.log"
  }
}
```

## Best Practices
- Always validate your config with `swarm-cli` before running agents.
- Use environment variable references for secrets (never hardcode API keys).
- Document custom fields with comments in a separate `.md` file, as JSON does not support comments.

---

**Reference this file for all questions about configuring Open Swarm via `swarm_config.json`.**
