"""Write-mode tools for creating/modifying NPCs, spawns, loot, items, etc."""

from mcp.server.fastmcp import FastMCP

from .helpers import db_conn


def register_write(mcp: FastMCP) -> None:

    # ---- NPC Management ----

    @mcp.tool()
    def create_npc(
        name: str,
        level: int,
        race: int,
        npc_class: int,
        hp: int = 0,
        loottable_id: int = 0,
        npc_faction_id: int = 0,
        merchant_id: int = 0,
        bodytype: int = 1,
        gender: int = 2,
    ) -> str:
        """Create a new NPC in the npc_types table.

        Args:
            name: NPC name (use _ for spaces).
            level: NPC level.
            race: Race ID.
            npc_class: Class ID.
            hp: Hit points (0 = auto-calculated).
            loottable_id: Loottable ID (0 = no loot).
            npc_faction_id: Faction ID (0 = none).
            merchant_id: Merchant list ID (0 = not a merchant).
            bodytype: Body type (default 1 = Humanoid).
            gender: Gender (0=Male, 1=Female, 2=Neuter).
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO npc_types (name, level, race, class, hp,
                   loottable_id, npc_faction_id, merchant_id, bodytype, gender)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (name, level, race, npc_class, hp, loottable_id, npc_faction_id, merchant_id, bodytype, gender),
            )
            conn.commit()
            npc_id = cursor.lastrowid
            return f"Created NPC '{name}' with ID {npc_id}"
        finally:
            conn.close()

    @mcp.tool()
    def update_npc(npc_id: int, **fields) -> str:
        """Update fields on an existing NPC.

        Args:
            npc_id: NPC type ID.
            **fields: Column=value pairs, e.g. level=50, hp=5000, name='New_Name'.
        """
        if not fields:
            return "Error: no fields provided to update."

        allowed = {
            "name", "level", "race", "class", "hp", "mana", "gender",
            "texture", "helmtexture", "size", "loottable_id", "merchant_id",
            "npc_spells_id", "npc_faction_id", "mindmg", "maxdmg", "attack_speed",
            "special_abilities", "bodytype", "see_invis", "see_hide",
            "see_improved_hide", "trackable", "runspeed", "walkspeed",
            "aggroradius", "assistradius", "maxlevel",
        }

        invalid = set(fields.keys()) - allowed
        if invalid:
            return f"Error: fields not allowed: {invalid}\nAllowed: {sorted(allowed)}"

        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM npc_types WHERE id = %s", (npc_id,))
            if not cursor.fetchone():
                return f"NPC {npc_id} not found."

            set_clause = ", ".join(f"`{k}` = %s" for k in fields)
            cursor.execute(
                f"UPDATE npc_types SET {set_clause} WHERE id = %s",
                (*fields.values(), npc_id),
            )
            conn.commit()
            return f"Updated NPC {npc_id}: {fields}"
        finally:
            conn.close()

    # ---- Spawn Management ----

    @mcp.tool()
    def create_spawn(
        zone: str,
        npc_id: int,
        x: float,
        y: float,
        z: float,
        heading: float = 0.0,
        respawntime: int = 640,
        spawngroup_name: str = "",
    ) -> str:
        """Create a new spawn point for an NPC in a zone.

        Creates a spawngroup, spawnentry, and spawn2 record.

        Args:
            zone: Zone short name.
            npc_id: NPC type ID.
            x: X coordinate.
            y: Y coordinate.
            z: Z coordinate.
            heading: Heading (default 0).
            respawntime: Respawn time in seconds (default 640).
            spawngroup_name: Optional name (auto-generated if empty).
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()

            # Verify NPC exists
            cursor.execute("SELECT name FROM npc_types WHERE id = %s", (npc_id,))
            npc = cursor.fetchone()
            if not npc:
                return f"NPC {npc_id} not found."

            if not spawngroup_name:
                spawngroup_name = f"{zone}_{npc[0]}_{npc_id}"

            # Create spawngroup
            cursor.execute(
                "INSERT INTO spawngroup (name, spawn_limit, dist) VALUES (%s, 0, 0)",
                (spawngroup_name,),
            )
            sg_id = cursor.lastrowid

            # Create spawnentry
            cursor.execute(
                "INSERT INTO spawnentry (spawngroupID, npcID, chance) VALUES (%s, %s, 100)",
                (sg_id, npc_id),
            )

            # Create spawn2
            cursor.execute(
                """INSERT INTO spawn2 (spawngroupID, zone, x, y, z, heading, respawntime)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (sg_id, zone, x, y, z, heading, respawntime),
            )
            s2_id = cursor.lastrowid
            conn.commit()

            return (
                f"Created spawn for {npc[0]} in {zone}:\n"
                f"  spawn2.id = {s2_id}\n"
                f"  spawngroup.id = {sg_id}\n"
                f"  Location: ({x}, {y}, {z}) heading={heading}\n"
                f"  Respawn: {respawntime}s\n"
                f"Note: use #repop in-game to see changes."
            )
        finally:
            conn.close()

    @mcp.tool()
    def delete_spawn(spawn2_id: int) -> str:
        """Delete a spawn2 entry and its orphaned spawngroup/spawnentry if no other spawn2 uses it.

        Args:
            spawn2_id: The spawn2.id value.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT spawngroupID, zone FROM spawn2 WHERE id = %s", (spawn2_id,))
            row = cursor.fetchone()
            if not row:
                return f"spawn2 {spawn2_id} not found."

            sg_id = row[0]
            cursor.execute("DELETE FROM spawn2 WHERE id = %s", (spawn2_id,))

            # Check if spawngroup is now orphaned
            cursor.execute("SELECT COUNT(*) FROM spawn2 WHERE spawngroupID = %s", (sg_id,))
            remaining = cursor.fetchone()[0]
            if remaining == 0:
                cursor.execute("DELETE FROM spawnentry WHERE spawngroupID = %s", (sg_id,))
                cursor.execute("DELETE FROM spawngroup WHERE id = %s", (sg_id,))

            conn.commit()
            return f"Deleted spawn2 {spawn2_id} from {row[1]}. Spawngroup {sg_id} {'also cleaned up' if remaining == 0 else 'still has other spawn2 entries'}."
        finally:
            conn.close()

    # ---- Loot Management ----

    @mcp.tool()
    def add_loot_to_npc(
        npc_id: int,
        item_id: int,
        chance: float = 100.0,
        min_amount: int = 1,
        max_amount: int = 1,
    ) -> str:
        """Add an item to an NPC's loot table. Creates the loot chain if needed.

        Args:
            npc_id: NPC type ID.
            item_id: Item ID to add.
            chance: Drop chance percentage (default 100).
            min_amount: Minimum quantity (default 1).
            max_amount: Maximum quantity (default 1).
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT name, loottable_id FROM npc_types WHERE id = %s", (npc_id,))
            npc = cursor.fetchone()
            if not npc:
                return f"NPC {npc_id} not found."

            cursor.execute("SELECT Name FROM items WHERE id = %s", (item_id,))
            item = cursor.fetchone()
            if not item:
                return f"Item {item_id} not found."

            lt_id = npc[1]
            if not lt_id:
                # Create loottable
                cursor.execute(
                    "INSERT INTO loottable (name) VALUES (%s)",
                    (f"{npc[0]}_loot",),
                )
                lt_id = cursor.lastrowid
                cursor.execute(
                    "UPDATE npc_types SET loottable_id = %s WHERE id = %s",
                    (lt_id, npc_id),
                )

            # Create lootdrop
            cursor.execute(
                "INSERT INTO lootdrop (name) VALUES (%s)",
                (f"{npc[0]}_{item[0]}_drop",),
            )
            ld_id = cursor.lastrowid

            # Create loottable_entry
            cursor.execute(
                "INSERT INTO loottable_entries (loottable_id, lootdrop_id, multiplier, probability) VALUES (%s, %s, 1, 100)",
                (lt_id, ld_id),
            )

            # Create lootdrop_entry
            cursor.execute(
                """INSERT INTO lootdrop_entries (lootdrop_id, item_id, item_charges, equip_item,
                   chance, min_amount, max_amount) VALUES (%s, %s, 1, 1, %s, %s, %s)""",
                (ld_id, item_id, chance, min_amount, max_amount),
            )
            conn.commit()

            return (
                f"Added {item[0]} to {npc[0]}'s loot:\n"
                f"  loottable_id = {lt_id}\n"
                f"  lootdrop_id = {ld_id}\n"
                f"  chance = {chance}%, qty = {min_amount}-{max_amount}\n"
                f"Note: use #repop or rezone to see changes."
            )
        finally:
            conn.close()

    # ---- Merchant Management ----

    @mcp.tool()
    def add_merchant_item(merchant_id: int, item_id: int, slot: int = 0) -> str:
        """Add an item to a merchant's inventory.

        Args:
            merchant_id: Merchant list ID.
            item_id: Item ID.
            slot: Slot number (0 = auto-assign next available).
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT Name FROM items WHERE id = %s", (item_id,))
            item = cursor.fetchone()
            if not item:
                return f"Item {item_id} not found."

            if slot == 0:
                cursor.execute(
                    "SELECT MAX(slot) FROM merchantlist WHERE merchantid = %s",
                    (merchant_id,),
                )
                max_slot = cursor.fetchone()[0]
                slot = (max_slot or 0) + 1

            cursor.execute(
                "INSERT INTO merchantlist (merchantid, slot, item) VALUES (%s, %s, %s)",
                (merchant_id, slot, item_id),
            )
            conn.commit()
            return f"Added {item[0]} (ID: {item_id}) to merchant {merchant_id} at slot {slot}"
        finally:
            conn.close()

    @mcp.tool()
    def remove_merchant_item(merchant_id: int, item_id: int) -> str:
        """Remove an item from a merchant's inventory.

        Args:
            merchant_id: Merchant list ID.
            item_id: Item ID to remove.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM merchantlist WHERE merchantid = %s AND item = %s",
                (merchant_id, item_id),
            )
            conn.commit()
            return f"Removed item {item_id} from merchant {merchant_id}. Rows affected: {cursor.rowcount}"
        finally:
            conn.close()

    # ---- Data Buckets ----

    @mcp.tool()
    def get_data_buckets(key_filter: str, limit: int = 50) -> str:
        """Search data buckets by key.

        Args:
            key_filter: Key substring filter.
            limit: Max results.
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, `key`, value, expires FROM data_buckets WHERE `key` LIKE %s ORDER BY id DESC LIMIT %s",
                (f"%{key_filter}%", limit),
            )
            rows = cursor.fetchall()
            if not rows:
                return "No data buckets found."
            lines = [f"{'ID':<8} {'Key':<50} {'Value':<30} {'Expires'}"]
            lines.append("-" * 95)
            for r in rows:
                lines.append(f"{r[0]:<8} {r[1]:<50} {str(r[2])[:30]:<30} {r[3] or 'never'}")
            return "\n".join(lines)
        finally:
            conn.close()

    @mcp.tool()
    def set_data_bucket(key: str, value: str, expires: int = 0) -> str:
        """Set a data bucket value.

        Args:
            key: Bucket key.
            value: Bucket value.
            expires: Unix timestamp when it expires (0 = never).
        """
        conn = db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM data_buckets WHERE `key` = %s",
                (key,),
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    "UPDATE data_buckets SET value = %s, expires = %s WHERE `key` = %s",
                    (value, expires, key),
                )
            else:
                cursor.execute(
                    "INSERT INTO data_buckets (`key`, value, expires) VALUES (%s, %s, %s)",
                    (key, value, expires),
                )
            conn.commit()
            return f"Set data_bucket '{key}' = '{value}'"
        finally:
            conn.close()
