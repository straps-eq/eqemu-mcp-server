"""Tools for exploring the EQEmu C++ source code."""

from mcp.server.fastmcp import FastMCP

from .config import SOURCE_PATH, MAX_RESULTS
from .helpers import ripgrep_search, resolve_source, safe_read


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def search_source(
        pattern: str,
        file_filter: str = "",
        max_results: int = 50,
    ) -> str:
        """Search the EQEmu C++ source code using ripgrep.

        Args:
            pattern: Regex pattern to search for.
            file_filter: Optional glob, e.g. '*.h' or 'zone/*.cpp'.
            max_results: Max matching lines (default 50, max 200).
        """
        return ripgrep_search(pattern, SOURCE_PATH, file_filter, max_results)

    @mcp.tool()
    def get_source_file(path: str) -> str:
        """Read an EQEmu source file by relative path.

        Args:
            path: e.g. 'zone/lua_mob.cpp' or 'common/database.h'.
        """
        return safe_read(resolve_source(path))

    @mcp.tool()
    def list_source_files(directory: str = "", pattern: str = "") -> str:
        """List files in the EQEmu source tree.

        Args:
            directory: Relative directory, e.g. 'zone' or 'common/repositories'.
            pattern: Optional glob, e.g. '*.h'.
        """
        target = resolve_source(directory) if directory else SOURCE_PATH
        if not target.is_dir():
            return f"Error: {directory} is not a directory."
        if pattern:
            files = sorted(str(f.relative_to(SOURCE_PATH)) for f in target.glob(pattern) if f.is_file())
        else:
            files = sorted(str(f.relative_to(SOURCE_PATH)) for f in target.iterdir())
        return "\n".join(files[:MAX_RESULTS]) if files else "No files found."
