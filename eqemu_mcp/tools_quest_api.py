"""Tools for exploring the Lua and Perl quest API bindings."""

import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import SOURCE_PATH


def _parse_lua_methods(filepath: Path) -> list[dict]:
    methods = []
    content = filepath.read_text(errors="replace")

    for m in re.finditer(
        r'\.def\(\s*"([^"]+)"\s*,\s*(?:\(([^)]*\([^)]*\)[^)]*)\)|[^)]*&\w+::(\w+))',
        content,
    ):
        methods.append({"name": m.group(1), "signature": (m.group(2) or "").strip()})

    for m in re.finditer(
        r'luabind::def\(\s*"([^"]+)"\s*,\s*(?:\(([^)]*\([^)]*\)[^)]*)\)|[^)]*)',
        content,
    ):
        methods.append({"name": m.group(1), "signature": (m.group(2) or "").strip()})

    seen: dict[str, dict] = {}
    for meth in methods:
        key = meth["name"]
        if key not in seen or (not seen[key]["signature"] and meth["signature"]):
            seen[key] = meth
    return list(seen.values())


def _parse_perl_methods(filepath: Path) -> list[dict]:
    methods = []
    content = filepath.read_text(errors="replace")

    for m in re.finditer(r'package\.add\(\s*"([^"]+)"', content):
        methods.append({"name": m.group(1), "signature": ""})

    for m in re.finditer(r'newXS\s*\(\s*"[^:]*::([^"]+)"', content):
        methods.append({"name": m.group(1), "signature": ""})

    func_pattern = re.compile(r'^[\w*&<> ]+\s+Perl_\w+_(\w+)\s*\(([^)]*)\)', re.MULTILINE)
    sig_map: dict[str, str] = {}
    for m in func_pattern.finditer(content):
        sig_map[m.group(1)] = m.group(2).strip()

    for meth in methods:
        if meth["name"] in sig_map and not meth["signature"]:
            meth["signature"] = sig_map[meth["name"]]

    seen: dict[str, dict] = {}
    for meth in methods:
        if meth["name"] not in seen:
            seen[meth["name"]] = meth
    return list(seen.values())


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_quest_api_classes() -> str:
        """List all Lua/Perl quest API classes with method counts."""
        zone_dir = SOURCE_PATH / "zone"
        classes = []
        for f in sorted(zone_dir.glob("lua_*.cpp")):
            name = f.stem.replace("lua_", "")
            classes.append(f"lua/{name}: {len(_parse_lua_methods(f))} methods ({f.name})")
        for f in sorted(zone_dir.glob("perl_*.cpp")):
            name = f.stem.replace("perl_", "")
            classes.append(f"perl/{name}: {len(_parse_perl_methods(f))} methods ({f.name})")
        return "\n".join(classes) if classes else "No quest API files found."

    @mcp.tool()
    def get_quest_api_methods(
        class_name: str,
        language: str = "lua",
        filter: str = "",
    ) -> str:
        """Get quest API methods for a class.

        Args:
            class_name: e.g. 'mob', 'client', 'npc', 'general', 'entity_list'.
            language: 'lua' or 'perl'.
            filter: Optional substring filter on method names.
        """
        filepath = SOURCE_PATH / "zone" / f"{language}_{class_name}.cpp"
        if not filepath.is_file():
            return f"Error: {language}_{class_name}.cpp not found. Use list_quest_api_classes."

        methods = _parse_lua_methods(filepath) if language == "lua" else _parse_perl_methods(filepath)
        if filter:
            fl = filter.lower()
            methods = [m for m in methods if fl in m["name"].lower()]
        if not methods:
            return "No methods found" + (f" matching '{filter}'." if filter else ".")

        lines = []
        for m in sorted(methods, key=lambda x: x["name"]):
            lines.append(f"{m['name']}  —  {m['signature']}" if m["signature"] else m["name"])

        header = f"{language}/{class_name}: {len(lines)} method(s)"
        if filter:
            header += f" matching '{filter}'"
        return header + "\n" + "-" * len(header) + "\n" + "\n".join(lines)
