"""Tools for querying the PEQ database schema and data."""

import re

from mcp.server.fastmcp import FastMCP

from .config import MAX_RESULTS, MAX_QUERY_ROWS
from .helpers import db_conn, sanitize_table_name


# Well-known EQEmu table relationships
_KNOWN_RELATIONS = {
    "npc_types": [
        "spawnentry.npcID -> npc_types.id",
        "npc_types_tint.id -> npc_types.id",
        "npc_faction.id -> npc_types.npc_faction_id",
        "merchantlist.merchantid -> npc_types.merchant_id",
        "loottable.id -> npc_types.loottable_id",
        "npc_spells.id -> npc_types.npc_spells_id",
    ],
    "spawn2": [
        "spawnentry.spawngroupID -> spawn2.spawngroupID",
        "spawngroup.id -> spawn2.spawngroupID",
        "zone.short_name -> spawn2.zone",
    ],
    "spawnentry": [
        "npc_types.id -> spawnentry.npcID",
        "spawngroup.id -> spawnentry.spawngroupID",
    ],
    "spawngroup": [
        "spawn2.spawngroupID -> spawngroup.id",
        "spawnentry.spawngroupID -> spawngroup.id",
    ],
    "items": [
        "lootdrop_entries.item_id -> items.id",
        "merchantlist.item -> items.id",
        "tradeskill_recipe_entries.item_id -> items.id",
        "starting_items.item_id -> items.id",
    ],
    "loottable": [
        "npc_types.loottable_id -> loottable.id",
        "loottable_entries.loottable_id -> loottable.id",
    ],
    "loottable_entries": [
        "loottable.id -> loottable_entries.loottable_id",
        "lootdrop.id -> loottable_entries.lootdrop_id",
    ],
    "lootdrop": [
        "loottable_entries.lootdrop_id -> lootdrop.id",
        "lootdrop_entries.lootdrop_id -> lootdrop.id",
    ],
    "lootdrop_entries": [
        "lootdrop.id -> lootdrop_entries.lootdrop_id",
        "items.id -> lootdrop_entries.item_id",
    ],
    "zone": [
        "spawn2.zone -> zone.short_name",
        "doors.zone -> zone.short_name",
    ],
    "doors": [
        "zone.short_name -> doors.zone",
    ],
    "merchantlist": [
        "npc_types.merchant_id -> merchantlist.merchantid",
        "items.id -> merchantlist.item",
    ],
    "npc_faction": [
        "npc_types.npc_faction_id -> npc_faction.id",
        "npc_faction_entries.npc_faction_id -> npc_faction.id",
    ],
    "npc_faction_entries": [
        "npc_faction.id -> npc_faction_entries.npc_faction_id",
        "faction_list.id -> npc_faction_entries.faction_id",
    ],
    "tasks": [
        "task_activities.taskid -> tasks.id",
        "character_tasks.taskid -> tasks.id",
        "tasksets.taskid -> tasks.id",
    ],
    "task_activities": [
        "tasks.id -> task_activities.taskid",
    ],
    "tradeskill_recipe": [
        "tradeskill_recipe_entries.recipe_id -> tradeskill_recipe.id",
    ],
    "tradeskill_recipe_entries": [
        "tradeskill_recipe.id -> tradeskill_recipe_entries.recipe_id",
        "items.id -> tradeskill_recipe_entries.item_id",
    ],
    "character_data": [
        "account.id -> character_data.account_id",
        "zone.zoneidnumber -> character_data.zone_id",
    ],
    "account": [
        "character_data.account_id -> account.id",
    ],
    "spells_new": [
        "npc_spells_entries.spellid -> spells_new.id",
    ],
}


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_tables(filter: str = "") -> str:
        """List all tables in the PEQ database.

        Args:
            filter: Optional substring filter on table names.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            if filter:
                fl = filter.lower()
                tables = [t for t in tables if fl in t.lower()]
            return f"{len(tables)} table(s):\n" + "\n".join(tables)
        finally:
            conn.close()

    @mcp.tool()
    def describe_table(table: str) -> str:
        """Get column definitions for a database table.

        Args:
            table: Table name, e.g. 'npc_types', 'items', 'spawnentry'.
        """
        table = sanitize_table_name(table)
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(f"DESCRIBE `{table}`")
            rows = cursor.fetchall()
            header = f"{'Column':<40} {'Type':<30} {'Null':<6} {'Key':<6} {'Default':<20} {'Extra'}"
            lines = [header, "-" * len(header)]
            for col, typ, null, key, default, extra in rows:
                lines.append(
                    f"{col:<40} {typ:<30} {null:<6} {key or '':<6} {str(default or ''):<20} {extra or ''}"
                )
            return "\n".join(lines)
        finally:
            conn.close()

    @mcp.tool()
    def run_query(sql: str, limit: int = 100) -> str:
        """Run a read-only SQL query.

        Only SELECT, SHOW, DESCRIBE, and EXPLAIN are allowed.

        Args:
            sql: The SQL query.
            limit: Max rows (default 100, max 500).
        """
        limit = min(limit, MAX_QUERY_ROWS)
        stripped = sql.strip().rstrip(";").strip()
        first_word = stripped.split()[0].upper() if stripped else ""
        if first_word not in ("SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN"):
            return "Error: only SELECT, SHOW, DESCRIBE, and EXPLAIN queries are allowed."

        dangerous = re.compile(
            r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|GRANT|REVOKE|INTO\s+OUTFILE|INTO\s+DUMPFILE|LOAD_FILE)\b',
            re.IGNORECASE,
        )
        if dangerous.search(stripped):
            return "Error: query contains disallowed keywords."

        if first_word == "SELECT" and "LIMIT" not in stripped.upper():
            stripped += f" LIMIT {limit}"

        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(stripped)
            rows = cursor.fetchall()
            if not rows:
                return "Query returned 0 rows."
            columns = [desc[0] for desc in cursor.description]
            col_widths = [len(c) for c in columns]
            for row in rows:
                for i, val in enumerate(row):
                    col_widths[i] = max(col_widths[i], len(str(val)))
            col_widths = [min(w, 60) for w in col_widths]

            header = " | ".join(c.ljust(col_widths[i]) for i, c in enumerate(columns))
            sep = "-+-".join("-" * w for w in col_widths)
            lines = [header, sep]
            for row in rows[:limit]:
                lines.append(" | ".join(str(v or "").ljust(col_widths[i])[:60] for i, v in enumerate(row)))

            result = "\n".join(lines)
            if len(rows) > limit:
                result += f"\n\n... {len(rows) - limit} more rows"
            return result
        finally:
            conn.close()

    @mcp.tool()
    def table_relationships(table: str) -> str:
        """Show FK relationships for a table.

        Args:
            table: Table name.
        """
        table = sanitize_table_name(table)
        lines = [f"Relationships for '{table}':"]
        if table in _KNOWN_RELATIONS:
            for rel in _KNOWN_RELATIONS[table]:
                lines.append(f"  {rel}")
        else:
            lines.append("  (no pre-defined relationships)")

        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(f"DESCRIBE `{table}`")
            rows = cursor.fetchall()
            fk_cols = [r[0] for r in rows if r[0].endswith(("_id", "ID", "id")) or r[0] in ("npcid", "zoneid")]
            if fk_cols:
                lines.append(f"\n  Likely FK columns: {', '.join(fk_cols)}")
        except Exception:
            pass
        finally:
            conn.close()

        return "\n".join(lines)


def register_write(mcp: FastMCP) -> None:
    """Write-mode database tools."""

    @mcp.tool()
    def run_write_query(sql: str) -> str:
        """Execute a write SQL query (INSERT, UPDATE, DELETE).

        USE WITH CAUTION. This modifies the live database.

        Args:
            sql: The SQL query (INSERT, UPDATE, DELETE only).
        """
        stripped = sql.strip().rstrip(";").strip()
        first_word = stripped.split()[0].upper() if stripped else ""
        if first_word not in ("INSERT", "UPDATE", "DELETE"):
            return "Error: only INSERT, UPDATE, and DELETE queries are allowed. Use run_query for reads."

        dangerous = re.compile(
            r'\b(DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b',
            re.IGNORECASE,
        )
        if dangerous.search(stripped):
            return "Error: query contains disallowed DDL keywords."

        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(stripped)
            conn.commit()
            return f"OK — {cursor.rowcount} row(s) affected."
        finally:
            conn.close()
