"""Shared helper utilities."""

import os
import re
import subprocess
from pathlib import Path

import mysql.connector

from .config import DB_CONFIG, MAX_FILE_SIZE, SOURCE_PATH, QUESTS_PATH, SERVER_PATH


def rg_bin() -> str:
    return os.environ.get("RG_PATH", "rg")


def db_conn():
    return mysql.connector.connect(**DB_CONFIG)


def safe_read(path: Path, max_size: int = MAX_FILE_SIZE) -> str:
    if not path.is_file():
        return f"Error: {path} is not a file or does not exist."
    size = path.stat().st_size
    if size > max_size:
        return f"Error: file is {size:,} bytes (limit {max_size:,}). Use a more targeted query."
    return path.read_text(errors="replace")


def resolve_under(base: Path, rel_path: str) -> Path:
    # Block path traversal via ".." but allow symlinks within the base directory
    normed = os.path.normpath(rel_path)
    if normed.startswith("..") or normed.startswith("/"):
        raise ValueError("Path traversal not allowed")
    return base / normed


def resolve_source(rel_path: str) -> Path:
    return resolve_under(SOURCE_PATH, rel_path)


def resolve_quests(rel_path: str) -> Path:
    return resolve_under(QUESTS_PATH, rel_path)


def resolve_server(rel_path: str) -> Path:
    return resolve_under(SERVER_PATH, rel_path)


def ripgrep_search(
    pattern: str,
    search_path: Path,
    file_glob: str = "",
    max_results: int = 50,
) -> str:
    from .config import MAX_RESULTS
    max_results = min(max_results, MAX_RESULTS)
    cmd = [rg_bin(), "--no-heading", "--line-number", "--color=never", "-m", str(max_results)]
    if file_glob:
        g = file_glob
        if "/" in g and not g.startswith("**/"):
            g = "**/" + g
        cmd += ["-g", g]
    cmd += [pattern, str(search_path)]

    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        cmd = ["grep", "-rn", pattern, str(search_path)]
        result = subprocess.run(
            cmd, capture_output=True, timeout=30,
            encoding="utf-8", errors="replace",
        )

    output = result.stdout.strip()
    if not output:
        return "No matches found."

    base = str(search_path) + "/"
    lines = output.split("\n")[:max_results]
    return "\n".join(line.replace(base, "", 1) for line in lines)


def sanitize_table_name(table: str) -> str:
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
        raise ValueError("Invalid table name")
    return table
