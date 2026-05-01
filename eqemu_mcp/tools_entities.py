"""Tools for working with NPCs, items, spawns, zones, loot, merchants, and tasks."""

from mcp.server.fastmcp import FastMCP

from .helpers import db_conn, sanitize_table_name


def register(mcp: FastMCP) -> None:
    """Read-only entity lookup tools."""

    # ---- NPCs ----

    @mcp.tool()
    def search_npcs(
        name: str = "",
        zone: str = "",
        min_level: int = 0,
        max_level: int = 255,
        limit: int = 50,
    ) -> str:
        """Search NPCs by name, zone, or level range.

        Args:
            name: Name substring filter (use _ for spaces).
            zone: Zone short name to filter spawns.
            min_level: Minimum level.
            max_level: Maximum level.
            limit: Max results (default 50).
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            if zone:
                cursor.execute(
                    """SELECT DISTINCT n.id, n.name, n.level, n.race, n.class, n.hp,
                              n.loottable_id, n.npc_faction_id
                       FROM npc_types n
                       JOIN spawnentry se ON se.npcID = n.id
                       JOIN spawn2 s2 ON s2.spawngroupID = se.spawngroupID
                       WHERE s2.zone = %s AND n.level BETWEEN %s AND %s
                       AND n.name LIKE %s
                       ORDER BY n.level, n.name LIMIT %s""",
                    (zone, min_level, max_level, f"%{name}%", limit),
                )
            else:
                cursor.execute(
                    """SELECT id, name, level, race, class, hp,
                              loottable_id, npc_faction_id
                       FROM npc_types
                       WHERE level BETWEEN %s AND %s AND name LIKE %s
                       ORDER BY level, name LIMIT %s""",
                    (min_level, max_level, f"%{name}%", limit),
                )
            rows = cursor.fetchall()
            if not rows:
                return "No NPCs found."
            lines = [f"{'ID':<8} {'Name':<35} {'Lvl':<5} {'Race':<6} {'Class':<6} {'HP':<10} {'Loot':<8} {'Faction'}"]
            lines.append("-" * 95)
            for r in rows:
                lines.append(f"{r[0]:<8} {r[1]:<35} {r[2]:<5} {r[3]:<6} {r[4]:<6} {r[5]:<10} {r[6]:<8} {r[7]}")
            return "\n".join(lines)
        finally:
            conn.close()

    @mcp.tool()
    def get_npc(npc_id: int) -> str:
        """Get full details for an NPC by ID.

        Args:
            npc_id: The npc_types.id value.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM npc_types WHERE id = %s", (npc_id,))
            row = cursor.fetchone()
            if not row:
                return f"NPC {npc_id} not found."
            lines = [f"NPC: {row['name']} (ID: {npc_id})", "-" * 50]
            for k, v in row.items():
                if v is not None and v != 0 and v != "" and v != "0":
                    lines.append(f"  {k}: {v}")

            # Also show spawn locations
            cursor.execute(
                """SELECT s2.zone, s2.x, s2.y, s2.z, s2.respawntime, sg.name as spawngroup_name
                   FROM spawnentry se
                   JOIN spawn2 s2 ON s2.spawngroupID = se.spawngroupID
                   JOIN spawngroup sg ON sg.id = se.spawngroupID
                   WHERE se.npcID = %s LIMIT 20""",
                (npc_id,),
            )
            spawns = cursor.fetchall()
            if spawns:
                lines.append(f"\nSpawn locations ({len(spawns)}):")
                for s in spawns:
                    lines.append(f"  {s['zone']}: ({s['x']:.1f}, {s['y']:.1f}, {s['z']:.1f}) respawn={s['respawntime']}s group={s['spawngroup_name']}")

            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Items ----

    @mcp.tool()
    def search_items(
        name: str = "",
        item_type: int = -1,
        min_level: int = 0,
        max_level: int = 255,
        limit: int = 50,
    ) -> str:
        """Search items by name, type, or required level.

        Args:
            name: Name substring filter.
            item_type: Item type ID (-1 for all).
            min_level: Min required level.
            max_level: Max required level.
            limit: Max results.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            params: list = []
            where_parts = ["name LIKE %s"]
            params.append(f"%{name}%")

            if item_type >= 0:
                where_parts.append("itemtype = %s")
                params.append(item_type)
            if min_level > 0:
                where_parts.append("reqlevel >= %s")
                params.append(min_level)
            if max_level < 255:
                where_parts.append("reqlevel <= %s")
                params.append(max_level)

            params.append(limit)
            cursor.execute(
                f"SELECT id, name, itemtype, reqlevel, classes, races, ac, hp, mana "
                f"FROM items WHERE {' AND '.join(where_parts)} ORDER BY reqlevel, name LIMIT %s",
                params,
            )
            rows = cursor.fetchall()
            if not rows:
                return "No items found."
            lines = [f"{'ID':<8} {'Name':<40} {'Type':<6} {'Lvl':<5} {'AC':<5} {'HP':<6} {'Mana':<6}"]
            lines.append("-" * 80)
            for r in rows:
                lines.append(f"{r[0]:<8} {r[1]:<40} {r[2]:<6} {r[3]:<5} {r[4]:<5} {r[5]:<6} {r[6]:<6}")
            return "\n".join(lines)
        finally:
            conn.close()

    @mcp.tool()
    def get_item(item_id: int) -> str:
        """Get full details for an item by ID.

        Args:
            item_id: The items.id value.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM items WHERE id = %s", (item_id,))
            row = cursor.fetchone()
            if not row:
                return f"Item {item_id} not found."
            lines = [f"Item: {row['Name']} (ID: {item_id})", "-" * 50]
            for k, v in row.items():
                if v is not None and v != 0 and v != "" and v != "0":
                    lines.append(f"  {k}: {v}")
            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Spawns ----

    @mcp.tool()
    def get_zone_spawns(zone: str, limit: int = 100) -> str:
        """Get all spawn points in a zone with their NPCs.

        Args:
            zone: Zone short name.
            limit: Max results (default 100).
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT s2.id, sg.name, n.id, n.name, n.level, se.chance,
                          s2.x, s2.y, s2.z, s2.respawntime
                   FROM spawn2 s2
                   JOIN spawngroup sg ON sg.id = s2.spawngroupID
                   JOIN spawnentry se ON se.spawngroupID = s2.spawngroupID
                   JOIN npc_types n ON n.id = se.npcID
                   WHERE s2.zone = %s
                   ORDER BY n.level, n.name LIMIT %s""",
                (zone, limit),
            )
            rows = cursor.fetchall()
            if not rows:
                return f"No spawns found in zone '{zone}'."
            lines = [f"{'S2ID':<8} {'Group':<30} {'NPCID':<8} {'NPC Name':<30} {'Lvl':<5} {'%':<5} {'Respawn'}"]
            lines.append("-" * 100)
            for r in rows:
                lines.append(
                    f"{r[0]:<8} {r[1]:<30} {r[2]:<8} {r[3]:<30} {r[4]:<5} {r[5]:<5} {r[9]}s"
                )
            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Loot ----

    @mcp.tool()
    def get_npc_loot(npc_id: int) -> str:
        """Get the full loot chain for an NPC: loottable -> lootdrop -> items.

        Args:
            npc_id: NPC type ID.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, loottable_id FROM npc_types WHERE id = %s", (npc_id,))
            npc = cursor.fetchone()
            if not npc:
                return f"NPC {npc_id} not found."
            if not npc[1]:
                return f"{npc[0]} has no loottable assigned."

            cursor.execute(
                """SELECT lt.id, lt.name, lte.lootdrop_id, ld.name as drop_name,
                          lte.multiplier, lte.probability,
                          lde.item_id, i.Name as item_name, lde.chance, lde.min_amount, lde.max_amount
                   FROM loottable lt
                   JOIN loottable_entries lte ON lte.loottable_id = lt.id
                   JOIN lootdrop ld ON ld.id = lte.lootdrop_id
                   JOIN lootdrop_entries lde ON lde.lootdrop_id = ld.id
                   JOIN items i ON i.id = lde.item_id
                   WHERE lt.id = %s
                   ORDER BY ld.name, lde.chance DESC""",
                (npc[1],),
            )
            rows = cursor.fetchall()
            if not rows:
                return f"{npc[0]} loottable {npc[1]} has no loot entries."

            lines = [f"Loot for {npc[0]} (NPC {npc_id}) — Loottable: {npc[1]}", "-" * 80]
            current_drop = None
            for r in rows:
                drop_name = r[3]
                if drop_name != current_drop:
                    current_drop = drop_name
                    lines.append(f"\n  Drop: {drop_name} (ID: {r[2]}) mult={r[4]} prob={r[5]}%")
                lines.append(f"    [{r[6]}] {r[7]:<40} chance={r[8]}% qty={r[9]}-{r[10]}")
            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Merchants ----

    @mcp.tool()
    def get_merchant_items(merchant_id: int) -> str:
        """Get items sold by a merchant.

        Args:
            merchant_id: The merchant list ID (npc_types.merchant_id).
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT ml.slot, ml.item, i.Name, i.price, i.itemtype, i.reqlevel
                   FROM merchantlist ml
                   JOIN items i ON i.id = ml.item
                   WHERE ml.merchantid = %s
                   ORDER BY ml.slot""",
                (merchant_id,),
            )
            rows = cursor.fetchall()
            if not rows:
                return f"No items found for merchant {merchant_id}."
            lines = [f"Merchant {merchant_id}: {len(rows)} item(s)"]
            lines.append(f"{'Slot':<6} {'ItemID':<8} {'Name':<40} {'Price':<10} {'ReqLvl'}")
            lines.append("-" * 75)
            for r in rows:
                lines.append(f"{r[0]:<6} {r[1]:<8} {r[2]:<40} {r[3]:<10} {r[5]}")
            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Zones ----

    @mcp.tool()
    def search_zones(filter: str = "", expansion: int = -1) -> str:
        """Search zones by name or expansion.

        Args:
            filter: Substring filter on short_name or long_name.
            expansion: Expansion number (-1 for all).
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            params: list = []
            where_parts = []
            if filter:
                where_parts.append("(short_name LIKE %s OR long_name LIKE %s)")
                params.extend([f"%{filter}%", f"%{filter}%"])
            if expansion >= 0:
                where_parts.append("expansion = %s")
                params.append(expansion)

            where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            cursor.execute(
                f"SELECT zoneidnumber, short_name, long_name, expansion, min_level, max_level "
                f"FROM zone {where} ORDER BY short_name LIMIT 100",
                params,
            )
            rows = cursor.fetchall()
            if not rows:
                return "No zones found."
            lines = [f"{'ID':<6} {'Short Name':<25} {'Long Name':<45} {'Exp':<5} {'MinLvl':<7} {'MaxLvl'}"]
            lines.append("-" * 100)
            for r in rows:
                lines.append(f"{r[0]:<6} {r[1]:<25} {r[2]:<45} {r[3]:<5} {r[4]:<7} {r[5]}")
            return "\n".join(lines)
        finally:
            conn.close()

    @mcp.tool()
    def get_zone_info(zone: str) -> str:
        """Get detailed info about a zone including spawn/NPC counts.

        Args:
            zone: Zone short name.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM zone WHERE short_name = %s", (zone,))
            row = cursor.fetchone()
            if not row:
                return f"Zone '{zone}' not found."

            lines = [f"Zone: {row['long_name']} ({zone})", "-" * 50]
            for k, v in row.items():
                if v is not None and v != 0 and v != "":
                    lines.append(f"  {k}: {v}")

            # Counts
            cursor.execute("SELECT COUNT(*) FROM spawn2 WHERE zone = %s", (zone,))
            spawn_count = cursor.fetchone()["COUNT(*)"]
            cursor.execute(
                """SELECT COUNT(DISTINCT se.npcID) FROM spawn2 s2
                   JOIN spawnentry se ON se.spawngroupID = s2.spawngroupID
                   WHERE s2.zone = %s""",
                (zone,),
            )
            npc_count = cursor.fetchone()["COUNT(DISTINCT se.npcID)"]
            cursor.execute("SELECT COUNT(*) FROM doors WHERE zone = %s", (zone,))
            door_count = cursor.fetchone()["COUNT(*)"]

            lines.append(f"\n  Spawn points: {spawn_count}")
            lines.append(f"  Unique NPCs: {npc_count}")
            lines.append(f"  Doors: {door_count}")

            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Tasks ----

    @mcp.tool()
    def search_tasks(name: str = "", limit: int = 50) -> str:
        """Search tasks by name.

        Args:
            name: Name substring filter.
            limit: Max results.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, type, title, description, reward_text
                   FROM tasks WHERE title LIKE %s ORDER BY id LIMIT %s""",
                (f"%{name}%", limit),
            )
            rows = cursor.fetchall()
            if not rows:
                return "No tasks found."
            lines = [f"{'ID':<8} {'Type':<6} {'Title':<40} {'Description'}"]
            lines.append("-" * 100)
            for r in rows:
                desc = (r[3] or "")[:50]
                lines.append(f"{r[0]:<8} {r[1]:<6} {r[2]:<40} {desc}")
            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Factions ----

    @mcp.tool()
    def search_factions(name: str = "", limit: int = 50) -> str:
        """Search factions by name.

        Args:
            name: Name substring filter.
            limit: Max results.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, base FROM faction_list WHERE name LIKE %s ORDER BY name LIMIT %s",
                (f"%{name}%", limit),
            )
            rows = cursor.fetchall()
            if not rows:
                return "No factions found."
            lines = [f"{'ID':<8} {'Name':<50} {'Base'}"]
            lines.append("-" * 65)
            for r in rows:
                lines.append(f"{r[0]:<8} {r[1]:<50} {r[2]}")
            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Spells ----

    @mcp.tool()
    def search_spells(name: str = "", limit: int = 50) -> str:
        """Search spells by name.

        Args:
            name: Name substring filter.
            limit: Max results.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, name, classes1, cast_time, mana, resisttype,
                          effectid1, effect_base_value1
                   FROM spells_new WHERE name LIKE %s ORDER BY id LIMIT %s""",
                (f"%{name}%", limit),
            )
            rows = cursor.fetchall()
            if not rows:
                return "No spells found."
            lines = [f"{'ID':<8} {'Name':<40} {'Class':<7} {'Cast':<6} {'Mana':<6} {'Resist':<8} {'Effect':<8} {'Base'}"]
            lines.append("-" * 95)
            for r in rows:
                lines.append(
                    f"{r[0]:<8} {r[1]:<40} {r[2]:<7} {r[3]:<6} {r[4]:<6} {r[5]:<8} {r[6]:<8} {r[7]}"
                )
            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Accounts / Characters ----

    @mcp.tool()
    def list_characters(account_name: str = "", limit: int = 50) -> str:
        """List characters, optionally filtered by account.

        Args:
            account_name: Optional account name filter.
            limit: Max results.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            if account_name:
                cursor.execute(
                    """SELECT c.id, c.name, c.level, c.class, c.race, a.name as acct
                       FROM character_data c
                       JOIN account a ON a.id = c.account_id
                       WHERE a.name LIKE %s
                       ORDER BY c.level DESC LIMIT %s""",
                    (f"%{account_name}%", limit),
                )
            else:
                cursor.execute(
                    """SELECT c.id, c.name, c.level, c.class, c.race, a.name as acct
                       FROM character_data c
                       JOIN account a ON a.id = c.account_id
                       ORDER BY c.level DESC LIMIT %s""",
                    (limit,),
                )
            rows = cursor.fetchall()
            if not rows:
                return "No characters found."
            lines = [f"{'ID':<8} {'Name':<25} {'Level':<6} {'Class':<7} {'Race':<6} {'Account'}"]
            lines.append("-" * 65)
            for r in rows:
                lines.append(f"{r[0]:<8} {r[1]:<25} {r[2]:<6} {r[3]:<7} {r[4]:<6} {r[5]}")
            return "\n".join(lines)
        finally:
            conn.close()
