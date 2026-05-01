"""Tools for searching and reading the EQEmu documentation (docs.eqemu.io).

Requires the eqemu-docs-v2 repo cloned locally. If EQEMU_DOCS_PATH is not set,
the tool will attempt to clone it automatically on first use.
"""

import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import DOCS_PATH, DOCS_REPO_URL, DOCS_SITE_URL, MAX_RESULTS
from .helpers import rg_bin


def _get_docs_root() -> Path:
    """Return the docs markdown root, auto-cloning if needed."""
    if DOCS_PATH and DOCS_PATH.is_dir():
        docs_md = DOCS_PATH / "docs"
        if docs_md.is_dir():
            return docs_md
        return DOCS_PATH

    # Try common locations
    candidates = [
        Path("/opt/akk-stack/eqemu-docs/docs"),
        Path("/opt/akk-stack/eqemu-mcp-server/eqemu-docs/docs"),
        Path.home() / "eqemu-docs" / "docs",
    ]
    for c in candidates:
        if c.is_dir():
            return c

    # Auto-clone
    clone_target = Path("/opt/akk-stack/eqemu-docs")
    if not clone_target.exists():
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", DOCS_REPO_URL, str(clone_target)],
                capture_output=True, timeout=120,
            )
        except Exception:
            pass
    if (clone_target / "docs").is_dir():
        return clone_target / "docs"

    return Path("/nonexistent")


def _docs_url(rel_path: str) -> str:
    """Convert a relative doc file path to a docs.eqemu.io URL."""
    url_path = rel_path.replace(".md", "").replace("/README", "")
    return f"{DOCS_SITE_URL}/{url_path}"


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def search_docs(query: str, section: str = "", max_results: int = 30) -> str:
        """Search the EQEmu documentation (docs.eqemu.io) for a topic.

        Searches across all doc pages including quest API, server operations,
        database schema, configuration, NPC guides, item references, etc.

        Args:
            query: Search term or regex pattern.
            section: Optional section filter: 'schema', 'quest-api', 'server',
                     'akk-stack', 'developer', or '' for all.
            max_results: Max results (default 30).
        """
        docs_root = _get_docs_root()
        if not docs_root.is_dir():
            return "Error: EQEmu docs not found. Set EQEMU_DOCS_PATH or clone eqemu-docs-v2."

        search_path = docs_root
        if section:
            section_path = docs_root / section
            if section_path.is_dir():
                search_path = section_path

        max_results = min(max_results, MAX_RESULTS)
        cmd = [rg_bin(), "--no-heading", "--line-number", "--color=never",
               "-g", "*.md", "-m", str(max_results), "-i",
               query, str(search_path)]

        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
        except FileNotFoundError:
            cmd = ["grep", "-rn", "-i", "--include=*.md", query, str(search_path)]
            result = subprocess.run(
                cmd, capture_output=True, timeout=30,
                encoding="utf-8", errors="replace",
            )

        output = result.stdout.strip()
        if not output:
            return f"No documentation found for '{query}'."

        base = str(docs_root) + "/"
        lines = output.split("\n")[:max_results]
        formatted = []
        for line in lines:
            clean = line.replace(base, "", 1)
            # Add URL reference
            parts = clean.split(":", 1)
            if len(parts) >= 1:
                file_path = parts[0].split(":")[0]
                url = _docs_url(file_path)
                formatted.append(f"{clean}\n  -> {url}")
            else:
                formatted.append(clean)

        return f"Found {len(formatted)} result(s):\n\n" + "\n".join(formatted)

    @mcp.tool()
    def read_doc(path: str) -> str:
        """Read a specific documentation page by path.

        Args:
            path: Relative path within the docs, e.g.:
                  'schema/npcs/npc_types.md'
                  'quest-api/methods/mob.md'
                  'server/operation/loading-server-data.md'
                  'quest-api/events.md'
        """
        docs_root = _get_docs_root()
        if not docs_root.is_dir():
            return "Error: EQEmu docs not found."

        # Handle with or without .md extension
        if not path.endswith(".md"):
            # Try as-is first (directory with README), then with .md
            readme = docs_root / path / "README.md"
            if readme.is_file():
                content = readme.read_text(errors="replace")
                return f"[{_docs_url(path)}]\n\n{content}"
            path = path + ".md"

        filepath = (docs_root / path).resolve()
        if not str(filepath).startswith(str(docs_root.resolve())):
            return "Error: path traversal not allowed."
        if not filepath.is_file():
            return f"Error: doc page '{path}' not found. Use search_docs or list_doc_sections to find pages."

        content = filepath.read_text(errors="replace")
        url = _docs_url(path)
        return f"[{url}]\n\n{content}"

    @mcp.tool()
    def list_doc_sections() -> str:
        """List all top-level documentation sections and their subsections."""
        docs_root = _get_docs_root()
        if not docs_root.is_dir():
            return "Error: EQEmu docs not found."

        lines = ["EQEmu Documentation Sections:", "=" * 40]
        for section_dir in sorted(docs_root.iterdir()):
            if section_dir.is_dir() and not section_dir.name.startswith("."):
                subsections = sorted(d.name for d in section_dir.iterdir() if d.is_dir())
                md_files = sorted(f.stem for f in section_dir.glob("*.md") if f.stem != "README")
                items = subsections + md_files
                lines.append(f"\n{section_dir.name}/")
                for item in items[:30]:
                    lines.append(f"  {item}")
                if len(items) > 30:
                    lines.append(f"  ... and {len(items) - 30} more")

        return "\n".join(lines)

    @mcp.tool()
    def get_schema_doc(table: str) -> str:
        """Get the full schema documentation for a database table.

        Returns column definitions with descriptions, data types, relationships,
        and ER diagrams from the official EQEmu docs.

        Args:
            table: Table name, e.g. 'npc_types', 'items', 'spawn2', 'spells_new',
                   'loottable', 'character_data'.
        """
        docs_root = _get_docs_root()
        if not docs_root.is_dir():
            return "Error: EQEmu docs not found."

        schema_dir = docs_root / "schema"
        if not schema_dir.is_dir():
            return "Error: schema docs not found."

        # Search for the table file across all schema subdirectories
        matches = list(schema_dir.rglob(f"{table}.md"))
        if not matches:
            # Try fuzzy match
            all_schemas = list(schema_dir.rglob("*.md"))
            close = [f for f in all_schemas if table.lower() in f.stem.lower()]
            if close:
                suggestions = ", ".join(f.stem for f in close[:10])
                return f"Table '{table}' not found. Similar: {suggestions}"
            return f"No schema documentation found for '{table}'. Use list_schema_tables to see available tables."

        filepath = matches[0]
        content = filepath.read_text(errors="replace")
        rel = str(filepath.relative_to(docs_root))
        url = _docs_url(rel)
        return f"[{url}]\n\n{content}"

    @mcp.tool()
    def list_schema_tables(category: str = "") -> str:
        """List all documented database tables, optionally filtered by category.

        Args:
            category: Optional category filter, e.g. 'npcs', 'items', 'loot',
                      'spells', 'spawns', 'characters', 'zones', 'tasks',
                      'account', 'merchants', 'factions'. Empty for all.
        """
        docs_root = _get_docs_root()
        schema_dir = docs_root / "schema"
        if not schema_dir.is_dir():
            return "Error: schema docs not found."

        lines = []
        for cat_dir in sorted(schema_dir.iterdir()):
            if not cat_dir.is_dir():
                continue
            if category and category.lower() not in cat_dir.name.lower():
                continue
            tables = sorted(f.stem for f in cat_dir.glob("*.md") if f.stem != "README")
            if tables:
                lines.append(f"\n{cat_dir.name}/ ({len(tables)} tables)")
                for t in tables:
                    lines.append(f"  {t}")

        if not lines:
            return f"No schema categories found matching '{category}'." if category else "No schema docs found."

        return "Documented Database Tables:\n" + "\n".join(lines)

    @mcp.tool()
    def get_quest_api_doc(subject: str, language: str = "") -> str:
        """Get quest API documentation for a specific class or topic.

        Returns method signatures, event documentation, and usage examples
        from the official EQEmu docs.

        Args:
            subject: Class or topic, e.g. 'mob', 'client', 'npc', 'entity_list',
                     'events', 'introduction', 'database'.
                     For events: 'perl-player', 'lua-npc', 'perl-npc', etc.
            language: Optional: 'perl' or 'lua' to filter event docs.
        """
        docs_root = _get_docs_root()
        qa_dir = docs_root / "quest-api"
        if not qa_dir.is_dir():
            return "Error: quest-api docs not found."

        # Check methods/
        methods_file = qa_dir / "methods" / f"{subject}.md"
        if methods_file.is_file():
            content = methods_file.read_text(errors="replace")
            rel = str(methods_file.relative_to(docs_root))
            return f"[{_docs_url(rel)}]\n\n{content}"

        # Check events/
        events_file = qa_dir / "events" / f"{subject}.md"
        if events_file.is_file():
            content = events_file.read_text(errors="replace")
            rel = str(events_file.relative_to(docs_root))
            return f"[{_docs_url(rel)}]\n\n{content}"

        # Check with language prefix for events
        if language:
            lang_file = qa_dir / "events" / f"{language}-{subject}.md"
            if lang_file.is_file():
                content = lang_file.read_text(errors="replace")
                rel = str(lang_file.relative_to(docs_root))
                return f"[{_docs_url(rel)}]\n\n{content}"

        # Check top-level quest-api/
        top_file = qa_dir / f"{subject}.md"
        if top_file.is_file():
            content = top_file.read_text(errors="replace")
            rel = str(top_file.relative_to(docs_root))
            return f"[{_docs_url(rel)}]\n\n{content}"

        # List what's available
        methods = sorted(f.stem for f in (qa_dir / "methods").glob("*.md"))
        events = sorted(f.stem for f in (qa_dir / "events").glob("*.md"))
        return (
            f"'{subject}' not found in quest-api docs.\n\n"
            f"Available methods docs: {', '.join(methods)}\n\n"
            f"Available events docs: {', '.join(events)}"
        )

    @mcp.tool()
    def get_server_doc(topic: str) -> str:
        """Get server operation/configuration documentation.

        Args:
            topic: Topic path, e.g.:
                   'operation/loading-server-data'
                   'operation/in-game-command-reference'
                   'operation/server-rules'
                   'npc/body-types'
                   'items/item-types'
                   'scripting'
        """
        docs_root = _get_docs_root()
        server_dir = docs_root / "server"
        if not server_dir.is_dir():
            return "Error: server docs not found."

        # Try direct path
        filepath = server_dir / f"{topic}.md"
        if filepath.is_file():
            content = filepath.read_text(errors="replace")
            rel = str(filepath.relative_to(docs_root))
            return f"[{_docs_url(rel)}]\n\n{content}"

        # Try as directory with README
        dir_path = server_dir / topic / "README.md"
        if dir_path.is_file():
            content = dir_path.read_text(errors="replace")
            return f"[{_docs_url(f'server/{topic}')}]\n\n{content}"

        # Search for the topic
        matches = list(server_dir.rglob(f"*{topic}*.md"))
        if matches:
            filepath = matches[0]
            content = filepath.read_text(errors="replace")
            rel = str(filepath.relative_to(docs_root))
            return f"[{_docs_url(rel)}]\n\n{content}"

        # List what's available
        sections = sorted(d.name for d in server_dir.iterdir() if d.is_dir())
        return f"Topic '{topic}' not found.\n\nAvailable server doc sections: {', '.join(sections)}"
