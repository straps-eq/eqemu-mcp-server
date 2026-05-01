<p align="center">
  <img src="https://img.shields.io/badge/version-0.4.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10+-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
  <img src="https://img.shields.io/badge/tools-60+-purple" alt="Tools">
</p>

# EQEmu MCP Server

> Give your AI assistant full context on your EverQuest Emulator server — source code, quest API, database schema, documentation, and live game data — so it can write accurate queries, debug issues, and manage content without guessing.

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for [EverQuest Emulator](https://docs.eqemu.io/) servers. Works with **Claude Desktop**, **Cursor**, **Windsurf**, and any MCP-compatible AI client.

---

## Why?

When you ask an AI assistant to write a query, inspect spawn data, or debug a quest issue, it has to **guess** table names, column names, relationships, and valid values. It gets things wrong. You end up copy-pasting schema docs and correcting hallucinated SQL.

This MCP server eliminates that. Your AI assistant can:

- **Look up exact schema** — `get_schema_doc("npc_types")` returns all 80+ columns with types and descriptions
- **Follow relationships** — `table_relationships("spawn2")` shows FK links through the entire spawn chain
- **Search documentation** — `search_docs("loottable_id")` finds every doc page referencing that column
- **Query live data** — `run_query("SELECT * FROM npc_types WHERE name LIKE '%Nagafen%'")` hits your actual database
- **Inspect full chains** — NPC → faction → loot → spawn group → grid path, all from structured tools

The result: correct queries on the first try, accurate quest scripts, and faster debugging.

---

## Tools (60+)

### Read-Only (always available)

| Category | Tools | Description |
|---|---|---|
| **C++ Source** | `search_source` `get_source_file` `list_source_files` | Search and browse the EQEmu C++ codebase |
| **Quest API** | `list_quest_api_classes` `get_quest_api_methods` | Browse Lua/Perl quest API method signatures |
| **Quest Scripts** | `list_quest_zones` `list_quest_files` `read_quest_file` `search_quests` | Browse and search quest scripts across all zones |
| **Server Files** | `list_server_files` `read_server_file` `get_server_config` | Server files, plugins, config (passwords redacted) |
| **Server Info** | `get_server_rules` `get_server_logs` `get_crash_logs` `get_content_flags` `get_expansion_info` | Rules, logs, crash analysis, content flags |
| **Database** | `list_tables` `describe_table` `run_query` `table_relationships` | Schema inspection and read-only SQL |
| **NPCs** | `search_npcs` `get_npc` | NPC search by name/zone/level with spawn locations |
| **Items** | `search_items` `get_item` `search_items_by_stat` | Item search by name/type/level or stat thresholds |
| **Spawns** | `get_zone_spawns` `get_spawngroup` | Spawn points, spawn groups, placeholder/named setups |
| **Loot** | `get_npc_loot` | Full loot chain: NPC → loottable → lootdrop → items |
| **Merchants** | `get_merchant_items` | Merchant inventories |
| **Zones** | `search_zones` `get_zone_info` | Zone lookup with spawn/NPC/door counts |
| **Spells** | `search_spells` `get_spell` | Spell search and full effect/class breakdown |
| **Factions** | `search_factions` `get_npc_faction` | Faction search and NPC faction kill-hit details |
| **Tasks** | `search_tasks` `get_task` | Task search and full activity/reward breakdown |
| **Characters** | `list_characters` `get_character` `get_online_characters` | Character inspection, stats, AAs, inventory, online players |
| **Accounts** | `get_account_info` `find_associated_accounts` | Account investigation, IP history, alt detection |
| **Tradeskills** | `search_recipes` `get_recipe` | Recipe search and component/result breakdown |
| **Grids** | `get_npc_grid` | NPC patrol paths with waypoint coordinates |
| **Doors** | `get_zone_doors` | Zone doors/portals with destinations, keys, lockpick |
| **Ground Spawns** | `get_ground_spawns` | Clickable ground items in a zone |
| **Forage/Fishing** | `get_zone_forage_fishing` | Zone forage and fishing loot tables |
| **Documentation** | `search_docs` `read_doc` `list_doc_sections` | Full-text search across docs.eqemu.io |
| **Schema Docs** | `get_schema_doc` `list_schema_tables` | Table docs with column descriptions and ER relationships |
| **Quest API Docs** | `get_quest_api_doc` | Official quest API docs with signatures and examples |
| **Server Docs** | `get_server_doc` | Server operation guides and command references |

### Write Tools (opt-in)

Enable with `EQEMU_ACCESS_MODE=readwrite`:

| Category | Tools | Description |
|---|---|---|
| **Quest Editing** | `write_quest_file` `delete_quest_file` | Create, edit, or delete quest scripts |
| **Server Rules** | `set_server_rule` | Change server rule values |
| **Content Flags** | `set_content_flag` | Enable/disable content flags |
| **NPC Management** | `create_npc` `update_npc` | Create or modify NPCs |
| **Spawn Management** | `create_spawn` `delete_spawn` | Add/remove spawn points |
| **Loot Management** | `add_loot_to_npc` | Add items to NPC loot tables |
| **Merchants** | `add_merchant_item` `remove_merchant_item` | Manage merchant inventories |
| **Data Buckets** | `get_data_buckets` `set_data_bucket` | Read/write data buckets |
| **Database** | `run_write_query` | Execute INSERT/UPDATE/DELETE queries |

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Access to an EQEmu server** ([akk-stack](https://github.com/Akkadius/akk-stack) recommended)
- **ripgrep** (optional — for fast source code search, falls back to grep)

### Option A: Docker (Recommended)

```bash
git clone https://github.com/straps-eq/eqemu-mcp-server.git
cd eqemu-mcp-server

cp .env.example .env
# Edit .env with your database credentials and paths

docker compose up -d
```

The server starts on port 8888. Connect your AI client to `http://YOUR_SERVER_IP:8888/sse`.

#### akk-stack Integration

If you're running [akk-stack](https://github.com/Akkadius/akk-stack), the MCP server can join your existing Docker network and talk to MariaDB directly. **No separate `.env` file is needed** — the compose overlay reads credentials from your akk-stack `.env` automatically.

**Step 1: Clone into your akk-stack directory**
```bash
cd /opt/akk-stack
git clone https://github.com/straps-eq/eqemu-mcp-server.git
```

**Step 2 (optional): Add token authentication**

To require a token for connections, add this to your akk-stack `.env`:
```bash
echo "EQEMU_MCP_TOKEN=$(openssl rand -hex 32)" >> /opt/akk-stack/.env
# View the generated token:
grep EQEMU_MCP_TOKEN /opt/akk-stack/.env
```

**Step 3: Build and start the MCP container**
```bash
cd /opt/akk-stack

# Build the image
docker compose -f docker-compose.yml \
  -f eqemu-mcp-server/docker-compose.akk-stack.yml \
  build eqemu-mcp

# Start (only the MCP container — does NOT restart your game server)
docker compose -f docker-compose.yml \
  -f eqemu-mcp-server/docker-compose.akk-stack.yml \
  up -d --no-deps eqemu-mcp
```

> **⚠️ Important:** Always use `--no-deps eqemu-mcp` to start *only* the MCP container. Without `--no-deps`, Docker Compose may recreate your MariaDB and EQEmu server containers, causing a server restart.

**Step 4: Open the firewall**
```bash
sudo ufw allow 8888/tcp
```

**Step 5: Verify**
```bash
docker logs akk-stack-eqemu-mcp-1 --tail 5
# Should show: "Uvicorn running on http://0.0.0.0:8888"
```

The MCP server is **read-only by default**. It automatically:
- Connects to MariaDB via the `backend` network (no external IP needed)
- Mounts your `code/` and `server/` directories read-only
- Uses your existing `MARIADB_PASSWORD` from the akk-stack `.env`

**Configuration:** All settings go in your akk-stack `.env` (`/opt/akk-stack/.env`) — you do **not** create a separate `.env` inside the `eqemu-mcp-server/` folder. Available variables:

| Variable | Default | Description |
|---|---|---|
| `MARIADB_PASSWORD` | *(from akk-stack)* | Database password — already in your `.env` |
| `IP_ADDRESS` | `0.0.0.0` | Bind address — already in your `.env` |
| `EQEMU_DB_NAME` | `peq` | Database name — set this if your DB isn't named `peq` |
| `EQEMU_MCP_TOKEN` | *(empty)* | Set to require token auth on connections |
| `MCP_ACCESS_MODE` | `read` | Set to `readwrite` to enable write tools |

### Option B: Manual Install (No Docker)

```bash
git clone https://github.com/straps-eq/eqemu-mcp-server.git
cd eqemu-mcp-server

python3 -m venv venv
source venv/bin/activate
pip install -e .

cp .env.example .env
# Edit .env with your server paths and database credentials

# Start SSE server
./start.sh --sse 8888
```

### Finding Your Database Credentials

**akk-stack users:**
```bash
cd /opt/akk-stack && make info
```

Or read `eqemu_config.json`:
```bash
cat /opt/akk-stack/server/eqemu_config.json | python3 -m json.tool
```

> **Note:** If running the MCP server outside Docker (directly on the host), use the host's external IP for `EQEMU_DB_HOST`, not `127.0.0.1` or `mariadb`.

---

## Connecting Your AI Client

### Option 1: SSE (Recommended for Remote)

Start the server:
```bash
./start.sh --sse 8888
```

Then configure your AI client:

<details>
<summary><b>Windsurf</b></summary>

Edit `~/.codeium/windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "eqemu": {
      "serverUrl": "http://YOUR_SERVER_IP:8888/sse"
    }
  }
}
```

With token authentication enabled:
```json
{
  "mcpServers": {
    "eqemu": {
      "serverUrl": "http://YOUR_SERVER_IP:8888/sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```
</details>

<details>
<summary><b>Cursor</b></summary>

In Settings → MCP Servers, add:
```json
{
  "mcpServers": {
    "eqemu": {
      "url": "http://YOUR_SERVER_IP:8888/sse"
    }
  }
}
```
</details>

<details>
<summary><b>VS Code (GitHub Copilot)</b></summary>

Open Command Palette → "MCP: Open User Configuration" (or edit `.vscode/mcp.json` in your workspace):
```json
{
  "servers": {
    "eqemu": {
      "type": "sse",
      "url": "http://YOUR_SERVER_IP:8888/sse"
    }
  }
}
```

With token authentication:
```json
{
  "servers": {
    "eqemu": {
      "type": "sse",
      "url": "http://YOUR_SERVER_IP:8888/sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```
</details>

<details>
<summary><b>OpenAI Codex CLI</b></summary>

Run `codex mcp add` or edit `~/.codex/config.toml`:
```toml
[mcp_servers.eqemu]
url = "http://YOUR_SERVER_IP:8888/sse"
enabled = true

[mcp_servers.eqemu.env]
MCP_TOKEN = "YOUR_TOKEN"
```

Or with token via environment variable:
```toml
[mcp_servers.eqemu]
url = "http://YOUR_SERVER_IP:8888/sse"
bearer_token_env_var = "MCP_TOKEN"
enabled = true
```

Then set `export MCP_TOKEN=YOUR_TOKEN` in your shell.
</details>

<details>
<summary><b>Claude Desktop</b></summary>

Claude Desktop doesn't natively support SSE. Use stdio mode instead (Option 2), or use [mcp-proxy](https://github.com/punkpeye/mcp-proxy) to bridge SSE to stdio.
</details>

### Option 2: stdio (Local)

If the MCP server is on the same machine as your AI client:

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

---

## Permission Model

| Mode | `EQEMU_ACCESS_MODE` | Tools | Use Case |
|---|---|---|---|
| **Read-Only** | `read` (default) | 50+ read-only | Safe for sharing — SQL restricted to SELECT, passwords redacted |
| **Read-Write** | `readwrite` | All 60+ | Server admins actively managing content |

```bash
# In .env
EQEMU_ACCESS_MODE=read      # safe default
EQEMU_ACCESS_MODE=readwrite  # full access
```

---

## Security

By default, the MCP server accepts connections from anyone who can reach the port. Use one or both of these methods to restrict access.

### Option 1: Firewall (IP Restriction)

Use UFW to only allow specific IP addresses to connect:

```bash
# Remove any existing open rule
sudo ufw delete allow 8888/tcp

# Allow only your IP
sudo ufw allow from YOUR_HOME_IP to any port 8888 proto tcp

# Allow additional users
sudo ufw allow from FRIEND_IP to any port 8888 proto tcp

# Verify
sudo ufw status | grep 8888
```

This is the simplest approach — no code changes needed. To find your IP, visit https://whatismyip.com.

### Option 2: Token Authentication

Require a secret token for all SSE connections. Set `EQEMU_MCP_TOKEN` in your `.env`:

```bash
# Generate a random token
EQEMU_MCP_TOKEN=$(openssl rand -hex 32)
echo "EQEMU_MCP_TOKEN=$EQEMU_MCP_TOKEN" >> .env
echo "Your token: $EQEMU_MCP_TOKEN"
```

Then restart the server. Clients must include the token in the URL:

**Windsurf:**
```json
{
  "mcpServers": {
    "eqemu": {
      "serverUrl": "http://YOUR_SERVER_IP:8888/sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

The token can also be passed as a query parameter (`?token=YOUR_TOKEN`) for clients that don't support custom headers. Without a valid token, the server returns `401 Unauthorized`.

### Combining Both

For maximum security, use both: firewall restricts which IPs can connect, and the token ensures only authorized clients can use the tools even if someone discovers the port.

---

## Example Conversations

Once connected, your AI assistant can handle requests like:

**Querying & Inspecting:**
> "Write me a query to find all NPCs in crushbone that drop cloth items"
>
> "What's in Lord Nagafen's loot table?"
>
> "Show me all items with haste >= 30"
>
> "Who's online right now?"

**Debugging & Investigation:**
> "Find all accounts that share IPs with the character Soandso"
>
> "Show me the patrol path for the guard NPCs in Qeynos"
>
> "What faction hits do you get for killing a Freeport Militia member?"
>
> "Show me the most recent crash logs"

**Quest Development:**
> "What Lua quest methods are available on the Client object?"
>
> "Search the source for how spell resistance is calculated"
>
> "Find all quest scripts that use `eq.spawn2`"

**Content Management** (write mode):
> "Create a new NPC named Test_Merchant at level 30"
>
> "Add a Cloth Cap to merchant 123's inventory"
>
> "Set the AA:ExpPerPoint rule to 50000000"

---

## Deployment on akk-stack

```bash
cd /opt/akk-stack

# Create venv
python3 -m venv eqemu-mcp-venv
source eqemu-mcp-venv/bin/activate
pip install mcp[cli] mysql-connector-python

# Install ripgrep (optional but recommended)
apt-get install -y ripgrep

# Clone documentation (for docs tools)
git clone --depth 1 https://github.com/EQEmu/eqemu-docs-v2.git eqemu-docs

# Clone and configure
git clone https://github.com/straps-eq/eqemu-mcp-server.git
cd eqemu-mcp-server
cp .env.example .env
# Edit .env with: DB host/password (from `make info`), paths, access mode

# Test
python server.py  # Ctrl+C to stop

# Run SSE
./start.sh --sse 8888

# Open the firewall port
sudo ufw allow 8888/tcp
```

### Running as a systemd Service

```bash
sudo tee /etc/systemd/system/eqemu-mcp.service > /dev/null << 'EOF'
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

---

## Architecture

```
eqemu-mcp-server/
  server.py                          # Entry point — registers tools based on access mode
  start.sh                           # Startup script (loads .env, activates venv)
  Dockerfile                         # Docker image for containerized deployment
  docker-compose.yml                 # Standalone Docker Compose
  docker-compose.akk-stack.yml       # akk-stack integration overlay
  eqemu_mcp/
    config.py                        # Centralized configuration from env vars
    helpers.py                       # Shared utilities (DB connections, ripgrep, file I/O)
    tools_source.py                  # C++ source code search and browsing
    tools_quest_api.py               # Lua/Perl quest API method parsing
    tools_quests.py                  # Quest script browsing + editing (write)
    tools_server.py                  # Server config, rules, logs, content flags
    tools_database.py                # Schema inspection and SQL queries
    tools_entities.py                # NPC, item, spawn, loot, zone, spell lookups
    tools_entities_write.py          # NPC, spawn, loot, merchant write operations
    tools_docs.py                    # EQEmu documentation search (docs.eqemu.io)
    tools_lookup.py                  # Characters, accounts, recipes, doors, grids, factions
```

---

## Self-Hosting for Other Server Operators

Each EQEmu server operator runs their own instance:

1. Clone this repo on the server
2. Configure `.env` with their paths and DB credentials
3. Set `EQEMU_ACCESS_MODE=read` (safe default)
4. Run via stdio or SSE
5. Connect their AI client

The server is completely self-contained — no external services, no cloud dependencies, no API keys. All data stays on your machine.

---

## License

MIT
