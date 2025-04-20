# Open Swarm Developer Guide

Welcome to the Open Swarm developer documentation! This guide is your starting point for building, extending, and maintaining blueprints, agents, and the Swarm framework itself.

---

## Table of Contents
- [Project Structure](#project-structure)
- [swarm_config.json](#swarm_configjson)
- [Blueprint Splash Abstraction](#blueprint-splash-abstraction)
- [Blueprint Metadata](#blueprint-metadata)
- [CLI vs API Behavior](#cli-vs-api-behavior)
- [Best Practices](#best-practices)
- [Contributing](#contributing)

---

## Project Structure
Describe the directory layout, key modules, and where to find blueprints, agents, utilities, and documentation.

## swarm_config.json
See [SWARM_CONFIG.md](./SWARM_CONFIG.md) for full details on the global configuration file.

## Blueprint Splash Abstraction
See [BLUEPRINT_SPLASH.md](./BLUEPRINT_SPLASH.md) for how to implement and display blueprint splash screens in CLI mode.

## Blueprint Metadata
- Every blueprint must define a `metadata` dictionary or property with at least `title` and `description`.
- This metadata is the canonical source of truth for UI, docs, and splash content.

## CLI vs API Behavior
- CLI entrypoints may display a splash (see above); API endpoints must never emit splash or ANSI.
- Always use metadata for programmatic or UI consumption.

## Best Practices
- Validate configs before running agents.
- Never hardcode secrets; use environment variables and document them in the config docs.
- Keep blueprint metadata up to date and descriptive.
- Reference documentation files in code and PRs to ensure consistency.

## Contributing
- Please read the [CONTRIBUTING.md](./CONTRIBUTING.md) file (if present) before submitting PRs.
- Follow code style and documentation conventions.

---

**For more details, see the referenced markdown files in the `docs/` directory.**
