"""Extended lookup tools for deeper inspection of game data.

Covers: character details, account investigation, tradeskill recipes,
doors, grids/pathing, spell details, NPC factions, task details,
and pre-built "handy queries" from the EQEmu docs.
"""

from mcp.server.fastmcp import FastMCP

from .helpers import db_conn


def register(mcp: FastMCP) -> None:

    # ---- Character deep-dive ----

    @mcp.tool()
    def get_character(name: str) -> str:
        """Get detailed character info including inventory summary, AAs, skills, and zone.

        Args:
            name: Character name (exact or partial match).
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT c.*, a.name as account_name, a.status as account_status,
                          COALESCE((SELECT short_name FROM zone WHERE zoneidnumber = c.zone_id LIMIT 1), 'unknown') as zone_name,
                          FROM_UNIXTIME(c.last_login) as last_login_time
                   FROM character_data c
                   JOIN account a ON a.id = c.account_id
                   WHERE c.name LIKE %s LIMIT 1""",
                (f"%{name}%",),
            )
            row = cur.fetchone()
            if not row:
                return f"Character '{name}' not found."

            char_id = row["id"]
            lines = [
                f"Character: {row['name']} (ID: {char_id})",
                f"  Account: {row['account_name']} (status: {row['account_status']})",
                f"  Level: {row['level']}  Class: {row['class']}  Race: {row['race']}",
                f"  Zone: {row['zone_name']} (id: {row['zone_id']}, instance: {row['zone_instance']})",
                f"  Position: ({row['x']:.1f}, {row['y']:.1f}, {row['z']:.1f})",
                f"  HP: {row['cur_hp']}  Mana: {row['mana']}",
                f"  STR: {row.get('str', 0)} STA: {row.get('sta', 0)} DEX: {row.get('dex', 0)} AGI: {row.get('agi', 0)} INT: {row.get('int', 0)} WIS: {row.get('wis', 0)} CHA: {row.get('cha', 0)}",
                f"  Platinum: {row.get('platinum', 0)} Gold: {row.get('gold', 0)} Silver: {row.get('silver', 0)} Copper: {row.get('copper', 0)}",
                f"  Bank Plat: {row.get('platinum_bank', 0)}",
                f"  Last Login: {row.get('last_login_time', 'never')}",
            ]

            # AA count
            cur.execute(
                "SELECT COUNT(*) as cnt, COALESCE(SUM(aa_value), 0) as total FROM character_alternate_abilities WHERE id = %s",
                (char_id,),
            )
            aa = cur.fetchone()
            lines.append(f"  AAs: {aa['total']} points across {aa['cnt']} abilities")

            # Inventory item count
            cur.execute(
                "SELECT COUNT(*) as cnt FROM inventory WHERE character_id = %s",
                (char_id,),
            )
            inv = cur.fetchone()
            lines.append(f"  Inventory slots used: {inv['cnt']}")

            # Guild
            cur.execute(
                """SELECT g.name as guild_name, gm.rank as guild_rank
                   FROM guild_members gm
                   JOIN guilds g ON g.id = gm.guild_id
                   WHERE gm.char_id = %s LIMIT 1""",
                (char_id,),
            )
            guild = cur.fetchone()
            if guild:
                lines.append(f"  Guild: {guild['guild_name']} (rank: {guild['guild_rank']})")

            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Account investigation ----

    @mcp.tool()
    def get_account_info(account_name: str = "", character_name: str = "") -> str:
        """Look up account details and all associated characters/IPs.

        Useful for admin investigation. Provide either account_name or character_name.

        Args:
            account_name: Account name to look up.
            character_name: Character name to find the account for.
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)
            if character_name:
                cur.execute(
                    """SELECT a.* FROM account a
                       JOIN character_data c ON c.account_id = a.id
                       WHERE c.name LIKE %s LIMIT 1""",
                    (f"%{character_name}%",),
                )
            elif account_name:
                cur.execute("SELECT * FROM account WHERE name LIKE %s LIMIT 1", (f"%{account_name}%",))
            else:
                return "Provide either account_name or character_name."

            acct = cur.fetchone()
            if not acct:
                return "Account not found."

            acct_id = acct["id"]
            lines = [
                f"Account: {acct['name']} (ID: {acct_id})",
                f"  Status: {acct['status']}",
                f"  Characters:",
            ]

            cur.execute(
                """SELECT id, name, level, class, race, zone_id,
                          FROM_UNIXTIME(last_login) as last_login
                   FROM character_data WHERE account_id = %s ORDER BY level DESC""",
                (acct_id,),
            )
            for c in cur.fetchall():
                lines.append(f"    {c['name']} — Level {c['level']} (Class {c['class']}, Race {c['race']}) — Last login: {c['last_login']}")

            # IP history
            cur.execute(
                """SELECT ip, FROM_UNIXTIME(lastused) as last_used
                   FROM account_ip WHERE accid = %s ORDER BY lastused DESC LIMIT 10""",
                (acct_id,),
            )
            ips = cur.fetchall()
            if ips:
                lines.append(f"  Recent IPs ({len(ips)}):")
                for ip in ips:
                    lines.append(f"    {ip['ip']} — {ip['last_used']}")

            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Online characters ----

    @mcp.tool()
    def get_online_characters(minutes: int = 10) -> str:
        """List characters that are likely online (logged in recently).

        Args:
            minutes: How many minutes back to check (default 10).
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT
                       c.name, c.level, c.class, c.race,
                       COALESCE((SELECT short_name FROM zone WHERE zoneidnumber = c.zone_id LIMIT 1), 'unknown') as zone_name,
                       a.name as account_name,
                       COALESCE((SELECT g.name FROM guilds g JOIN guild_members gm ON g.id = gm.guild_id WHERE gm.char_id = c.id LIMIT 1), '') as guild_name,
                       FROM_UNIXTIME(c.last_login) as last_login
                   FROM character_data c
                   JOIN account a ON a.id = c.account_id
                   WHERE c.last_login > (UNIX_TIMESTAMP() - %s)
                   ORDER BY c.name""",
                (minutes * 60,),
            )
            rows = cur.fetchall()
            if not rows:
                return f"No characters logged in within the past {minutes} minutes."

            lines = [f"Online characters (within {minutes} min): {len(rows)}"]
            lines.append(f"{'Name':<20} {'Lvl':<5} {'Class':<7} {'Zone':<20} {'Guild':<20} {'Account'}")
            lines.append("-" * 90)
            for r in rows:
                lines.append(
                    f"{r['name']:<20} {r['level']:<5} {r['class']:<7} "
                    f"{r['zone_name']:<20} {r['guild_name']:<20} {r['account_name']}"
                )
            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Tradeskill recipes ----

    @mcp.tool()
    def search_recipes(name: str = "", item_id: int = 0, skill: int = -1, limit: int = 50) -> str:
        """Search tradeskill recipes by name, component item, or tradeskill type.

        Args:
            name: Recipe name filter.
            item_id: Find recipes that use or produce this item ID.
            skill: Tradeskill skill ID (e.g. 59=Blacksmithing, 60=Brewing, 63=Tailoring, 56=Baking).
            limit: Max results.
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)
            if item_id:
                cur.execute(
                    """SELECT DISTINCT r.id, r.name, r.tradeskill, r.trivial, r.must_learn
                       FROM tradeskill_recipe r
                       JOIN tradeskill_recipe_entries e ON e.recipe_id = r.id
                       WHERE e.item_id = %s
                       ORDER BY r.name LIMIT %s""",
                    (item_id, limit),
                )
            elif name:
                where = "r.name LIKE %s"
                params = [f"%{name}%"]
                if skill >= 0:
                    where += " AND r.tradeskill = %s"
                    params.append(skill)
                params.append(limit)
                cur.execute(
                    f"""SELECT r.id, r.name, r.tradeskill, r.trivial, r.must_learn
                        FROM tradeskill_recipe r WHERE {where}
                        ORDER BY r.name LIMIT %s""",
                    params,
                )
            else:
                return "Provide name or item_id to search recipes."

            rows = cur.fetchall()
            if not rows:
                return "No recipes found."

            lines = [f"{'ID':<8} {'Name':<45} {'Skill':<8} {'Trivial':<8} {'Learn'}"]
            lines.append("-" * 80)
            for r in rows:
                lines.append(f"{r['id']:<8} {r['name']:<45} {r['tradeskill']:<8} {r['trivial']:<8} {r['must_learn']}")
            return "\n".join(lines)
        finally:
            conn.close()

    @mcp.tool()
    def get_recipe(recipe_id: int) -> str:
        """Get full recipe details including all components and results.

        Args:
            recipe_id: The tradeskill_recipe.id value.
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM tradeskill_recipe WHERE id = %s", (recipe_id,))
            recipe = cur.fetchone()
            if not recipe:
                return f"Recipe {recipe_id} not found."

            lines = [
                f"Recipe: {recipe['name']} (ID: {recipe_id})",
                f"  Tradeskill: {recipe['tradeskill']}  Trivial: {recipe['trivial']}",
                f"  Must Learn: {recipe['must_learn']}  Learned: {recipe.get('learned_by_item_id', 0)}",
            ]

            cur.execute(
                """SELECT e.*, i.Name as item_name
                   FROM tradeskill_recipe_entries e
                   LEFT JOIN items i ON i.id = e.item_id
                   WHERE e.recipe_id = %s
                   ORDER BY e.iscontainer DESC, e.successcount DESC""",
                (recipe_id,),
            )
            entries = cur.fetchall()

            components = [e for e in entries if e.get("componentcount", 0) > 0]
            results_success = [e for e in entries if e.get("successcount", 0) > 0]
            results_fail = [e for e in entries if e.get("failcount", 0) > 0]
            containers = [e for e in entries if e.get("iscontainer", 0) > 0]

            if containers:
                lines.append("  Container:")
                for c in containers:
                    lines.append(f"    {c.get('item_name', '?')} (ID: {c['item_id']})")

            if components:
                lines.append("  Components:")
                for c in components:
                    lines.append(f"    {c.get('item_name', '?')} (ID: {c['item_id']}) x{c['componentcount']}")

            if results_success:
                lines.append("  Success results:")
                for r in results_success:
                    lines.append(f"    {r.get('item_name', '?')} (ID: {r['item_id']}) x{r['successcount']}")

            if results_fail:
                lines.append("  Failure results:")
                for r in results_fail:
                    lines.append(f"    {r.get('item_name', '?')} (ID: {r['item_id']}) x{r['failcount']}")

            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Doors ----

    @mcp.tool()
    def get_zone_doors(zone: str, version: int = 0) -> str:
        """List all doors/objects in a zone.

        Args:
            zone: Zone short name (e.g. 'crushbone').
            version: Zone version (default 0).
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT id, doorid, name, pos_x, pos_y, pos_z, dest_zone,
                          dest_x, dest_y, dest_z, keyitem, lockpick, triggerdoor, triggertype
                   FROM doors WHERE zone = %s AND version = %s ORDER BY doorid""",
                (zone, version),
            )
            rows = cur.fetchall()
            if not rows:
                return f"No doors found in zone '{zone}' version {version}."

            lines = [f"Doors in {zone} v{version}: {len(rows)}"]
            for d in rows:
                dest = f" -> {d['dest_zone']}({d['dest_x']:.0f},{d['dest_y']:.0f},{d['dest_z']:.0f})" if d.get("dest_zone") else ""
                key = f" key={d['keyitem']}" if d.get("keyitem") else ""
                lock = f" lockpick={d['lockpick']}" if d.get("lockpick") else ""
                lines.append(f"  [{d['doorid']}] {d['name']} at ({d['pos_x']:.1f},{d['pos_y']:.1f},{d['pos_z']:.1f}){dest}{key}{lock}")
            return "\n".join(lines)
        finally:
            conn.close()

    # ---- NPC Grids / Pathing ----

    @mcp.tool()
    def get_npc_grid(zone: str, grid_id: int = 0, npc_name: str = "") -> str:
        """Get NPC patrol/wandering grid paths in a zone.

        Args:
            zone: Zone short name.
            grid_id: Specific grid ID to look up (0 for all grids in zone).
            npc_name: NPC name to find their grid.
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)

            if npc_name:
                # Find grid via spawn2 -> spawnentry -> npc_types
                cur.execute(
                    """SELECT DISTINCT s2.pathgrid, n.name, n.id as npc_id
                       FROM spawn2 s2
                       JOIN spawnentry se ON se.spawngroupID = s2.spawngroupID
                       JOIN npc_types n ON n.id = se.npcID
                       WHERE s2.zone = %s AND n.name LIKE %s AND s2.pathgrid > 0
                       LIMIT 10""",
                    (zone, f"%{npc_name}%"),
                )
                grids = cur.fetchall()
                if not grids:
                    return f"No grids found for NPC '{npc_name}' in {zone}."
                grid_ids = [g["pathgrid"] for g in grids]
                lines = [f"Grids for '{npc_name}' in {zone}:"]
                for g in grids:
                    lines.append(f"  NPC {g['name']} (ID: {g['npc_id']}) uses grid {g['pathgrid']}")
            elif grid_id > 0:
                grid_ids = [grid_id]
                lines = [f"Grid {grid_id} in {zone}:"]
            else:
                cur.execute(
                    "SELECT id, type, type2 FROM grid WHERE zoneid = (SELECT zoneidnumber FROM zone WHERE short_name = %s LIMIT 1) LIMIT 50",
                    (zone,),
                )
                rows = cur.fetchall()
                if not rows:
                    return f"No grids found in zone '{zone}'."
                lines = [f"Grids in {zone}: {len(rows)}"]
                for r in rows:
                    lines.append(f"  Grid {r['id']}: wander_type={r['type']} pause_type={r['type2']}")
                return "\n".join(lines)

            # Get grid entries (waypoints)
            for gid in grid_ids:
                cur.execute(
                    """SELECT ge.number, ge.x, ge.y, ge.z, ge.heading, ge.pause
                       FROM grid_entries ge
                       WHERE ge.gridid = %s AND ge.zoneid = (SELECT zoneidnumber FROM zone WHERE short_name = %s LIMIT 1)
                       ORDER BY ge.number""",
                    (gid, zone),
                )
                waypoints = cur.fetchall()
                lines.append(f"\n  Grid {gid} waypoints ({len(waypoints)}):")
                for wp in waypoints:
                    lines.append(
                        f"    WP {wp['number']}: ({wp['x']:.1f}, {wp['y']:.1f}, {wp['z']:.1f}) "
                        f"heading={wp['heading']:.0f} pause={wp['pause']}s"
                    )

            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Spell details ----

    @mcp.tool()
    def get_spell(spell_id: int) -> str:
        """Get full details for a spell by ID.

        Returns all spell fields including effects, targets, resists, durations, etc.

        Args:
            spell_id: The spells_new.id value.
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM spells_new WHERE id = %s", (spell_id,))
            row = cur.fetchone()
            if not row:
                return f"Spell {spell_id} not found."

            lines = [
                f"Spell: {row['name']} (ID: {spell_id})",
                f"  Mana: {row['mana']}  Cast Time: {row['cast_time']}ms  Recast: {row['recast_time']}ms",
                f"  Range: {row['range']}  AE Range: {row.get('aoerange', 0)}",
                f"  Duration: {row.get('buffduration', 0)} ticks  Resist Type: {row.get('resisttype', 0)}  Resist Diff: {row.get('ResistDiff', 0)}",
                f"  Target Type: {row.get('targettype', 0)}  Skill: {row.get('skill', 0)}",
                "",
                "  Effects:",
            ]

            for i in range(1, 13):
                eid = row.get(f"effectid{i}", 254)
                base = row.get(f"effect_base_value{i}", 0)
                limit_val = row.get(f"effect_limit_value{i}", 0)
                max_val = row.get(f"max{i}", 0)
                formula = row.get(f"formula{i}", 0)
                if eid != 254 and eid != 0:
                    lines.append(f"    Slot {i}: Effect={eid} Base={base} Limit={limit_val} Max={max_val} Formula={formula}")

            # Class usability
            class_names = [
                "WAR", "CLR", "PAL", "RNG", "SHD", "DRU", "MNK", "BRD",
                "ROG", "SHM", "NEC", "WIZ", "MAG", "ENC", "BST", "BER",
            ]
            usable_by = []
            for i, cls in enumerate(class_names, 1):
                level = row.get(f"classes{i}", 255)
                if level < 255:
                    usable_by.append(f"{cls}({level})")
            if usable_by:
                lines.append(f"\n  Usable by: {', '.join(usable_by)}")

            # Teleport info
            if row.get("teleport_zone"):
                lines.append(f"\n  Teleports to: {row['teleport_zone']} ({row.get('teleport_x', 0)}, {row.get('teleport_y', 0)}, {row.get('teleport_z', 0)})")

            return "\n".join(lines)
        finally:
            conn.close()

    # ---- NPC faction details ----

    @mcp.tool()
    def get_npc_faction(npc_id: int = 0, faction_id: int = 0) -> str:
        """Get the full faction setup for an NPC or inspect a faction list.

        Shows primary faction and all faction hits (positive and negative) when
        an NPC is killed.

        Args:
            npc_id: NPC ID to look up their faction setup.
            faction_id: Or look up a faction list directly by its ID.
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)

            if npc_id and not faction_id:
                cur.execute("SELECT npc_faction_id FROM npc_types WHERE id = %s", (npc_id,))
                row = cur.fetchone()
                if not row or not row["npc_faction_id"]:
                    return f"NPC {npc_id} has no faction assigned."
                faction_id = row["npc_faction_id"]

            if not faction_id:
                return "Provide npc_id or faction_id."

            cur.execute("SELECT * FROM npc_faction WHERE id = %s", (faction_id,))
            nf = cur.fetchone()
            if not nf:
                return f"Faction list {faction_id} not found."

            lines = [
                f"NPC Faction List: {nf['name']} (ID: {faction_id})",
                f"  Primary Faction: {nf['primaryfaction']}",
            ]

            # Get primary faction name
            if nf["primaryfaction"]:
                cur.execute("SELECT name FROM faction_list WHERE id = %s", (nf["primaryfaction"],))
                pf = cur.fetchone()
                if pf:
                    lines[-1] += f" ({pf['name']})"

            # Get all faction entries
            cur.execute(
                """SELECT nfe.faction_id, nfe.value, nfe.npc_value, nfe.temp,
                          fl.name as faction_name
                   FROM npc_faction_entries nfe
                   LEFT JOIN faction_list fl ON fl.id = nfe.faction_id
                   WHERE nfe.npc_faction_id = %s
                   ORDER BY nfe.value DESC""",
                (faction_id,),
            )
            entries = cur.fetchall()
            if entries:
                lines.append(f"\n  Faction hits on kill ({len(entries)}):")
                for e in entries:
                    sign = "+" if e["value"] > 0 else ""
                    lines.append(f"    {e.get('faction_name', '?')} (ID: {e['faction_id']}): {sign}{e['value']} (npc_value: {e['npc_value']})")

            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Task details ----

    @mcp.tool()
    def get_task(task_id: int) -> str:
        """Get full task details including activities and rewards.

        Args:
            task_id: The tasks.id value.
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
            task = cur.fetchone()
            if not task:
                return f"Task {task_id} not found."

            lines = [
                f"Task: {task['title']} (ID: {task_id})",
                f"  Type: {task['type']}  Duration: {task['duration']}",
                f"  Min Level: {task.get('minlevel', 0)}  Max Level: {task.get('maxlevel', 0)}",
                f"  Reward: {task.get('reward', '')}  Cash: {task.get('cashreward', 0)}cp  XP: {task.get('rewardmethod', 0)}",
            ]

            if task.get("description"):
                desc = task["description"][:200]
                lines.append(f"  Description: {desc}")

            # Activities
            cur.execute(
                """SELECT * FROM task_activities
                   WHERE taskid = %s ORDER BY activityid""",
                (task_id,),
            )
            activities = cur.fetchall()
            if activities:
                lines.append(f"\n  Activities ({len(activities)}):")
                for a in activities:
                    zone_info = f" zone={a.get('zone_ids', '')}" if a.get("zone_ids") else ""
                    lines.append(
                        f"    [{a['activityid']}] Type={a.get('activitytype', '?')} "
                        f"Goal={a.get('goalcount', 0)}{zone_info} "
                        f"Desc: {a.get('description_override', '')[:80]}"
                    )

            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Item search by stats ----

    @mcp.tool()
    def search_items_by_stat(
        stat: str,
        min_value: int = 1,
        item_type: int = -1,
        max_level: int = 255,
        limit: int = 50,
    ) -> str:
        """Search items by a specific stat value (e.g. find all items with high HP).

        Args:
            stat: Column name to search by, e.g. 'hp', 'mana', 'ac', 'damage',
                  'haste', 'heroic_str', 'attack', 'accuracy', 'regen', etc.
            min_value: Minimum value for the stat.
            item_type: Filter by item type (0=1HS, 1=2HS, 2=Piercing, etc. -1=all).
            max_level: Max required level.
            limit: Max results.
        """
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', stat):
            return "Invalid stat name."

        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)
            where = f"`{stat}` >= %s"
            params = [min_value]

            if item_type >= 0:
                where += " AND itemtype = %s"
                params.append(item_type)
            if max_level < 255:
                where += " AND reqlevel <= %s"
                params.append(max_level)

            params.append(limit)
            cur.execute(
                f"""SELECT id, Name, `{stat}`, reqlevel, itemtype, classes, races
                    FROM items WHERE {where}
                    ORDER BY `{stat}` DESC LIMIT %s""",
                params,
            )
            rows = cur.fetchall()
            if not rows:
                return f"No items found with {stat} >= {min_value}."

            lines = [f"{'ID':<8} {'Name':<45} {stat:<10} {'ReqLvl':<7} {'Type'}"]
            lines.append("-" * 80)
            for r in rows:
                lines.append(f"{r['id']:<8} {r['Name']:<45} {r[stat]:<10} {r['reqlevel']:<7} {r['itemtype']}")
            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Spawn group details ----

    @mcp.tool()
    def get_spawngroup(spawngroup_id: int = 0, zone: str = "", npc_name: str = "") -> str:
        """Get spawn group details showing all NPCs that share a spawn point.

        Useful for understanding random spawn tables and placeholder/named setups.

        Args:
            spawngroup_id: Spawn group ID.
            zone: Find spawn groups in a zone (returns list).
            npc_name: Find spawn groups containing this NPC.
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)

            if spawngroup_id:
                cur.execute("SELECT * FROM spawngroup WHERE id = %s", (spawngroup_id,))
                sg = cur.fetchone()
                if not sg:
                    return f"Spawngroup {spawngroup_id} not found."

                lines = [
                    f"Spawngroup: {sg['name']} (ID: {spawngroup_id})",
                    f"  Spawn Limit: {sg.get('spawn_limit', 0)}  Dist: {sg.get('dist', 0)}",
                ]

                cur.execute(
                    """SELECT se.npcID, se.chance, n.name, n.level, n.maxlevel
                       FROM spawnentry se
                       JOIN npc_types n ON n.id = se.npcID
                       WHERE se.spawngroupID = %s ORDER BY se.chance DESC""",
                    (spawngroup_id,),
                )
                entries = cur.fetchall()
                lines.append(f"\n  NPCs in group ({len(entries)}):")
                for e in entries:
                    lvl = f"{e['level']}" if e['level'] == e.get('maxlevel', e['level']) else f"{e['level']}-{e['maxlevel']}"
                    lines.append(f"    {e['name']} (ID: {e['npcID']}) — {e['chance']}% chance — Level {lvl}")

                # Show spawn2 locations
                cur.execute(
                    """SELECT zone, x, y, z, respawntime, enabled
                       FROM spawn2 WHERE spawngroupID = %s""",
                    (spawngroup_id,),
                )
                spawns = cur.fetchall()
                if spawns:
                    lines.append(f"\n  Spawn locations ({len(spawns)}):")
                    for s in spawns:
                        en = "" if s["enabled"] else " [DISABLED]"
                        lines.append(f"    {s['zone']}: ({s['x']:.1f}, {s['y']:.1f}, {s['z']:.1f}) respawn={s['respawntime']}s{en}")

                return "\n".join(lines)

            elif npc_name:
                cur.execute(
                    """SELECT DISTINCT sg.id, sg.name, se.chance, n.name as npc_name
                       FROM spawngroup sg
                       JOIN spawnentry se ON se.spawngroupID = sg.id
                       JOIN npc_types n ON n.id = se.npcID
                       WHERE n.name LIKE %s LIMIT 30""",
                    (f"%{npc_name}%",),
                )
                rows = cur.fetchall()
                if not rows:
                    return f"No spawn groups found for NPC '{npc_name}'."
                lines = [f"Spawn groups containing '{npc_name}':"]
                for r in rows:
                    lines.append(f"  Group {r['id']} ({r['name']}): {r['npc_name']} at {r['chance']}% chance")
                return "\n".join(lines)

            elif zone:
                cur.execute(
                    """SELECT DISTINCT sg.id, sg.name, COUNT(se.npcID) as npc_count
                       FROM spawn2 s2
                       JOIN spawngroup sg ON sg.id = s2.spawngroupID
                       JOIN spawnentry se ON se.spawngroupID = sg.id
                       WHERE s2.zone = %s
                       GROUP BY sg.id ORDER BY sg.name LIMIT 100""",
                    (zone,),
                )
                rows = cur.fetchall()
                if not rows:
                    return f"No spawn groups in zone '{zone}'."
                lines = [f"Spawn groups in {zone}: {len(rows)}"]
                for r in rows:
                    lines.append(f"  {r['id']}: {r['name']} ({r['npc_count']} NPCs)")
                return "\n".join(lines)

            return "Provide spawngroup_id, zone, or npc_name."
        finally:
            conn.close()

    # ---- Ground spawns ----

    @mcp.tool()
    def get_ground_spawns(zone: str, limit: int = 100) -> str:
        """List all ground spawns (clickable items on the ground) in a zone.

        Args:
            zone: Zone short name.
            limit: Max results.
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT gs.id, gs.zoneid, gs.max_x, gs.max_y, gs.max_z,
                          gs.min_x, gs.min_y, gs.heading, gs.item,
                          gs.respawn_timer, i.Name as item_name
                   FROM ground_spawns gs
                   LEFT JOIN items i ON i.id = gs.item
                   WHERE gs.zoneid = (SELECT zoneidnumber FROM zone WHERE short_name = %s LIMIT 1)
                   LIMIT %s""",
                (zone, limit),
            )
            rows = cur.fetchall()
            if not rows:
                return f"No ground spawns in zone '{zone}'."

            lines = [f"Ground spawns in {zone}: {len(rows)}"]
            for r in rows:
                lines.append(
                    f"  [{r['id']}] {r.get('item_name', '?')} (item {r['item']}) "
                    f"at ({r['max_x']:.1f}, {r['max_y']:.1f}, {r['max_z']:.1f}) "
                    f"respawn={r['respawn_timer']}s"
                )
            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Forage/fishing ----

    @mcp.tool()
    def get_zone_forage_fishing(zone: str) -> str:
        """Get forage and fishing loot tables for a zone.

        Args:
            zone: Zone short name.
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)
            zone_id_q = "(SELECT zoneidnumber FROM zone WHERE short_name = %s LIMIT 1)"

            lines = [f"Forage & Fishing in {zone}:"]

            # Forage
            cur.execute(
                f"""SELECT f.id, f.itemid, f.level, f.chance,
                           i.Name as item_name
                    FROM forage f
                    LEFT JOIN items i ON i.id = f.itemid
                    WHERE f.zoneid = {zone_id_q}
                    ORDER BY f.chance DESC""",
                (zone,),
            )
            forage = cur.fetchall()
            if forage:
                lines.append(f"\n  Forage items ({len(forage)}):")
                for f in forage:
                    lines.append(f"    {f.get('item_name', '?')} (ID: {f['itemid']}) — {f['chance']}% (min level {f['level']})")
            else:
                lines.append("\n  No forage items.")

            # Fishing
            cur.execute(
                f"""SELECT f.id, f.Itemid, f.skill_level, f.chance,
                           i.Name as item_name, f.npc_id, f.npc_chance
                    FROM fishing f
                    LEFT JOIN items i ON i.id = f.Itemid
                    WHERE f.zoneid = {zone_id_q}
                    ORDER BY f.chance DESC""",
                (zone,),
            )
            fishing = cur.fetchall()
            if fishing:
                lines.append(f"\n  Fishing items ({len(fishing)}):")
                for f in fishing:
                    npc = f" (NPC {f['npc_id']} at {f['npc_chance']}%)" if f.get("npc_id") else ""
                    lines.append(f"    {f.get('item_name', '?')} (ID: {f['Itemid']}) — {f['chance']}% (skill {f['skill_level']}){npc}")
            else:
                lines.append("\n  No fishing items.")

            return "\n".join(lines)
        finally:
            conn.close()

    # ---- Shared IP / alt detection ----

    @mcp.tool()
    def find_associated_accounts(character_name: str) -> str:
        """Find all accounts that share IPs with a character's account.

        Useful for detecting alts or multi-boxers.

        Args:
            character_name: Character name to investigate.
        """
        conn = db_conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT DISTINCT a.id, a.name, a.charname, a.status,
                          (SELECT ip FROM account_ip WHERE accid = a.id ORDER BY lastused DESC LIMIT 1) as last_ip
                   FROM account a
                   JOIN account_ip ai ON ai.accid = a.id
                   WHERE ai.ip IN (
                       SELECT ip FROM account_ip WHERE accid = (
                           SELECT account_id FROM character_data WHERE name = %s LIMIT 1
                       )
                   )
                   ORDER BY a.name""",
                (character_name,),
            )
            rows = cur.fetchall()
            if not rows:
                return f"No accounts found for character '{character_name}'."

            lines = [f"Accounts sharing IPs with '{character_name}': {len(rows)}"]
            for r in rows:
                lines.append(f"  {r['name']} (ID: {r['id']}) — status: {r['status']} last_ip: {r.get('last_ip', '?')} charname: {r.get('charname', '?')}")
            return "\n".join(lines)
        finally:
            conn.close()
