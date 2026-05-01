"""Tools for inspecting and managing the EQEmu server environment."""

import json
import os
import subprocess

from mcp.server.fastmcp import FastMCP

from .config import SERVER_PATH, DOCKER_CONTAINER, MAX_RESULTS
from .helpers import resolve_server, safe_read


def _docker_exec(container: str, cmd: str, timeout: int = 15) -> str:
    try:
        result = subprocess.run(
            ["docker", "exec", container, "bash", "-c", cmd],
            capture_output=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return result.stdout.strip() or result.stderr.strip()
    except FileNotFoundError:
        return "Error: docker not available."
    except subprocess.TimeoutExpired:
        return "Error: command timed out."


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_server_files(directory: str = "") -> str:
        """List files in the EQEmu server directory.

        Args:
            directory: Relative path, e.g. 'plugins', 'lua_modules', 'logs'.
        """
        target = resolve_server(directory) if directory else SERVER_PATH
        if target.is_symlink() and not target.resolve().is_dir():
            return f"Error: {directory} is a symlink to {os.readlink(target)} which is not accessible (may be inside a Docker container)."
        if not target.is_dir():
            return f"Error: {directory} is not a directory."
        entries = sorted(str(f.relative_to(SERVER_PATH)) for f in target.iterdir())
        return "\n".join(entries[:MAX_RESULTS])

    @mcp.tool()
    def read_server_file(path: str) -> str:
        """Read a file from the server directory.

        Args:
            path: Relative path, e.g. 'plugins/check_handin.pl' or 'eqemu_config.json'.
        """
        return safe_read(resolve_server(path))

    @mcp.tool()
    def get_server_config() -> str:
        """Read the eqemu_config.json server configuration (sensitive fields redacted)."""
        config_path = SERVER_PATH / "eqemu_config.json"
        if not config_path.is_file():
            return "Error: eqemu_config.json not found."
        try:
            config = json.loads(config_path.read_text())
            # Redact passwords/keys
            _redact(config)
            return json.dumps(config, indent=2)
        except json.JSONDecodeError as e:
            return f"Error parsing config: {e}"

    @mcp.tool()
    def get_server_rules(filter: str = "") -> str:
        """Get server rules from the rule_values table.

        Args:
            filter: Optional substring filter on rule names, e.g. 'AA', 'Combat', 'Zone'.
        """
        from .helpers import db_conn
        conn = db_conn()
        try:
            cursor = conn.cursor()
            if filter:
                cursor.execute(
                    "SELECT rule_name, rule_value, notes FROM rule_values WHERE rule_name LIKE %s ORDER BY rule_name",
                    (f"%{filter}%",),
                )
            else:
                cursor.execute("SELECT rule_name, rule_value, notes FROM rule_values ORDER BY rule_name")
            rows = cursor.fetchall()
            if not rows:
                return "No rules found."
            lines = [f"{'Rule':<55} {'Value':<20} Notes", "-" * 100]
            for name, value, notes in rows:
                note_str = (notes or "")[:60]
                lines.append(f"{name:<55} {str(value):<20} {note_str}")
            return "\n".join(lines)
        finally:
            conn.close()

    @mcp.tool()
    def get_server_logs(log_type: str = "world", lines: int = 100) -> str:
        """Read recent server log entries.

        Args:
            log_type: 'world', 'zone', 'login', 'ucs', or a specific zone log filename.
            lines: Number of lines to return (default 100, max 500).
        """
        import os
        lines = min(lines, 500)
        logs_dir = SERVER_PATH / "logs"

        if log_type == "zone":
            # list available zone logs
            zone_logs = sorted(
                (SERVER_PATH / "logs" / "zone").glob("*.log"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if not zone_logs:
                return "No zone logs found."
            entries = [f.name for f in zone_logs[:30]]
            return f"Recent zone logs (use log_type with full filename):\n" + "\n".join(entries)

        # Find the most recent matching log
        if "/" in log_type or log_type.endswith(".log"):
            log_path = resolve_server(f"logs/{log_type}" if not log_type.startswith("logs/") else log_type)
        else:
            matching = sorted(
                logs_dir.glob(f"{log_type}_*.log"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if not matching:
                return f"No {log_type} logs found."
            log_path = matching[0]

        if not log_path.is_file():
            return f"Error: log file not found."

        # Read last N lines
        content = log_path.read_text(errors="replace")
        all_lines = content.split("\n")
        tail = all_lines[-lines:]
        return f"[{log_path.name}] last {len(tail)} lines:\n" + "\n".join(tail)

    @mcp.tool()
    def get_crash_logs() -> str:
        """List and read recent crash logs from the server."""
        crashes_dir = SERVER_PATH / "logs" / "crashes"
        if not crashes_dir.is_dir():
            return "No crashes directory found."
        files = sorted(crashes_dir.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            return "No crash logs found."

        result = [f"Found {len(files)} crash log(s):"]
        for f in files[:5]:
            result.append(f"\n--- {f.name} ---")
            content = f.read_text(errors="replace")
            result.append(content[:2000])
        return "\n".join(result)

    @mcp.tool()
    def get_content_flags() -> str:
        """Get all content flags and their enabled/disabled status."""
        from .helpers import db_conn
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT flag_name, enabled, notes FROM content_flags ORDER BY flag_name")
            rows = cursor.fetchall()
            if not rows:
                return "No content flags found."
            lines = [f"{'Flag':<40} {'Enabled':<10} Notes", "-" * 80]
            for name, enabled, notes in rows:
                lines.append(f"{name:<40} {bool(enabled)!s:<10} {(notes or '')[:40]}")
            return "\n".join(lines)
        finally:
            conn.close()

    @mcp.tool()
    def get_expansion_info() -> str:
        """Get current expansion setting and zone expansion data."""
        from .helpers import db_conn
        conn = db_conn()
        try:
            cursor = conn.cursor()
            # Get current expansion from rules
            cursor.execute(
                "SELECT rule_value FROM rule_values WHERE rule_name = 'Expansion:CurrentExpansion'"
            )
            row = cursor.fetchone()
            exp_id = row[0] if row else "unknown"

            exp_names = {
                "0": "Classic", "1": "Ruins of Kunark", "2": "Scars of Velious",
                "3": "Shadows of Luclin", "4": "Planes of Power", "5": "Legacy of Ykesha",
                "6": "Lost Dungeons of Norrath", "7": "Gates of Discord",
                "8": "Omens of War", "9": "Dragons of Norrath", "10": "Depths of Darkhollow",
                "11": "Prophecy of Ro", "12": "The Serpent's Spine",
                "13": "The Buried Sea", "14": "Secrets of Faydwer",
            }

            # Count zones per expansion
            cursor.execute(
                "SELECT expansion, COUNT(*) FROM zone GROUP BY expansion ORDER BY expansion"
            )
            zone_counts = cursor.fetchall()

            lines = [f"Current Expansion: {exp_id} ({exp_names.get(str(exp_id), 'Unknown')})", ""]
            lines.append(f"{'Expansion':<5} {'Name':<35} {'Zones':<6}")
            lines.append("-" * 50)
            for exp, count in zone_counts:
                lines.append(f"{exp:<5} {exp_names.get(str(exp), 'Unknown'):<35} {count}")
            return "\n".join(lines)
        finally:
            conn.close()


def register_write(mcp: FastMCP) -> None:
    """Write-mode server management tools."""

    @mcp.tool()
    def set_server_rule(rule_name: str, rule_value: str, notes: str = "") -> str:
        """Update a server rule value.

        Args:
            rule_name: Full rule name, e.g. 'AA:ExpPerPoint'.
            rule_value: New value for the rule.
            notes: Optional note to update.
        """
        from .helpers import db_conn
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT rule_value FROM rule_values WHERE rule_name = %s", (rule_name,))
            row = cursor.fetchone()
            if not row:
                return f"Error: rule '{rule_name}' not found."
            old_value = row[0]
            if notes:
                cursor.execute(
                    "UPDATE rule_values SET rule_value = %s, notes = %s WHERE rule_name = %s",
                    (rule_value, notes, rule_name),
                )
            else:
                cursor.execute(
                    "UPDATE rule_values SET rule_value = %s WHERE rule_name = %s",
                    (rule_value, rule_name),
                )
            conn.commit()
            return f"Updated {rule_name}: {old_value} -> {rule_value}\nNote: use #reload rules in-game to apply."
        finally:
            conn.close()

    @mcp.tool()
    def set_content_flag(flag_name: str, enabled: bool) -> str:
        """Enable or disable a content flag.

        Args:
            flag_name: Flag name, e.g. 'peq_halloween'.
            enabled: True to enable, False to disable.
        """
        from .helpers import db_conn
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT enabled FROM content_flags WHERE flag_name = %s", (flag_name,))
            row = cursor.fetchone()
            if not row:
                return f"Error: flag '{flag_name}' not found."
            cursor.execute(
                "UPDATE content_flags SET enabled = %s WHERE flag_name = %s",
                (1 if enabled else 0, flag_name),
            )
            conn.commit()
            return f"Set {flag_name} = {'enabled' if enabled else 'disabled'}\nNote: use #reload content_flags in-game to apply."
        finally:
            conn.close()


def _redact(obj, depth=0):
    """Recursively redact password/key fields."""
    if depth > 10:
        return
    if isinstance(obj, dict):
        for key in obj:
            if any(s in key.lower() for s in ("password", "key", "secret", "token")):
                obj[key] = "***REDACTED***"
            else:
                _redact(obj[key], depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _redact(item, depth + 1)
