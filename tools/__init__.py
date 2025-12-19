"""
Tools package with auto-discovery.

Structure:
- shared/   - Available for both Legacy and Unified modes
- legacy/   - Legacy autopost only
- unified/  - Unified Agent only

Use registry.py to access tools programmatically.
"""

from tools.registry import (
    TOOLS,
    ALL_TOOLS,
    get_tools_description,
    get_tools_for_mode,
    get_tools_description_for_mode,
    get_tools_enum_for_mode,
    get_tool_func,
    refresh_tools
)

__all__ = [
    "TOOLS",
    "ALL_TOOLS",
    "get_tools_description",
    "get_tools_for_mode",
    "get_tools_description_for_mode",
    "get_tools_enum_for_mode",
    "get_tool_func",
    "refresh_tools"
]
