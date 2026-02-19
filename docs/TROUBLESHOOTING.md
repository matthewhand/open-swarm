# Open Swarm Troubleshooting Guide

Having issues with Open Swarm? Here are some common problems and solutions.

---

## 1. CLI or Blueprint Not Found
- Ensure `~/.local/bin` is in your `$PATH`.
- Try running the command directly: `~/.local/bin/codey`

## 2. API Errors or LLM Not Working
- Double-check your API key in `~/.config/swarm/.env`.
- Make sure your network connection is active.
- If using a custom endpoint, verify the URL and credentials.

## 3. Configuration Issues
- Review your config file: `~/.config/swarm/swarm_config.json`.
  - Look for typos, missing fields, or invalid JSON.
  - You can edit with any text editor (e.g., `nano`, `vim`, `code`).
- If you continue to have issues, **as a last resort** you can delete the config file:
  ```bash
  rm ~/.config/swarm/swarm_config.json
  ```
  - The system will regenerate a default config on next run, but you will need to reconfigure agents and LLMs.

## 4. Logs and Debugging
- Check logs at `~/.swarm/swarm.log` for error messages.
- Run CLI commands with increased verbosity if supported (e.g., `--verbose`).

## 5. Getting Help
- Use `swarm-cli --help` or `<blueprint> --help` for usage info.
- Review the [QUICKSTART](./QUICKSTART.md) and [DEVELOPER_GUIDE](./DEVELOPER_GUIDE.md).
- If all else fails, open an issue on the project’s GitHub or reach out to the community.

### Common CLI mismatches
- If docs mention `swarm-cli blueprints list` or `swarm-cli run`, use the current commands instead:
  - List blueprints: `swarm-cli list`
  - Install executable: `swarm-cli install <name>`
  - Launch installed executable: `swarm-cli launch <name> --message "..."`

---

## 6. Running Generated Blueprints in Restricted Environments

If you run a generated blueprint (from `swarm-cli wizard`) in a highly restricted sandbox (e.g., some CI or container sandboxes), you may see errors like:

```
PermissionError: [Errno 1] Operation not permitted (socketpair) … during asyncio event loop creation
```

What it means:
- The blueprint’s `__main__` uses `asyncio.run(...)`, which internally sets up an event loop using system primitives (e.g., socketpair). Some sandboxes prohibit these operations.

How to proceed:
- The blueprint file is valid and compiles; this is an environment restriction.
- Run the script on a normal shell or a less-restricted environment.
- Alternatively, import and run from Python where an event loop is already available and permitted, or disable the `__main__` block for CI-only checks (use `python -m py_compile` for syntax validation).

### Config and secrets location
- Config JSON: `~/.config/swarm/swarm_config.json`
- Secrets file: `~/.config/swarm/.env`
- Reference secrets in JSON using `${ENV_VAR}` (e.g., `"api_key": "${OPENAI_API_KEY}"`).

---

**Tip:** Most issues are caused by misconfigured API keys, missing dependencies, or a corrupted config file. Reviewing or resetting your config often resolves stubborn problems.
