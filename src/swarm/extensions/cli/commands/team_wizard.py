"""
Interactive wizard to generate a new Swarm team blueprint.

Flow:
- Collect basics (name, description, abbreviation, agents) via args or prompts
- Optionally ask an LLM for a constrained JSON spec (offline-friendly fallback)
- Render a Python blueprint file into the user blueprints dir (or --output-dir)
- Verify by compiling with py_compile
- Optionally create a CLI shortcut in the user bin dir
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
import py_compile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from swarm.core import paths

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    jsonschema = None


# -----------------------
# Data model and helpers
# -----------------------


def _slugify(name: str) -> str:
    name = name.strip().lower()
    # Replace non-alphanumeric with underscores
    name = re.sub(r"[^a-z0-9]+", "_", name)
    # Collapse repeated underscores
    name = re.sub(r"_+", "_", name)
    return name.strip("_") or "team"


def _pascal_case(name: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", name)
    return "".join(p.capitalize() for p in parts if p)


@dataclass
class TeamAgent:
    name: str
    role: str
    tools: list[str] = field(default_factory=list)


@dataclass
class TeamSpec:
    name: str
    description: str
    abbreviation: str
    agents: list[TeamAgent]

    @property
    def package_name(self) -> str:
        return _slugify(self.name)

    @property
    def class_name(self) -> str:
        return f"{_pascal_case(self.name)}Blueprint"


def _default_tools_for_role(role: str) -> list[str]:
    # Very light heuristic; real tool attachment happens in blueprint code
    keywords = role.lower()
    tools = []
    if any(k in keywords for k in ["file", "code", "engineer", "dev", "refactor"]):
        tools += ["read_file", "write_file", "list_files", "execute_shell_command"]
    if any(k in keywords for k in ["shell", "ops", "deploy", "system", "devops", "sre", "admin", "infra", "k8s", "kubernetes", "docker", "aws", "cloud"]):
        tools += ["execute_shell_command"]
    if any(k in keywords for k in ["research", "analy", "investigat", "fact", "summary", "summariz"]):
        tools += ["read_file", "list_files"]
    if any(k in keywords for k in ["write", "doc", "report", "scribe", "draft"]):
        tools += ["write_file"]
    return sorted(set(tools))


# Common presets for quick starts
PRESETS: dict[str, dict[str, Any]] = {
    "research": {
        "description": "A small research squad with a coordinator and a researcher.",
        "agents": [
            {"name": "Coordinator", "role": "Orchestrates research and summarizes results"},
            {"name": "Researcher", "role": "Fact-finding, analysis, and synthesis"},
        ],
    },
    "devops": {
        "description": "DevOps duo for ops tasks and scripting.",
        "agents": [
            {"name": "Coordinator", "role": "Plans, reviews, and approves ops tasks"},
            {"name": "Operator", "role": "Shell tasks, deployment, and infrastructure checks"},
        ],
    },
    "content": {
        "description": "Content creation and editing pair.",
        "agents": [
            {"name": "Editor", "role": "Outlines, reviews, and polishes"},
            {"name": "Writer", "role": "Drafts and revises content"},
        ],
    },
    "code": {
        "description": "Coding assistant team for analysis and implementation.",
        "agents": [
            {"name": "LeadDev", "role": "Coordinates coding tasks and reviews"},
            {"name": "Engineer", "role": "Implements and refactors code"},
        ],
    },
}


def _collect_interactive(args: argparse.Namespace) -> TeamSpec:
    print("\n🛠️  Swarm Team Wizard — let’s scaffold your team\n")

    name = args.name or input("Team name (e.g., Product Research Crew): ").strip()
    while not name:
        name = input("Please enter a team name: ").strip()

    description = args.description or input("Short description (one line): ").strip()
    if not description:
        description = "Custom team blueprint created with the Swarm wizard."

    abbreviation = args.abbreviation or input(
        f"Executable name (default: {_slugify(name)}): "
    ).strip()
    if not abbreviation:
        abbreviation = _slugify(name)

    if args.agents:
        raw_agents = args.agents
    else:
        print("\nDefine agents (comma-separated). Example: 'Coordinator:orchestrates, Researcher:finds facts'\n")
        raw_agents = input("Agents (name:role[,...]): ").strip()
        if not raw_agents:
            raw_agents = "Coordinator:orchestrates, Specialist:executes"

    agents: list[TeamAgent] = []
    for chunk in raw_agents.split(","):
        if not chunk.strip():
            continue
        if ":" in chunk:
            nm, rl = [p.strip() for p in chunk.split(":", 1)]
        else:
            nm, rl = chunk.strip(), ""
        tools = _default_tools_for_role(rl or nm)
        agents.append(TeamAgent(name=nm or "Agent", role=rl or nm, tools=tools))

    return TeamSpec(
        name=name,
        description=description,
        abbreviation=_slugify(abbreviation),
        agents=agents or [TeamAgent(name="Coordinator", role="Orchestrates")],
    )


def _collect_non_interactive(args: argparse.Namespace) -> TeamSpec:
    if not args.name:
        raise SystemExit("Error: --name is required in --non-interactive mode.")
    description = args.description or "Custom team blueprint created with the Swarm wizard."
    abbreviation = args.abbreviation or _slugify(args.name)
    agents: list[TeamAgent] = []
    raw_agents = args.agents or "Coordinator:orchestrates, Specialist:executes"
    for chunk in raw_agents.split(","):
        if not chunk.strip():
            continue
        if ":" in chunk:
            nm, rl = [p.strip() for p in chunk.split(":", 1)]
        else:
            nm, rl = chunk.strip(), ""
        tools = _default_tools_for_role(rl or nm)
        agents.append(TeamAgent(name=nm or "Agent", role=rl or nm, tools=tools))
    return TeamSpec(
        name=args.name,
        description=description,
        abbreviation=_slugify(abbreviation),
        agents=agents or [TeamAgent(name="Coordinator", role="Orchestrates")],
    )


# -----------------------
# LLM constrained spec (optional)
# -----------------------


LLM_SPEC_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["name", "description", "abbreviation", "agents"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string", "minLength": 1},
        "abbreviation": {"type": "string", "minLength": 1},
        "agents": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["name", "role"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "role": {"type": "string", "minLength": 1},
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


def _try_llm_spec(seed: TeamSpec, model: str | None) -> TeamSpec | None:
    """
    Attempt to call an LLM to refine the team spec, constrained to the JSON schema above.
    If any error occurs or environment is not configured, return None to fall back gracefully.
    """
    # Only run if OPENAI/LiteLLM is configured
    has_key = bool(os.environ.get("LITELLM_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    if not has_key:
        return None

    # Prefer OpenAI client if available in the environment; otherwise, skip
    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return None

    try:
        client = OpenAI(
            base_url=os.environ.get("LITELLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL"),
            api_key=os.environ.get("LITELLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        )
        prompt = {
            "role": "system",
            "content": textwrap.dedent(
                f"""
                You are a helpful assistant that outputs ONLY JSON matching the provided schema.
                Schema: {json.dumps(LLM_SPEC_JSON_SCHEMA)}
                Seed (user intent): {json.dumps(seed, default=lambda o: o.__dict__)}
                Output: a single JSON object conforming strictly to the schema.
                """
            ).strip(),
        }
        resp = client.chat.completions.create(
            model=model or os.environ.get("SWARM_WIZARD_MODEL", "gpt-4o-mini"),
            messages=[prompt, {"role": "user", "content": "Generate team spec JSON now."}],
            temperature=0.2,
        )
        content = resp.choices[0].message.content if resp.choices else None
        if not content:
            return None
        # Some models may wrap JSON in fences; strip them
        content = content.strip()
        content = re.sub(r"^```(json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()
        data = json.loads(content)

        # Minimal validation against expected keys
        if not isinstance(data, dict):
            return None
        for key in ("name", "description", "abbreviation", "agents"):
            if key not in data:
                return None

        agents = [
            TeamAgent(
                name=a.get("name", "Agent"),
                role=a.get("role", ""),
                tools=[t for t in a.get("tools", []) if isinstance(t, str)],
            )
            for a in data.get("agents", [])
            if isinstance(a, dict)
        ]
        if not agents:
            return None

        return TeamSpec(
            name=str(data["name"]).strip() or seed.name,
            description=str(data["description"]).strip() or seed.description,
            abbreviation=_slugify(str(data["abbreviation"]) or seed.abbreviation),
            agents=agents,
        )
    except Exception:
        # Do not fail the wizard; just fall back
        return None


def _try_llm_from_description(description: str, model: str | None) -> TeamSpec | None:
    """Generate a fresh TeamSpec from a free-text description via LLM (if configured)."""
    seed = TeamSpec(
        name="Custom Team",
        description=description or "Custom team",
        abbreviation=_slugify("custom_team"),
        agents=[TeamAgent(name="Coordinator", role="Orchestrates")],
    )
    return _try_llm_spec(seed, model)


def _validate_against_schema(data: dict[str, Any], schema: dict[str, Any]) -> bool:
    if jsonschema is None:
        return True
    try:
        jsonschema.validate(instance=data, schema=schema)
        return True
    except Exception:
        return False


# -----------------------
# Rendering and writing
# -----------------------


def _render_blueprint_code(spec: TeamSpec, template: str = "simple") -> str:
    """Create a minimal yet functional blueprint Python file."""
    agents_table = "\n".join(
        f"        - {a.name}: {a.role} (tools: {', '.join(a.tools) if a.tools else 'none'})" for a in spec.agents
    )
    # Provide simple tool wiring based on the base EchoCraft example
    tools_binding = textwrap.dedent(
        """
        # Bind generic file/shell tools if requested by agents
        class _Tool:
            def __init__(self, func, name):
                self.func = func
                self.name = name

        def read_file(path: str) -> str:
            try:
                with open(path) as f:
                    return f.read()
            except Exception as e:
                return "ERROR: " + str(e)
        def write_file(path: str, content: str) -> str:
            try:
                with open(path, 'w') as f:
                    f.write(content)
                return "OK: file written"
            except Exception as e:
                return "ERROR: " + str(e)
        def list_files(directory: str = '.') -> str:
            import os
            try:
                return '\\n'.join(os.listdir(directory))
            except Exception as e:
                return "ERROR: " + str(e)
        def execute_shell_command(command: str) -> str:
            import os, subprocess
            try:
                timeout = int(os.getenv("SWARM_COMMAND_TIMEOUT", "60"))
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
                output = "Exit Code: " + str(result.returncode) + "\\n"
                if result.stdout:
                    output += "STDOUT:\\n" + result.stdout + "\\n"
                if result.stderr:
                    output += "STDERR:\\n" + result.stderr + "\\n"
                return output.strip()
            except subprocess.TimeoutExpired:
                return "Error: Command timed out after " + os.getenv('SWARM_COMMAND_TIMEOUT', '60') + " seconds."
            except Exception as e:
                return "Error executing command: " + str(e)
        read_file_tool = _Tool(read_file, 'read_file')
        write_file_tool = _Tool(write_file, 'write_file')
        list_files_tool = _Tool(list_files, 'list_files')
        execute_shell_command_tool = _Tool(execute_shell_command, 'execute_shell_command')
        """
    ).strip("\n")

    agent_tool_select = []
    for a in spec.agents:
        tools_list = []
        if "read_file" in a.tools:
            tools_list.append("read_file_tool")
        if "write_file" in a.tools:
            tools_list.append("write_file_tool")
        if "list_files" in a.tools:
            tools_list.append("list_files_tool")
        if "execute_shell_command" in a.tools:
            tools_list.append("execute_shell_command_tool")
        joined = ", ".join(tools_list)
        agent_tool_select.append(f"            '{a.name}': [{joined}] if [{joined}] else [],")

    agent_tools_map_src = (
        "\n".join(agent_tool_select) if agent_tool_select else "            'Coordinator': [],"
    )

    team_name_json = json.dumps(spec.name)
    lines: list[str] = []
    lines.append("# Auto-generated by Swarm Team Wizard")
    lines.append("import json")
    lines.append("import time")
    lines.append("import uuid")
    lines.append("from typing import Any")
    lines.append("")
    lines.append("from swarm.core.blueprint_base import BlueprintBase")
    lines.append("")
    lines.append(tools_binding)
    lines.append("")
    lines.append(f"class {spec.class_name}(BlueprintBase):")
    lines.append('    """')
    for ln in (spec.description or "").splitlines() or [""]:
        lines.append(f"    {ln}")
    lines.append("")
    lines.append("    Agents:")
    for ln in agents_table.splitlines():
        lines.append(f"{ln}")
    lines.append('    """')
    lines.append("")
    lines.append("    async def _original_run(self, messages: list[dict[str, Any]], **kwargs: Any):")
    lines.append("        # Simple coordinator: echo last user message prefixed by team name")
    lines.append("        last_user = next((m.get('content', '') for m in reversed(messages) if m.get('role') == 'user'), '')")
    lines.append(f"        echo = \"[\" + {team_name_json} + \"] \" + last_user")
    lines.append("        completion_id = \"chatcmpl-\" + str(uuid.uuid4())")
    lines.append("        created_ts = int(time.time())")
    lines.append("        yield {")
    lines.append("            \"id\": completion_id,")
    lines.append("            \"object\": \"chat.completion\",")
    lines.append("            \"created\": created_ts,")
    lines.append("            \"model\": self.llm_profile_name or \"default\",")
    lines.append("            \"choices\": [{")
    lines.append("                \"index\": 0,")
    lines.append("                \"message\": {\"role\": \"assistant\", \"content\": echo},")
    lines.append("                \"finish_reason\": \"stop\",")
    lines.append("                \"logprobs\": None")
    lines.append("            }],")
    lines.append("        }")
    lines.append("")
    lines.append("    async def run(self, messages: list[dict[str, Any]], **kwargs: Any):")
    lines.append("        async for result in self._original_run(messages, **kwargs):")
    lines.append("            yield result")
    lines.append("")
    lines.append("    def create_starting_agent(self, mcp_servers):")
    if template == "multiagent" and len(spec.agents) > 1:
        # Hint at multiple agents and how tools could be distributed
        lines.append("        # Example multi-agent setup; tools per agent defined below")
    else:
        lines.append("        # Example: attach per-agent tools based on the spec")
    lines.append("        tools_map = {")
    lines.append(agent_tools_map_src)
    lines.append("        }")
    lines.append("        # Use the coordinator name if present, else fall back to first")
    lines.append(f"        start_name = '{spec.agents[0].name}'")
    lines.append("        return self.make_agent(")
    lines.append("            name=start_name,")
    lines.append(f"            instructions=\"You are the coordinator for the team \" + {team_name_json} + \".\",")
    lines.append("            tools=tools_map.get(start_name, []),")
    lines.append("            mcp_servers=mcp_servers,")
    lines.append("        )")
    lines.append("")
    lines.append("")
    lines.append("if __name__ == \"__main__\":")
    lines.append("    import asyncio")
    lines.append(f"    bp = {spec.class_name}(blueprint_id='{spec.package_name}')")
    lines.append("    async def _run():")
    lines.append("        msgs = [{\"role\": \"user\", \"content\": \"Say hello.\"}]")
    lines.append("        last = None")
    lines.append("        async for chunk in bp.run(msgs):")
    lines.append("            try:")
    lines.append("                if isinstance(chunk, dict) and chunk.get('choices'):")
    lines.append("                    ch = chunk['choices'][0]")
    lines.append("                    msg = ch.get('message') or {}")
    lines.append("                    if isinstance(msg, dict) and 'content' in msg:")
    lines.append("                        last = msg['content']")
    lines.append("            except Exception:")
    lines.append("                pass")
    lines.append("        if last is not None:")
    lines.append("            print(last)")
    lines.append("    asyncio.run(_run())")
    return "\n".join(lines)


def _write_blueprint_file(spec: TeamSpec, output_dir: Path, overwrite: bool, template: str = "simple") -> Path:
    bp_dir = output_dir / spec.package_name
    bp_path = bp_dir / f"blueprint_{spec.package_name}.py"
    if bp_path.exists() and not overwrite:
        raise FileExistsError(f"Blueprint already exists: {bp_path}")
    bp_dir.mkdir(parents=True, exist_ok=True)
    code = _render_blueprint_code(spec, template=template)
    bp_path.write_text(code, encoding="utf-8")
    return bp_path


def _verify_python_file(path: Path) -> None:
    py_compile.compile(str(path), doraise=True)


def _install_shortcut(spec: TeamSpec, blueprint_path: Path, bin_dir: Path, overwrite: bool) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    name = spec.abbreviation or spec.package_name
    shortcut_path = bin_dir / name
    if shortcut_path.exists() and not overwrite:
        raise FileExistsError(f"Shortcut already exists: {shortcut_path}")
    script = f"#!/usr/bin/env bash\nexec python3 '{blueprint_path}' \"$@\"\n"
    shortcut_path.write_text(script, encoding="utf-8")
    os.chmod(shortcut_path, 0o755)
    return shortcut_path


def _verify_importable(bp_path: Path, class_name: str) -> bool:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(bp_path.stem, str(bp_path))
        if not spec or not spec.loader:
            return False
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = getattr(module, class_name, None)
        if cls is None:
            return False
        # Avoid side effects: instantiate with minimal args
        _ = cls(blueprint_id=bp_path.parent.name)
        return True
    except Exception:
        return False


def _scaffold_tests(tests_root: Path, spec: TeamSpec, bp_path: Path) -> Path:
    tests_root.mkdir(parents=True, exist_ok=True)
    test_file = tests_root / f"test_{spec.package_name}_smoke.py"
    content = f"""
import py_compile
from pathlib import Path

def test_blueprint_compiles():
    bp = Path({json.dumps(str(bp_path))})
    py_compile.compile(str(bp), doraise=True)
""".lstrip()
    test_file.write_text(content, encoding="utf-8")
    return test_file


# -----------------------
# CLI glue
# -----------------------


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--name", "-n", help="Team name (e.g., Product Research Crew)")
    parser.add_argument("--description", "-d", help="Short description")
    parser.add_argument("--abbreviation", "-a", help="Executable name/shortcut (default: slugified name)")
    parser.add_argument(
        "--agents",
        "-r",
        help="Comma-separated agents as 'Name:role[,...]'. Default: 'Coordinator:orchestrates, Specialist:executes'",
    )
    parser.add_argument("--preset", choices=sorted(PRESETS.keys()), help="Start from a preset team (research, devops, content, code)")
    parser.add_argument("--template", choices=["simple", "multiagent"], default="simple", help="Generated code template complexity")
    parser.add_argument("--from-description", dest="from_description", help="Free-text description to generate a team via LLM (if configured)")
    parser.add_argument("--model", help="LLM model for constrained JSON (optional)")
    parser.add_argument("--use-llm", dest="use_llm", action="store_true", help="Use LLM to refine spec")
    parser.add_argument("--no-llm", dest="use_llm", action="store_false", help="Do not call LLM")
    parser.set_defaults(use_llm=False)
    parser.add_argument("--non-interactive", action="store_true", help="Do not prompt; require flags")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files/shortcuts if present")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing files")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to place blueprint (default: user blueprints dir)",
    )
    parser.add_argument(
        "--bin-dir",
        type=Path,
        help="Directory to place CLI shortcut (default: user bin dir)",
    )
    parser.add_argument(
        "--no-shortcut",
        dest="no_shortcut",
        action="store_true",
        help="Do not create a CLI shortcut",
    )
    parser.add_argument("--print-spec", action="store_true", help="Print the final spec as JSON")
    parser.add_argument("--verify-import", action="store_true", help="After writing, import and instantiate the class to verify importability")
    parser.add_argument("--scaffold-tests", action="store_true", help="Create a minimal pytest smoke test for the generated blueprint")


def _prompt_yes_no(question: str, default: bool) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        ans = input(f"{question}{suffix} ").strip().lower()
        if ans == "" and default is not None:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'.")


def execute(args: argparse.Namespace) -> None:
    # Collect spec
    # 1) From description via LLM (if provided and configured)
    spec = None
    if args.from_description:
        spec = _try_llm_from_description(args.from_description, args.model)
    # 2) Otherwise, normal collection route
    if spec is None:
        spec = (
            _collect_non_interactive(args) if args.non_interactive else _collect_interactive(args)
        )

    # Apply preset overlay if requested
    if args.preset:
        preset = PRESETS.get(args.preset)
        if preset:
            # If description was not explicitly provided, use preset description
            if not args.description and preset.get("description"):
                spec.description = preset["description"]
            # If agents were not explicitly provided, use preset agents
            if not args.agents and preset.get("agents"):
                spec.agents = [
                    TeamAgent(name=a.get("name", "Agent"), role=a.get("role", ""), tools=_default_tools_for_role(a.get("role", "")))
                    for a in preset["agents"]
                ]

    # Optionally refine via LLM with constrained JSON
    use_llm_flag = bool(args.use_llm)
    if not args.non_interactive and not use_llm_flag:
        # Offer refinement if keys are present
        if os.environ.get("LITELLM_API_KEY") or os.environ.get("OPENAI_API_KEY"):
            use_llm_flag = _prompt_yes_no("Refine team spec with LLM?", default=False)
    if use_llm_flag:
        refined = _try_llm_spec(spec, args.model)
        if refined:
            spec = refined

    # Optional: print final spec
    if args.print_spec:
        as_dict = {
            "name": spec.name,
            "description": spec.description,
            "abbreviation": spec.abbreviation,
            "agents": [{"name": a.name, "role": a.role, "tools": a.tools} for a in spec.agents],
        }
        print(json.dumps(as_dict, indent=2))

    # Resolve dirs with env-aware fallbacks
    try:
        paths.ensure_swarm_directories_exist()
    except Exception:
        pass
    output_dir = args.output_dir or paths.get_user_blueprints_dir()
    bin_dir = args.bin_dir or paths.get_user_bin_dir()

    # Decide on creating a shortcut
    create_shortcut = not bool(args.no_shortcut)
    if not args.non_interactive and not args.no_shortcut:
        create_shortcut = _prompt_yes_no("Create a CLI shortcut?", default=True)

    print("\nPlan:")
    print(f"- Blueprint package: {spec.package_name}")
    print(f"- Write to: {output_dir / spec.package_name}")
    if create_shortcut:
        print(f"- Shortcut: {bin_dir / (spec.abbreviation or spec.package_name)}")
    else:
        print("- Shortcut: (skipped)")

    if args.dry_run:
        print("\nDry-run complete. No files written.")
        return

    # Write files
    try:
        bp_path = _write_blueprint_file(spec, output_dir, overwrite=args.overwrite, template=args.template)
    except FileExistsError as e:
        print(str(e))
        sys.exit(2)

    # Verify
    try:
        _verify_python_file(bp_path)
    except Exception as e:
        print(f"Verification failed (syntax error): {e}")
        sys.exit(1)

    shortcut_path: Path | None = None
    if create_shortcut:
        try:
            shortcut_path = _install_shortcut(spec, bp_path, bin_dir, overwrite=args.overwrite)
        except FileExistsError as e:
            print(str(e))
            sys.exit(2)
        except Exception as e:
            print(f"Warning: Failed to create shortcut: {e}")

    # Optional import verification
    if args.verify_import:
        ok = _verify_importable(bp_path, spec.class_name)
        if not ok:
            print("Warning: Import verification failed (class not importable).")

    # Optional test scaffold
    if args.scaffold_tests:
        tests_dir = Path("tests") / "generated"
        test_path = _scaffold_tests(tests_dir, spec, bp_path)
        print(f"- Scaffolded pytest smoke test: {test_path}")

    # Summary
    print("\n✅ Team blueprint created!")
    print(f"- File: {bp_path}")
    if shortcut_path:
        print(f"- Shortcut: {shortcut_path}")
        print("  Tip: Add it to your PATH if not already.")
    else:
        print("- Shortcut: not created")
