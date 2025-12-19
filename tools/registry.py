"""
Tool registry with auto-discovery.

Discovers tools from subdirectories:
- shared/   - available for both Legacy and Unified modes
- legacy/   - Legacy autopost only
- unified/  - Unified Agent only

Each tool file should export:
- TOOL_CONFIG: dict with name, description, params, optional tier
- An async function with the same name as TOOL_CONFIG["name"]
"""

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Callable

from config.settings import settings

logger = logging.getLogger(__name__)

# Tools that require image generation to be enabled
IMAGE_TOOLS = {"generate_image"}
# Params that require image generation to be enabled
IMAGE_PARAMS = {"include_image"}
# Tools that require mentions to be enabled
MENTION_TOOLS = {"get_mentions", "create_reply"}


def _discover_tools_from_folder(folder_name: str) -> dict[str, dict]:
    """
    Discover tools from a specific folder.

    Args:
        folder_name: Name of the folder (shared, legacy, unified).

    Returns:
        Dict mapping tool_name -> {config, func}.
    """
    tools = {}
    folder_path = Path(__file__).parent / folder_name

    if not folder_path.exists():
        logger.warning(f"[REGISTRY] Folder not found: {folder_path}")
        return tools

    for _, module_name, _ in pkgutil.iter_modules([str(folder_path)]):
        if module_name.startswith("_"):
            continue

        try:
            module = importlib.import_module(f"tools.{folder_name}.{module_name}")

            if hasattr(module, "TOOL_CONFIG"):
                config = module.TOOL_CONFIG
                tool_name = config["name"]

                if hasattr(module, tool_name):
                    tool_func = getattr(module, tool_name)
                    tools[tool_name] = {
                        "config": config,
                        "func": tool_func,
                        "folder": folder_name
                    }
                    logger.debug(f"[REGISTRY] Discovered {folder_name}/{tool_name}")
                else:
                    logger.warning(f"[REGISTRY] {module_name} has TOOL_CONFIG but no function '{tool_name}'")

        except Exception as e:
            logger.error(f"[REGISTRY] Error loading {folder_name}/{module_name}: {e}")

    return tools


def _discover_all_tools() -> dict[str, dict]:
    """Discover all tools from all folders."""
    all_tools = {}

    for folder in ["shared", "legacy", "unified"]:
        folder_tools = _discover_tools_from_folder(folder)
        all_tools.update(folder_tools)

    logger.info(f"[REGISTRY] Discovered {len(all_tools)} tools: {list(all_tools.keys())}")
    return all_tools


# Auto-discover on module load
ALL_TOOLS = _discover_all_tools()


def get_tools_for_mode(mode: str, tier: str = "basic+") -> dict[str, dict]:
    """
    Get tools available for a specific mode.

    Args:
        mode: "legacy" or "unified"
        tier: "free" or "basic+" (for filtering tier-restricted tools)

    Returns:
        Dict of available tools for this mode.
    """
    available = {}

    for name, tool in ALL_TOOLS.items():
        folder = tool["folder"]
        config = tool["config"]

        # Skip image tools if image generation is disabled
        if name in IMAGE_TOOLS and not settings.enable_image_generation:
            continue

        # Skip mention tools if mentions are disabled
        if name in MENTION_TOOLS and not settings.allow_mentions:
            continue

        # Check if tool is available for this mode
        if mode == "legacy":
            if folder in ["shared", "legacy"]:
                available[name] = tool
        elif mode == "unified":
            if folder in ["shared", "unified"]:
                # Check tier restriction
                tool_tier = config.get("tier", "all")
                if tool_tier == "all" or (tool_tier == "basic+" and tier != "free"):
                    available[name] = tool

    return available


def get_tool_func(name: str) -> Callable | None:
    """Get a tool function by name."""
    if name in ALL_TOOLS:
        return ALL_TOOLS[name]["func"]
    return None


def get_tools_description_for_mode(mode: str, tier: str = "basic+") -> str:
    """
    Generate human-readable tools description for prompts.

    Args:
        mode: "legacy" or "unified"
        tier: "free" or "basic+"

    Returns:
        Formatted string describing available tools.
    """
    tools = get_tools_for_mode(mode, tier)
    lines = ["## AVAILABLE TOOLS\n"]

    for i, (name, tool) in enumerate(tools.items(), 1):
        config = tool["config"]
        desc = config["description"]
        params = config.get("params", {})

        lines.append(f"{i}. **{name}** - {desc}")

        # Filter out image params if image generation is disabled
        filtered_params = {
            pname: pinfo for pname, pinfo in params.items()
            if pname not in IMAGE_PARAMS or settings.enable_image_generation
        }

        if filtered_params:
            lines.append("   - params:")
            for pname, pinfo in filtered_params.items():
                if isinstance(pinfo, dict):
                    ptype = pinfo.get("type", "string")
                    pdesc = pinfo.get("description", "")
                    required = pinfo.get("required", False)
                    req_marker = " [REQUIRED]" if required else ""
                    lines.append(f"     - {pname} ({ptype}){req_marker}: {pdesc}")
                else:
                    lines.append(f"     - {pname}")
        else:
            lines.append("   - params: none")

        lines.append("")

    return "\n".join(lines)


def get_tools_enum_for_mode(mode: str, tier: str = "basic+") -> list[str]:
    """
    Get list of tool names for JSON schema enum.

    Args:
        mode: "legacy" or "unified"
        tier: "free" or "basic+"

    Returns:
        List of tool names.
    """
    tools = get_tools_for_mode(mode, tier)
    return list(tools.keys())


def get_tools_params_schema() -> dict:
    """
    Get combined params schema for all tools.

    Returns:
        Dict of all possible params across all tools.
    """
    all_params = {}

    for tool in ALL_TOOLS.values():
        params = tool["config"].get("params", {})
        for pname, pinfo in params.items():
            # Skip image params if image generation is disabled
            if pname in IMAGE_PARAMS and not settings.enable_image_generation:
                continue

            if pname not in all_params:
                if isinstance(pinfo, dict):
                    all_params[pname] = {"type": pinfo.get("type", "string")}
                else:
                    all_params[pname] = {"type": "string"}

    return all_params


# Legacy compatibility - expose TOOLS dict for autopost.py
TOOLS = {name: tool["func"] for name, tool in get_tools_for_mode("legacy").items()}


def get_tools_description() -> str:
    """Legacy compatibility - get tools description for autopost."""
    return get_tools_description_for_mode("legacy")


def refresh_tools() -> None:
    """Re-discover tools (useful if tools are added at runtime)."""
    global ALL_TOOLS, TOOLS
    ALL_TOOLS = _discover_all_tools()
    TOOLS = {name: tool["func"] for name, tool in get_tools_for_mode("legacy").items()}
