#!/usr/bin/env python3
"""
Comprehensive end-to-end test for every tool in the EQEmu MCP Server.
Runs each tool against the live database and file system to verify correctness.
"""

import os
import sys
import traceback

# Set up environment
os.environ.setdefault("EQEMU_DOCS_PATH", "/opt/akk-stack/eqemu-docs")
os.environ.setdefault("EQEMU_SOURCE_PATH", "/opt/akk-stack/code")
os.environ.setdefault("EQEMU_QUESTS_PATH", "/opt/akk-stack/server/quests")
os.environ.setdefault("EQEMU_SERVER_PATH", "/opt/akk-stack/server")
os.environ.setdefault("EQEMU_DB_HOST", "15.204.234.211")
os.environ.setdefault("EQEMU_DB_PORT", "3306")
os.environ.setdefault("EQEMU_DB_USER", "eqemu")
os.environ.setdefault("EQEMU_DB_PASSWORD", "QXoKk67qHjBNjP86sj6GRr6tsNslSVF")
os.environ.setdefault("EQEMU_DB_NAME", "peq")
os.environ.setdefault("RG_PATH", "/opt/akk-stack/eqemu-mcp-venv/bin/rg")
os.environ.setdefault("EQEMU_ACCESS_MODE", "read")

from mcp.server.fastmcp import FastMCP

# Import all tool modules
from eqemu_mcp import (
    tools_source,
    tools_quest_api,
    tools_quests,
    tools_server,
    tools_database,
    tools_entities,
    tools_docs,
    tools_lookup,
)

# Create MCP instance and register all tools
mcp = FastMCP("test")
tools_source.register(mcp)
tools_quest_api.register(mcp)
tools_quests.register(mcp)
tools_server.register(mcp)
tools_database.register(mcp)
tools_entities.register(mcp)
tools_docs.register(mcp)
tools_lookup.register(mcp)

# Get all registered tool functions
_tools = {}
for tool in mcp._tool_manager._tools.values():
    _tools[tool.name] = tool.fn

passed = 0
failed = 0
errors = []


def test(name: str, tool_name: str, kwargs: dict | None = None):
    """Run a tool and check for basic correctness."""
    global passed, failed
    kwargs = kwargs or {}
    try:
        fn = _tools.get(tool_name)
        if fn is None:
            print(f"  SKIP: {name} — tool '{tool_name}' not registered")
            return

        result = fn(**kwargs)
        result_str = str(result)

        # Check for error indicators
        is_error = any(x in result_str[:200] for x in [
            "Traceback", "Error:", "error:", "not found", "No such file",
        ])
        # Symlink-to-docker errors are expected, not failures
        if "not accessible (may be inside a Docker container)" in result_str:
            is_error = False

        # Some "not found" results are expected for specific queries
        expected_not_found = any(x in result_str for x in [
            "not found", "No matches", "No spells found", "No characters found",
            "No recipes found", "No doors found", "No grids found",
            "No ground spawns", "No forage", "No accounts found",
        ])

        if is_error and not expected_not_found:
            print(f"  FAIL: {name}")
            print(f"        {result_str[:200]}")
            failed += 1
            errors.append((name, result_str[:300]))
        else:
            preview = result_str[:100].replace("\n", " | ")
            print(f"  PASS: {name} — {preview}")
            passed += 1
    except Exception as e:
        print(f"  FAIL: {name} — EXCEPTION: {e}")
        traceback.print_exc()
        failed += 1
        errors.append((name, str(e)))


print("=" * 70)
print("EQEmu MCP Server — Comprehensive Tool Test")
print("=" * 70)

# ---- tools_source.py ----
print("\n--- Source Code Tools ---")
test("search_source", "search_source", {"pattern": "ZoneDatabase", "file_filter": "*.h", "max_results": 5})
test("get_source_file", "get_source_file", {"path": "zone/main.cpp"})
test("list_source_files", "list_source_files", {"directory": "zone", "pattern": "*.cpp"})

# ---- tools_quest_api.py ----
print("\n--- Quest API Tools ---")
test("list_quest_api_classes", "list_quest_api_classes")
test("get_quest_api_methods_lua", "get_quest_api_methods", {"class_name": "Mob", "language": "lua"})
test("get_quest_api_methods_perl", "get_quest_api_methods", {"class_name": "Mob", "language": "perl"})

# ---- tools_quests.py ----
print("\n--- Quest Script Tools ---")
test("list_quest_zones", "list_quest_zones")
test("list_quest_files", "list_quest_files", {"zone": "qeynos2"})
test("read_quest_file", "read_quest_file", {"zone": "qeynos2", "filename": "Aenia_Ghenson.lua"})
test("search_quests", "search_quests", {"pattern": "quest::say", "max_results": 5})

# ---- tools_server.py ----
print("\n--- Server Tools ---")
test("get_server_config", "get_server_config")
test("get_server_rules", "get_server_rules", {"filter": "Character"})
test("get_server_logs", "get_server_logs", {"log_type": "zone"})
test("get_crash_logs", "get_crash_logs")
test("get_content_flags", "get_content_flags")
test("get_expansion_info", "get_expansion_info")
test("list_server_files_root", "list_server_files")
test("list_server_files_subdir", "list_server_files", {"directory": "plugins"})
test("read_server_file", "read_server_file", {"path": "eqemu_config.json"})

# ---- tools_database.py ----
print("\n--- Database Tools ---")
test("list_tables", "list_tables")
test("describe_table", "describe_table", {"table": "npc_types"})
test("run_query", "run_query", {"sql": "SELECT COUNT(*) as total FROM npc_types"})
test("table_relationships", "table_relationships", {"table": "spawn2"})

# ---- tools_entities.py ----
print("\n--- Entity Tools ---")
test("search_npcs_by_name", "search_npcs", {"name": "Fippy", "limit": 5})
test("search_npcs_by_zone", "search_npcs", {"zone": "qeynos2", "limit": 5})
test("get_npc", "get_npc", {"npc_id": 1})  # NPC ID 1 should exist
test("search_items", "search_items", {"name": "Cloth Cap", "limit": 5})
test("get_item", "get_item", {"item_id": 1001})
test("get_zone_spawns", "get_zone_spawns", {"zone": "qeynos2", "limit": 5})
test("get_npc_loot", "get_npc_loot", {"npc_id": 1})
test("search_zones", "search_zones", {"filter": "qeynos"})
test("get_zone_info", "get_zone_info", {"zone": "qeynos2"})
test("search_tasks", "search_tasks", {"name": "test", "limit": 5})
test("search_factions", "search_factions", {"name": "Freeport", "limit": 5})
test("search_spells", "search_spells", {"name": "Complete Heal", "limit": 5})
test("get_merchant_items", "get_merchant_items", {"merchant_id": 1})
test("list_characters", "list_characters", {"limit": 5})

# ---- tools_docs.py ----
print("\n--- Documentation Tools ---")
test("search_docs", "search_docs", {"query": "loottable", "max_results": 5})
test("read_doc", "read_doc", {"path": "server/operation/in-game-command-reference"})
test("list_doc_sections", "list_doc_sections")
test("get_schema_doc", "get_schema_doc", {"table": "npc_types"})
test("list_schema_tables", "list_schema_tables")
test("list_schema_tables_filtered", "list_schema_tables", {"category": "loot"})
test("get_quest_api_doc", "get_quest_api_doc", {"subject": "client"})
test("get_server_doc", "get_server_doc", {"topic": "commands"})

# ---- tools_lookup.py ----
print("\n--- Lookup Tools ---")
test("get_character", "get_character", {"name": "%"})  # Match any character
test("get_account_info", "get_account_info", {"account_name": "%"})  # Match any account
test("get_online_characters", "get_online_characters", {"minutes": 10})
test("search_recipes", "search_recipes", {"name": "Bread", "limit": 5})
test("get_recipe", "get_recipe", {"recipe_id": 1})
test("get_zone_doors", "get_zone_doors", {"zone": "qeynos2"})
test("get_npc_grid_list", "get_npc_grid", {"zone": "qeynos2"})
test("get_spell_detail", "get_spell", {"spell_id": 13})  # Complete Heal
test("get_npc_faction", "get_npc_faction", {"faction_id": 1})
test("get_task", "get_task", {"task_id": 1})
test("search_items_by_stat", "search_items_by_stat", {"stat": "hp", "min_value": 100, "limit": 5})
test("get_spawngroup", "get_spawngroup", {"zone": "qeynos2"})
test("get_ground_spawns", "get_ground_spawns", {"zone": "qeynos2"})
test("get_zone_forage_fishing", "get_zone_forage_fishing", {"zone": "qeynos2"})
test("find_associated_accounts", "find_associated_accounts", {"character_name": "Admin"})

# ---- Summary ----
print("\n" + "=" * 70)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 70)

if errors:
    print(f"\nFailed tests ({len(errors)}):")
    for name, err in errors:
        print(f"  - {name}: {err[:150]}")

sys.exit(0 if failed == 0 else 1)
