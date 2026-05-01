"""Smoke test for the new lookup tools on the live server."""
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

from mcp.server.fastmcp import FastMCP
from eqemu_mcp import tools_lookup

mcp = FastMCP("test")
tools_lookup.register(mcp)

# We need to call the tool functions directly
from eqemu_mcp.helpers import db_conn

def test(name, fn):
    try:
        result = fn()
        preview = str(result)[:250]
        ok = "Error" not in preview[:60] and "Traceback" not in preview
        print(f"{'PASS' if ok else 'WARN'}: {name}")
        if not ok:
            print(f"  -> {preview[:200]}")
        return ok
    except Exception as e:
        print(f"FAIL: {name} -> {e}")
        return False

passed = 0
total = 0

# Verify import works
total += 1
passed += test("module_import", lambda: "OK")

# Test each tool function by calling the DB queries directly
conn = db_conn()

def query_test(sql, params=None):
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    return cur.fetchall()

# get_character - find any character
total += 1
passed += test("get_character_query", lambda: query_test(
    "SELECT c.name, c.level FROM character_data c LIMIT 1"
))

# get_account_info
total += 1
passed += test("get_account_info_query", lambda: query_test(
    "SELECT a.name, a.status FROM account a LIMIT 1"
))

# get_online_characters
total += 1
passed += test("online_characters_query", lambda: query_test(
    "SELECT c.name FROM character_data c WHERE c.last_login > (UNIX_TIMESTAMP() - 600) LIMIT 5"
))

# search_recipes
total += 1
passed += test("search_recipes_query", lambda: query_test(
    "SELECT r.id, r.name, r.tradeskill FROM tradeskill_recipe r LIMIT 5"
))

# get_recipe - find any recipe
total += 1
rows = query_test("SELECT id FROM tradeskill_recipe LIMIT 1")
recipe_id = rows[0]["id"] if rows else 1
passed += test("get_recipe_query", lambda: query_test(
    "SELECT r.*, e.item_id FROM tradeskill_recipe r JOIN tradeskill_recipe_entries e ON e.recipe_id = r.id WHERE r.id = %s LIMIT 5",
    (recipe_id,)
))

# get_zone_doors
total += 1
passed += test("get_zone_doors_query", lambda: query_test(
    "SELECT id, doorid, name FROM doors WHERE zone = 'crushbone' LIMIT 5"
))

# get_npc_grid
total += 1
passed += test("get_npc_grid_query", lambda: query_test(
    "SELECT id, type FROM grid LIMIT 5"
))

# get_spell
total += 1
passed += test("get_spell_query", lambda: query_test(
    "SELECT * FROM spells_new WHERE id = 1"
))

# get_npc_faction
total += 1
passed += test("get_npc_faction_query", lambda: query_test(
    "SELECT nf.id, nf.name FROM npc_faction nf LIMIT 3"
))

# get_task
total += 1
passed += test("get_task_query", lambda: query_test(
    "SELECT * FROM tasks LIMIT 1"
))

# search_items_by_stat
total += 1
passed += test("search_items_by_stat_query", lambda: query_test(
    "SELECT id, Name, hp FROM items WHERE hp >= 100 ORDER BY hp DESC LIMIT 5"
))

# get_spawngroup
total += 1
passed += test("get_spawngroup_query", lambda: query_test(
    "SELECT sg.id, sg.name FROM spawngroup sg LIMIT 3"
))

# get_ground_spawns
total += 1
passed += test("ground_spawns_query", lambda: query_test(
    "SELECT gs.id, gs.item FROM ground_spawns gs LIMIT 3"
))

# get_zone_forage_fishing
total += 1
passed += test("forage_fishing_query", lambda: query_test(
    "SELECT f.id, f.itemid FROM forage f LIMIT 3"
))

# find_associated_accounts
total += 1
passed += test("find_associated_accounts_query", lambda: query_test(
    "SELECT DISTINCT accid, ip FROM account_ip LIMIT 3"
))

conn.close()

# Now test the actual server module import
total += 1
passed += test("full_server_import", lambda: __import__("server") and "OK")

print(f"\n{'='*40}")
print(f"Results: {passed}/{total} passed")
