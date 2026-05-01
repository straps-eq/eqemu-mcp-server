"""Smoke test for docs tools on the live server."""
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
from eqemu_mcp import tools_docs

mcp = FastMCP("test")
tools_docs.register(mcp)

from eqemu_mcp.tools_docs import _get_docs_root
import subprocess

docs_root = _get_docs_root()
print(f"Docs root: {docs_root} (exists: {docs_root.is_dir()})")

def test(name, fn):
    try:
        result = fn()
        preview = str(result)[:300]
        ok = "Error" not in preview[:50] and "not found" not in preview[:80].lower()
        print(f"{'PASS' if ok else 'WARN'}: {name}")
        if not ok:
            print(f"  -> {preview[:200]}")
        return ok
    except Exception as e:
        print(f"FAIL: {name} -> {e}")
        return False

passed = 0
total = 0

# list_doc_sections
total += 1
passed += test("list_doc_sections", lambda: "\n".join(
    f"{d.name}/" for d in sorted(docs_root.iterdir()) if d.is_dir() and not d.name.startswith(".")
))

# list_schema_tables
total += 1
passed += test("list_schema_tables", lambda: "\n".join(
    f"{d.name}: {len(list(d.glob('*.md')))} tables"
    for d in sorted((docs_root / "schema").iterdir()) if d.is_dir()
))

# get_schema_doc - npc_types
total += 1
passed += test("get_schema_doc(npc_types)", lambda: (docs_root / "schema" / "npcs" / "npc_types.md").read_text()[:200])

# get_schema_doc - items
total += 1
passed += test("get_schema_doc(items)", lambda: (docs_root / "schema" / "items" / "items.md").read_text()[:200])

# get_schema_doc - spawn2
total += 1
passed += test("get_schema_doc(spawn2)", lambda: str(list((docs_root / "schema").rglob("spawn2.md"))))

# get_schema_doc - spells_new
total += 1
passed += test("get_schema_doc(spells_new)", lambda: str(list((docs_root / "schema").rglob("spells_new.md"))))

# get_schema_doc - loottable
total += 1
passed += test("get_schema_doc(loottable)", lambda: str(list((docs_root / "schema").rglob("loottable.md"))))

# search_docs
total += 1
rg = os.environ.get("RG_PATH", "rg")
passed += test("search_docs(npc_types)", lambda: subprocess.run(
    [rg, "--no-heading", "-l", "-i", "-g", "*.md", "npc_types", str(docs_root / "schema")],
    capture_output=True, text=True, timeout=10
).stdout)

# quest-api methods
total += 1
passed += test("get_quest_api_doc(mob)", lambda: (docs_root / "quest-api" / "methods" / "mob.md").read_text()[:200])

# quest-api events
total += 1
passed += test("get_quest_api_doc(perl-npc)", lambda: (docs_root / "quest-api" / "events" / "perl-npc.md").read_text()[:200])

# server docs
total += 1
passed += test("get_server_doc(loading-server-data)", lambda: (docs_root / "server" / "operation" / "loading-server-data.md").read_text()[:200])

# server rules doc
total += 1
passed += test("get_server_doc(server-rules)", lambda: (docs_root / "server" / "operation" / "server-rules.md").read_text()[:200])

# search for a specific column
total += 1
passed += test("search_docs(loottable_id)", lambda: subprocess.run(
    [rg, "--no-heading", "-c", "-i", "-g", "*.md", "loottable_id", str(docs_root)],
    capture_output=True, text=True, timeout=10
).stdout)

print(f"\n{'='*40}")
print(f"Results: {passed}/{total} passed")
