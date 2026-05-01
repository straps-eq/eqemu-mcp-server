"""Quick smoke test of all tool modules against the live server."""
import os
from pathlib import Path

# Load environment from .env if present
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

os.environ.setdefault("EQEMU_ACCESS_MODE", "read")

from mcp.server.fastmcp import FastMCP
from eqemu_mcp import tools_source, tools_quest_api, tools_quests, tools_server, tools_database, tools_entities

mcp = FastMCP("test")
tools_source.register(mcp)
tools_quest_api.register(mcp)
tools_quests.register(mcp)
tools_server.register(mcp)
tools_database.register(mcp)
tools_entities.register(mcp)

import eqemu_mcp.helpers as h

def test(name, fn):
    try:
        result = fn()
        preview = str(result)[:200]
        ok = "Error" not in preview and "not found" not in preview.lower()
        print(f"{'PASS' if ok else 'WARN'}: {name}")
        if not ok:
            print(f"  -> {preview}")
        return ok
    except Exception as e:
        print(f"FAIL: {name} -> {e}")
        return False

passed = 0
total = 0

# Source tools
total += 1; passed += test("search_source", lambda: h.ripgrep_search("GetHP", h.resolve_source(""), "zone/*.h", 5))
total += 1; passed += test("list_source_files", lambda: "\n".join(str(f) for f in sorted(h.resolve_source("zone").iterdir())[:5]))

# Quest API tools
from eqemu_mcp.tools_quest_api import _parse_lua_methods
total += 1; passed += test("parse_lua_methods", lambda: str(len(_parse_lua_methods(h.resolve_source("zone/lua_mob.cpp")))) + " methods")

# Quest script tools
total += 1; passed += test("search_quests", lambda: h.ripgrep_search("quest::say", h.resolve_quests(""), "*.pl", 5))
total += 1; passed += test("list_quest_zones", lambda: "\n".join(sorted(d.name for d in h.resolve_quests("").iterdir() if d.is_dir())[:5]))

# Database tools
conn = h.db_conn()
c = conn.cursor()

total += 1; passed += test("list_tables", lambda: (c.execute("SHOW TABLES"), str(len(c.fetchall())) + " tables")[1])
total += 1; passed += test("describe_table", lambda: (c.execute("DESCRIBE npc_types"), str(len(c.fetchall())) + " columns")[1])

# Entity tools
total += 1; passed += test("search_npcs", lambda: (c.execute("SELECT id, name, level FROM npc_types WHERE name LIKE '%Fippy%' LIMIT 5"), [r for r in c.fetchall()])[1])
total += 1; passed += test("search_items", lambda: (c.execute("SELECT id, name FROM items WHERE name LIKE '%Cloth%' LIMIT 5"), [r for r in c.fetchall()])[1])
total += 1; passed += test("search_zones", lambda: (c.execute("SELECT short_name, long_name FROM zone WHERE short_name LIKE '%kael%' LIMIT 5"), [r for r in c.fetchall()])[1])
total += 1; passed += test("search_spells", lambda: (c.execute("SELECT id, name FROM spells_new WHERE name LIKE '%Heal%' LIMIT 5"), [r for r in c.fetchall()])[1])
total += 1; passed += test("search_factions", lambda: (c.execute("SELECT id, name FROM faction_list WHERE name LIKE '%Guard%' LIMIT 5"), [r for r in c.fetchall()])[1])
total += 1; passed += test("get_server_rules", lambda: (c.execute("SELECT rule_name, rule_value FROM rule_values WHERE rule_name LIKE '%AA%' LIMIT 5"), [r for r in c.fetchall()])[1])
total += 1; passed += test("get_content_flags", lambda: (c.execute("SELECT flag_name, enabled FROM content_flags LIMIT 5"), [r for r in c.fetchall()])[1])
total += 1; passed += test("list_characters", lambda: (c.execute("SELECT id, name, level FROM character_data ORDER BY level DESC LIMIT 5"), [r for r in c.fetchall()])[1])
total += 1; passed += test("get_zone_spawns", lambda: (c.execute("SELECT s2.id, n.name, n.level FROM spawn2 s2 JOIN spawnentry se ON se.spawngroupID=s2.spawngroupID JOIN npc_types n ON n.id=se.npcID WHERE s2.zone='befallen' LIMIT 5"), [r for r in c.fetchall()])[1])

# Server file tools
server_path = Path(os.environ.get("EQEMU_SERVER_PATH", "/opt/akk-stack/server"))
total += 1; passed += test("read_server_config", lambda: (server_path / "eqemu_config.json").exists())
total += 1; passed += test("get_server_logs", lambda: len(list((server_path / "logs").glob("world_*.log"))))

# Loot chain
total += 1; passed += test("get_npc_loot_chain", lambda: (c.execute("""
    SELECT lt.name, lte.lootdrop_id, i.Name
    FROM npc_types n
    JOIN loottable lt ON lt.id = n.loottable_id
    JOIN loottable_entries lte ON lte.loottable_id = lt.id
    JOIN lootdrop_entries lde ON lde.lootdrop_id = lte.lootdrop_id
    JOIN items i ON i.id = lde.item_id
    WHERE n.id = 2001 LIMIT 5"""), [r for r in c.fetchall()])[1])

conn.close()

print(f"\n{'='*40}")
print(f"Results: {passed}/{total} passed")
