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

---

**Tip:** Most issues are caused by misconfigured API keys, missing dependencies, or a corrupted config file. Reviewing or resetting your config often resolves stubborn problems.
