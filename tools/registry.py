"""
Tool registry with auto-discovery.

Automatically discovers tools from the tools/ directory.
Each tool file should export:
- TOOL_SCHEMA: OpenAI-style function calling schema
- The function with the same name as schema["function"]["name"]
"""

import importlib
import logging
import pkgutil
from pathlib import Path

logger = logging.getLogger(__name__)


def _discover_tools() -> tuple[dict, list]:
    """
    Auto-discover all tools in tools/ directory.

    Scans all Python modules in the tools/ directory and collects:
    - Tool functions (callable)
    - Tool schemas (for LLM function calling)

    Returns:
        Tuple of (tools dict, schemas list).
    """
    tools = {}
    schemas = []

    tools_path = Path(__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(tools_path)]):
        # Skip registry and __init__
        if module_name in ("registry", "__init__"):
            continue

        try:
            module = importlib.import_module(f"tools.{module_name}")

            # Check if module exports TOOL_SCHEMA
            if hasattr(module, "TOOL_SCHEMA"):
                schema = module.TOOL_SCHEMA
                tool_name = schema["function"]["name"]

                # Get the tool function
                if hasattr(module, tool_name):
                    tool_func = getattr(module, tool_name)
                    tools[tool_name] = tool_func
                    schemas.append(schema)
                    logger.debug(f"[REGISTRY] Discovered tool: {tool_name}")
                else:
                    logger.warning(
                        f"[REGISTRY] Tool {module_name} has TOOL_SCHEMA "
                        f"but no function named '{tool_name}'"
                    )
            else:
                logger.debug(f"[REGISTRY] Skipping {module_name}: no TOOL_SCHEMA")

        except Exception as e:
            logger.error(f"[REGISTRY] Error loading tool {module_name}: {e}")

    logger.info(f"[REGISTRY] Discovered {len(tools)} tools: {list(tools.keys())}")
    return tools, schemas


# Auto-discover tools on module load
TOOLS, TOOLS_SCHEMA = _discover_tools()


def get_tools_description() -> str:
    """
    Generate human-readable tools description from TOOLS_SCHEMA.

    Used in agent prompts so LLM knows what tools are available.
    When you add a new tool with TOOL_SCHEMA, it automatically appears here.

    Returns:
        Formatted string describing all available tools.
    """
    lines = ["### Available Tools:"]

    for i, tool_def in enumerate(TOOLS_SCHEMA, 1):
        func = tool_def["function"]
        name = func["name"]
        desc = func["description"]
        params = func["parameters"]["properties"]
        required = func["parameters"].get("required", [])

        lines.append(f"\n**{i}. {name}**")
        lines.append(f"   {desc}")
        lines.append(f"   Parameters:")

        for param_name, param_info in params.items():
            req = "(required)" if param_name in required else "(optional)"
            lines.append(f"   - {param_name}: {param_info['description']} {req}")

    return "\n".join(lines)


def refresh_tools() -> None:
    """
    Re-discover tools (useful if tools are added at runtime).
    """
    global TOOLS, TOOLS_SCHEMA
    TOOLS, TOOLS_SCHEMA = _discover_tools()
