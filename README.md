# EQEmu MCP Server

A comprehensive [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for managing and operating [EverQuest Emulator](https://docs.eqemu.io/) servers. Connects your AI coding assistant (Claude, Cursor, etc.) directly to your EQEmu source code, quest scripts, database, and server configuration.

## Features

**60+ tools** across two permission tiers:

### Read-Only Tools (always available)

| Category | Tools | Description |
|---|---|---|
| **C++ Source** | `search_source`, `get_source_file`, `list_source_files` | Search and browse the EQEmu C++ codebase |
| **Quest API** | `list_quest_api_classes`, `get_quest_api_methods` | Browse Lua/Perl quest API bindings with method signatures |
| **Quest Scripts** | `list_quest_zones`, `list_quest_files`, `read_quest_file`, `search_quests` | Browse and search quest scripts across all zones |
| **Server Files** | `list_server_files`, `read_server_file`, `get_server_config` | Inspect server files, plugins, config (passwords redacted) |
| **Server Info** | `get_server_rules`, `get_server_logs`, `get_crash_logs`, `get_content_flags`, `get_expansion_info` | Rules, logs, crashes, content flags, expansion info |
| **Database** | `list_tables`, `describe_table`, `run_query`, `table_relationships` | Schema inspection and read-only SQL queries |
| **NPCs** | `search_npcs`, `get_npc` | Search NPCs by name/zone/level, full NPC details with spawn locations |
| **Items** | `search_items`, `get_item` | Search items by name/type/level, full item stats |
| **Spawns** | `get_zone_spawns` | List all spawn points and NPCs in a zone |
| **Loot** | `get_npc_loot` | Full loot chain: NPC -> loottable -> lootdrop -> items |
| **Merchants** | `get_merchant_items` | View merchant inventories |
| **Zones** | `search_zones`, `get_zone_info` | Zone lookup with spawn/NPC/door counts |
| **Tasks** | `search_tasks` | Search tasks by name |
| **Factions** | `search_factions` | Search factions by name |
| **Spells** | `search_spells` | Search spells by name |
| **Characters** | `list_characters`, `get_character`, `get_online_characters` | List, inspect, and find online characters |
| **Accounts** | `get_account_info`, `find_associated_accounts` | Account investigation, IP history, alt detection |
| **Spells (Detail)** | `get_spell` | Full spell details: effects, class usability, teleport info |
| **Factions (Detail)** | `get_npc_faction` | NPC faction assignments and kill-hit breakdowns |
| **Tasks (Detail)** | `get_task` | Full task details with activities and rewards |
| **Tradeskills** | `search_recipes`, `get_recipe` | Tradeskill recipe search and full component/result breakdown |
| **Spawn Groups** | `get_spawngroup` | Spawn group inspection — placeholder/named setups, NPC chances |
| **Grids/Pathing** | `get_npc_grid` | NPC patrol paths with waypoint coordinates |
| **Doors** | `get_zone_doors` | Zone doors/portals with destinations and lock info |
| **Ground Spawns** | `get_ground_spawns` | Clickable ground items in a zone |
| **Forage/Fishing** | `get_zone_forage_fishing` | Zone forage and fishing loot tables |
| **Item Stats** | `search_items_by_stat` | Find items by specific stat thresholds (HP, mana, haste, etc.) |
| **Documentation** | `search_docs`, `read_doc`, `list_doc_sections` | Search and read the full docs.eqemu.io documentation |
| **Schema Docs** | `get_schema_doc`, `list_schema_tables` | Database table documentation with column descriptions, types, relationships |
| **Quest API Docs** | `get_quest_api_doc` | Official quest API method/event docs with examples |
| **Server Docs** | `get_server_doc` | Server operation guides, configuration references, command lists |

### Write Tools (opt-in via `EQEMU_ACCESS_MODE=readwrite`)

| Category | Tools | Description |
|---|---|---|
| **Quest Editing** | `write_quest_file`, `delete_quest_file` | Create, edit, or delete quest scripts |
| **Server Rules** | `set_server_rule` | Change server rule values |
| **Content Flags** | `set_content_flag` | Enable/disable content flags |
| **NPC Management** | `create_npc`, `update_npc` | Create new NPCs or modify existing ones |
| **Spawn Management** | `create_spawn`, `delete_spawn` | Add/remove spawn points |
| **Loot Management** | `add_loot_to_npc` | Add items to NPC loot tables |
| **Merchants** | `add_merchant_item`, `remove_merchant_item` | Manage merchant inventories |
| **Data Buckets** | `get_data_buckets`, `set_data_bucket` | Read/write data buckets |
| **Database** | `run_write_query` | Execute INSERT/UPDATE/DELETE queries |

## Quick Start

### Prerequisites

- Python 3.10+
- Access to an EQEmu server (akk-stack recommended)
- [ripgrep](https://github.com/BurntSushi/ripgrep) (for source code search — optional, falls back to grep)

### Installation

```bash
# Clone the repo
git clone https://github.com/your-org/eqemu-mcp-server.git
cd eqemu-mcp-server

# Create a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your server's paths and database credentials
```

### Finding Your Database Credentials

**akk-stack users:**
```bash
cd /opt/akk-stack
make info    # Shows all passwords and connection details
```

Or check your `eqemu_config.json`:
```bash
cat /opt/akk-stack/server/eqemu_config.json | python3 -m json.tool
```

The database section has `host`, `port`, `username`, `password`, and `db`.

**Important:** If running the MCP server *outside* the Docker network (e.g., directly on the host), use the host's external IP for `EQEMU_DB_HOST`, not `127.0.0.1` or `mariadb`.

### Usage

#### stdio (Claude Desktop / Cursor / Windsurf)

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "eqemu": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/eqemu-mcp-server/server.py"],
      "env": {
        "EQEMU_SOURCE_PATH": "/opt/akk-stack/code",
        "EQEMU_QUESTS_PATH": "/opt/akk-stack/server/quests",
        "EQEMU_SERVER_PATH": "/opt/akk-stack/server",
        "EQEMU_DB_HOST": "YOUR_SERVER_IP",
        "EQEMU_DB_PORT": "3306",
        "EQEMU_DB_USER": "eqemu",
        "EQEMU_DB_PASSWORD": "YOUR_DB_PASSWORD",
        "EQEMU_DB_NAME": "peq",
        "RG_PATH": "/path/to/rg",
        "EQEMU_ACCESS_MODE": "read"
      }
    }
  }
}
```

#### SSE (Remote / Network)

```bash
./start.sh --sse 8888
```

Then connect your MCP client to `http://your-server:8888/sse`.

## Permission Model

The server operates in one of two modes, controlled by `EQEMU_ACCESS_MODE`:

| Mode | Value | Tools Available | Use Case |
|---|---|---|---|
| **Read-Only** | `read` (default) | 30+ read-only tools | Safe for shared/public use, exploring and learning |
| **Read-Write** | `readwrite` | All 40+ tools | Server admins actively managing content |

**Read-only mode** is the default and is safe to expose. All database queries are restricted to SELECT/SHOW/DESCRIBE, all file access is read-only, and passwords in server config are redacted.

**Read-write mode** enables database modifications, quest file editing, NPC/spawn/loot creation, and server rule changes. Only enable this if you trust the MCP client and understand the implications.

### Setting the Mode

```bash
# In .env
EQEMU_ACCESS_MODE=readwrite

# Or as environment variable
EQEMU_ACCESS_MODE=readwrite python server.py
```

## Architecture

```
eqemu-mcp-server/
  server.py                 # Entry point — registers tools based on access mode
  eqemu_mcp/
    __init__.py
    config.py               # Centralized configuration from env vars
    helpers.py              # Shared utilities (DB, ripgrep, file I/O)
    tools_source.py         # C++ source code search/browsing
    tools_quest_api.py      # Lua/Perl quest API method parsing
    tools_quests.py         # Quest script browsing + editing (write)
    tools_server.py         # Server config, rules, logs, content flags
    tools_database.py       # Schema inspection, SQL queries
    tools_entities.py       # NPC, item, spawn, loot, zone, spell lookups
    tools_entities_write.py # NPC, spawn, loot, merchant write operations
    tools_docs.py           # EQEmu documentation search (docs.eqemu.io)
    tools_lookup.py         # Deep-dive lookups: characters, accounts, recipes, doors, grids, factions
  .env.example              # Configuration template
  start.sh                  # Startup script
  pyproject.toml            # Python package config
```

## Deployment on akk-stack

For servers running the [akk-stack](https://github.com/Akkadius/akk-stack):

```bash
# On the server host
cd /opt/akk-stack

# Create venv (if not already done)
python3 -m venv eqemu-mcp-venv
source eqemu-mcp-venv/bin/activate
pip install mcp[cli] mysql-connector-python

# Install ripgrep (if not available)
apt-get install -y ripgrep  # or download from GitHub releases

# Clone EQEmu docs (for documentation search tools)
git clone --depth 1 https://github.com/EQEmu/eqemu-docs-v2.git eqemu-docs

# Clone and configure
git clone https://github.com/your-org/eqemu-mcp-server.git
cd eqemu-mcp-server
cp .env.example .env

# Edit .env:
#   EQEMU_DB_HOST=<your-server-external-ip>
#   EQEMU_DB_PASSWORD=<from 'make info'>
#   EQEMU_ACCESS_MODE=read  (or readwrite)
#   EQEMU_DOCS_PATH=/opt/akk-stack/eqemu-docs

# Test
python server.py  # Ctrl+C to stop

# Run as SSE service
./start.sh --sse 8888
```

### Running as a systemd Service

```bash
sudo cat > /etc/systemd/system/eqemu-mcp.service << 'EOF'
[Unit]
Description=EQEmu MCP Server
After=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/akk-stack/eqemu-mcp-server
ExecStart=/opt/akk-stack/eqemu-mcp-server/start.sh --sse 8888
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable eqemu-mcp
sudo systemctl start eqemu-mcp
```

## Public / Shared Access

For offering this to other EQEmu server operators:

### Self-Hosted (Recommended)

Each server operator runs their own MCP server instance pointed at their own data. This is the simplest and most secure approach:

1. Clone the repo on their server
2. Configure `.env` with their paths and DB credentials
3. Set `EQEMU_ACCESS_MODE=read` for safety
4. Run via stdio or SSE

### Hosted Service (Advanced)

For a centralized MCP service serving multiple servers:

- Each server would need a unique API key / tenant identifier
- Database connections would be per-tenant
- Source code access could point to the public EQEmu GitHub repo
- Quest and server file access would need secure file serving per tenant

This requires additional authentication/authorization infrastructure beyond what's in the current codebase.

## Example Queries

Once connected, you can ask your AI assistant things like:

- "What quest methods are available for mob HP manipulation in Lua?"
- "Show me all NPCs in Befallen above level 10"
- "What's in Fippy Darkpaw's loot table?"
- "Search the C++ source for how spell resistance is calculated"
- "What server rules control AA experience?"
- "Show me the most recent world server logs"
- "List all merchants in East Commonlands"
- "What items does the Cloth Cap recipe require?"
- "Find all quest scripts that use `quest::say`"

With write mode enabled:
- "Create a new NPC named Test_Merchant at level 30"
- "Add a Cloth Cap to merchant 123's inventory"
- "Set the AA:ExpPerPoint rule to 50000000"
- "Write a new quest script for an NPC in gfaydark"

## License

MIT
