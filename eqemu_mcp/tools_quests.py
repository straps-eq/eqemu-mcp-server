"""Tools for browsing and searching quest script files."""

from mcp.server.fastmcp import FastMCP

from .config import QUESTS_PATH, MAX_RESULTS, is_writable
from .helpers import ripgrep_search, resolve_quests, safe_read


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_quest_zones() -> str:
        """List all zone directories containing quest scripts."""
        if not QUESTS_PATH.is_dir():
            return f"Error: quests directory not found at {QUESTS_PATH}"
        zones = sorted(d.name for d in QUESTS_PATH.iterdir() if d.is_dir())
        return f"{len(zones)} zones:\n" + "\n".join(zones)

    @mcp.tool()
    def list_quest_files(zone: str) -> str:
        """List quest script files in a zone.

        Args:
            zone: Zone short name, e.g. 'gfaydark', 'qeynos2', 'global'.
        """
        zone_dir = resolve_quests(zone)
        if not zone_dir.is_dir():
            return f"Error: zone '{zone}' not found."
        files = sorted(f.name for f in zone_dir.rglob("*") if f.is_file())
        return f"{zone}: {len(files)} file(s)\n" + "\n".join(files)

    @mcp.tool()
    def read_quest_file(zone: str, filename: str) -> str:
        """Read a quest script file.

        Args:
            zone: Zone short name.
            filename: e.g. 'Priest_of_Discord.pl' or '#Fippy_Darkpaw.lua'.
        """
        return safe_read(resolve_quests(f"{zone}/{filename}"))

    @mcp.tool()
    def search_quests(
        pattern: str,
        zone: str = "",
        file_type: str = "",
        max_results: int = 50,
    ) -> str:
        """Search quest scripts using ripgrep.

        Args:
            pattern: Regex pattern.
            zone: Optional zone to restrict search.
            file_type: Optional extension filter, e.g. 'lua' or 'pl'.
            max_results: Max matches (default 50, max 200).
        """
        search_path = resolve_quests(zone) if zone else QUESTS_PATH
        glob = f"*.{file_type}" if file_type else ""
        return ripgrep_search(pattern, search_path, glob, max_results)


def register_write(mcp: FastMCP) -> None:
    """Write-mode quest tools."""

    @mcp.tool()
    def write_quest_file(zone: str, filename: str, content: str) -> str:
        """Create or overwrite a quest script file.

        Args:
            zone: Zone short name.
            filename: Script filename.
            content: Full file content to write.
        """
        zone_dir = resolve_quests(zone)
        if not zone_dir.is_dir():
            zone_dir.mkdir(parents=True, exist_ok=True)
        filepath = resolve_quests(f"{zone}/{filename}")
        filepath.write_text(content)
        return f"Written {len(content)} bytes to {zone}/{filename}"

    @mcp.tool()
    def delete_quest_file(zone: str, filename: str) -> str:
        """Delete a quest script file.

        Args:
            zone: Zone short name.
            filename: Script filename.
        """
        filepath = resolve_quests(f"{zone}/{filename}")
        if not filepath.is_file():
            return f"Error: {zone}/{filename} does not exist."
        filepath.unlink()
        return f"Deleted {zone}/{filename}"
