# Contributing to EQEmu MCP Server

Thanks for your interest in contributing! This project aims to give AI assistants accurate, real-time context about EQEmu servers.

## Getting Started

1. Fork and clone the repo
2. Set up a development environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -e .
   ```
3. Copy `.env.example` to `.env` and configure with your EQEmu server details
4. Run the test suite: `python test_all_tools.py`

## Project Structure

```
eqemu_mcp/
  config.py              # Environment-based configuration
  helpers.py             # Shared utilities (DB, ripgrep, file I/O)
  tools_source.py        # C++ source code search
  tools_quest_api.py     # Quest API method parsing
  tools_quests.py        # Quest script browsing/editing
  tools_server.py        # Server config, rules, logs
  tools_database.py      # Schema inspection and SQL
  tools_entities.py      # NPC, item, spawn, zone lookups
  tools_entities_write.py # Write operations (NPC, spawn, loot)
  tools_docs.py          # Documentation search
  tools_lookup.py        # Characters, accounts, recipes, etc.
```

## Adding a New Tool

1. Identify the correct module (or create a new `tools_*.py` file if it's a new domain)
2. Write the tool function with a clear docstring — this is what the AI assistant sees
3. Register it in the module's `register(mcp)` function
4. If it's a write tool, gate it behind `config.is_writable()`
5. Add a test case to `test_all_tools.py`
6. Update the tool count in `README.md` if adding new tools

### Tool Guidelines

- **Read tools** should never modify data
- **Write tools** must check `config.is_writable()` and return a clear error if not enabled
- Use `helpers.db_conn()` for database connections
- Use `helpers.resolve_under()` for file path validation (prevents path traversal)
- Return formatted, human-readable strings (the AI will parse them)
- Keep result sizes reasonable — use `config.MAX_RESULTS` and `config.MAX_QUERY_ROWS`
- Redact sensitive fields (passwords, keys) in config/server output

## Security

- **Never** hardcode credentials, IPs, or secrets in source files
- All sensitive config comes from environment variables (`.env`)
- Test files load config from `.env` — never commit a `.env` file
- The `.gitignore` excludes `.env` to prevent accidental commits
- Read-only mode (`EQEMU_ACCESS_MODE=read`) is the default — write tools are opt-in

## Submitting Changes

1. Create a feature branch
2. Make your changes
3. Run the test suite to verify
4. Open a pull request with a clear description

## Reporting Issues

Open an issue on GitHub with:
- What you expected to happen
- What actually happened
- Your EQEmu server setup (akk-stack version, OS, Docker vs. manual)
- Relevant error messages or logs
