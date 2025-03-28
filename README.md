Open-Swarm Update - 20250328

This project is now repurposed due to OpenAI officially supporting the Swarm framework under the new name "openai-agents(-python)".

Open-swarm now utilizes the openai-agents framework for enhanced capabilities. Additionally, the MCP logic has been offloaded to the openai-agents framework.

Key focus areas of this open-swarm framework include:
- Blueprints: A blueprint can be converted into an OpenAI-compatible REST endpoint (analogous to /v1/chat/completions, but with agents).
- Config Loader: Blueprints and configuration management are core to the project's functionality.

Future developments include:
- Swarm CLI: A command-line utility that accepts blueprint content or file as input.
- Swarm REST: A RESTful service that installs or references blueprints from ~/.swarm/blueprints/ (for production, blueprints are loaded from ./blueprints/ during development).

For further updates and contributions, please refer to the project’s repository.