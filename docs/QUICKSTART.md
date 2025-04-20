# Open Swarm Quickstart

This guide will help you get started with Open Swarm, install and configure blueprints (like Codey), and run your first LLM-powered agent.

---

## 1. Install Open Swarm

Install the Open Swarm framework and CLI globally:
```bash
pip install --user open-swarm
```
- This provides the `swarm-cli` tool and core libraries.
- Make sure `~/.local/bin` is in your `$PATH` so CLI tools are discoverable.

---

## 2. Install a Blueprint (e.g., Codey)

Blueprints are modular agents or tools. To install Codey (a coding assistant):
```bash
swarm-cli install codey
```
- This downloads and registers the Codey blueprint.
- The `codey` command will be installed to your local bin directory.

To list available blueprints:
```bash
swarm-cli blueprints list
```

---

## 3. Configure Your LLM Provider

Before using LLM-powered agents, you must provide credentials.

### a. Add an OpenAI API Key (simplest case)
```bash
swarm-cli llm add --provider openai --api-key sk-... 
```
- This saves your API key to `~/.config/swarm/.env` as `OPENAI_API_KEY`.

### b. Use a Custom Endpoint or Model
```bash
swarm-cli llm add --provider openai --api-key sk-... --base-url https://api.your-endpoint.com/v1 --model gpt-4
```
- Supports local models and other providers (see `swarm-cli llm add --help`).

### c. Check or Edit LLM Config
- View config: `swarm-cli llm list`
- Edit config manually: `nano ~/.config/swarm/.env`

---

## 4. Run a Blueprint (e.g., Codey)

To start Codey interactively:
```bash
codey
```
- If you see "command not found", try:
  - `~/.local/bin/codey`
  - Or add `~/.local/bin` to your `$PATH`.

To run a one-off instruction (non-interactive):
```bash
codey --message "Write a Python function to add two numbers"
```

---

## 5. Managing Blueprints

- **List installed blueprints:**
  ```bash
  swarm-cli blueprints list
  ```
- **Update a blueprint:**
  ```bash
  swarm-cli blueprints update codey
  ```
- **Remove a blueprint:**
  ```bash
  swarm-cli blueprints remove codey
  ```

---

## 6. Advanced: Configure swarm_config.json

- The main config file is at `~/.swarm/swarm_config.json`.
- Edit this to register agents, set defaults, or customize advanced options.
- See [docs/SWARM_CONFIG.md](./SWARM_CONFIG.md) for details.

---

## 7. Troubleshooting

- **Blueprint/command not found:** Ensure `~/.local/bin` is in your `$PATH`.
- **API errors:** Check your API key and network connectivity.
- **Config issues:** Validate your config with `swarm-cli config validate` (if available).
- **Logs:** Check `~/.swarm/swarm.log` or run with increased verbosity if supported.

---

## 8. Next Steps & Resources

- Run `swarm-cli --help` and `codey --help` for usage info.
- Explore more blueprints: `swarm-cli blueprints list`
- Read the [Developer Guide](./DEVELOPER_GUIDE.md) for advanced usage, customization, and contribution tips.
- See [docs/SWARM_CONFIG.md](./SWARM_CONFIG.md) and [docs/BLUEPRINT_SPLASH.md](./BLUEPRINT_SPLASH.md) for in-depth config and blueprint info.

---

**Happy hacking with Open Swarm!**
