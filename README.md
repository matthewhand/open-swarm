Open-Swarm Update - 20250328

This project is now repurposed due to OpenAI officially supporting the Swarm framework under the new name "openai-agents(-python)".

Open-swarm now utilizes the openai-agents framework for enhanced capabilities, and the MCP logic has been offloaded to the openai-agents framework.

Key focus areas of this open-swarm framework include:
- **Blueprints**: A blueprint can be converted into an OpenAI-compatible REST endpoint (analogous to `/v1/chat/completions`, but with agents) and/or into CLI utilities on the shell.
- **Config Loader**: Blueprints and configuration management form a core aspect of the project.

Installation:
-------------
Open-swarm is available via PyPI. To install, run:
```
pip install open-swarm
```

Usage:
------
In development, after cloning the repository (`github.com/matthewhand/open-swarm`), you can run a blueprint directly with:
```
uv run blueprints/mcp_demo/blueprint_mcp_demo.py
```

To run the blueprint with a specific instruction (for example, to list its tools), execute:
```
uv run blueprints/mcp_demo/blueprint_mcp_demo.py --instruction "list your tools"
```

Alternatively, you can run the blueprint as an API endpoint using the swarm-api utility:
```
swarm-api --blueprint mcp_demo
```

In production, you can use the swarm-cli utility to manage and run blueprints. For example, to add an example blueprint:
```
swarm-cli add github:matthewhand/open-swarm/blueprints/mcp_demo
```
This command saves the blueprint to:
```
~/.swarm/blueprints/mcp_demo/
```
After adding the blueprint, you can convert it into a standalone CLI utility with:
```
swarm-cli install mcp_demo
```

Building a Basic Blueprint & Config File:
------------------------------------------
You can create your own blueprint to extend open-swarm's capabilities. Here is a walkthrough:

1. **Create a Blueprint File:**
   - In the `blueprints/` directory, create a new Python file, for example `blueprints/my_blueprint.py`.
   - Define a new class that inherits from `BlueprintBase` and implement the required abstract methods, such as `metadata` and `create_agents()`. For instance:
     ```
     from swarm.extensions.blueprint.blueprint_base import BlueprintBase

     class MyBlueprint(BlueprintBase):
         @property
         def metadata(self):
             return {
                 "title": "MyBlueprint",
                 "env_vars": [],
                 "required_mcp_servers": [],
                 "max_context_tokens": 8000,
                 "max_context_messages": 50
             }

         def create_agents(self):
             # Create and return agents as a dictionary.
             return {"MyAgent": ...}  # Implement your agent creation logic here.

     if __name__ == "__main__":
         MyBlueprint.main()
     ```

2. **Create a Configuration File:**
   - Create a configuration file (e.g., `swarm_config.json`) at the root of the project. This file can include settings for LLM models and MCP servers. For example:
     ```
     {
       "llm": {
         "default": {
           "provider": "openai",
           "model": "gpt-4",
           "api_key": "your-openai-api-key",
           "base_url": null
         }
       },
       "mcpServers": {
         "mcp_llms_txt_server": {
           "command": "echo",
           "args": [],
           "env": {}
         },
         "everything_server": {
           "command": "echo",
           "args": [],
           "env": {}
         }
       }
     }
     ```

3. **Running Your Blueprint:**
   - To run your blueprint in development mode, use:
     ```
     uv run blueprints/my_blueprint.py
     ```
   - Ensure your configuration file is properly loaded by your blueprint (this might require modifications in your blueprint's initialization logic or passing a `--config` parameter).

Installation & Deployment via swarm-cli:
--------------------------------------------
After creating your blueprint and config file, you can manage it with the swarm-cli utility. For example:
- **Adding your blueprint:**
  ```
  swarm-cli add github:matthewhand/open-swarm/blueprints/my_blueprint
  ```
- **Installing as a standalone CLI utility:**
  ```
  swarm-cli install my_blueprint
  ```

Examples:
---------
**Blueprint "mcp_demo":**

The blueprint located in `blueprints/mcp_demo` demonstrates a key design principle:
- It creates a primary agent named **Sage** that leverages the MCP framework to incorporate external capabilities.
- **Sage** uses another agent, **Explorer**, as a tool to extend its functionality.

This hierarchical agent design illustrates how blueprints can compose agents that call on subagents as tools. This model serves as a prototype for creating powerful agent-driven workflows and can be deployed both as a REST endpoint and as a CLI tool.

Production Environment:
-----------------------
After installing the package via pip, you can manage blueprints with `swarm-cli` and launch them as standalone utilities or REST services.

For help with swarm-cli:
```
swarm-cli --help
```

For help with swarm-api:
```
swarm-api --help
