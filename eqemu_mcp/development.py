"""Developer-focused MCP primitives and structured environment introspection."""

from pathlib import Path

from mcp.server import MCPServer
from pydantic import BaseModel, Field

from .annotations import READ_ONLY
from .config import ACCESS_MODE, DB_CONFIG, DOCS_PATH, QUESTS_PATH, SERVER_PATH, SOURCE_PATH


class PathStatus(BaseModel):
    """Status for one configured EQEmu content path."""

    path: str
    exists: bool
    is_directory: bool


class DatabaseTarget(BaseModel):
    """Non-secret database connection target."""

    host: str
    port: int
    database: str
    user: str


class DevelopmentEnvironment(BaseModel):
    """Structured overview of the MCP server's EQEmu development context."""

    access_mode: str
    source: PathStatus
    quests: PathStatus
    server: PathStatus
    docs: PathStatus | None
    database: DatabaseTarget
    recommendations: list[str] = Field(default_factory=list)


def _path_status(path: Path) -> PathStatus:
    return PathStatus(path=str(path), exists=path.exists(), is_directory=path.is_dir())


def register(mcp: MCPServer) -> None:
    """Register development helpers, resources, and prompts."""

    @mcp.tool(
        title="Inspect EQEmu Development Environment",
        annotations=READ_ONLY,
    )
    def inspect_development_environment() -> DevelopmentEnvironment:
        """Inspect configured EQEmu paths and the non-secret database target.

        Use this before development or debugging work to see which source,
        quest, server, documentation, and database inputs are available.
        """
        statuses = {
            "source": _path_status(SOURCE_PATH),
            "quests": _path_status(QUESTS_PATH),
            "server": _path_status(SERVER_PATH),
        }
        recommendations = [
            f"Configure EQEMU_{name.upper()}_PATH; {status.path} is unavailable."
            for name, status in statuses.items()
            if not status.is_directory
        ]
        if DOCS_PATH is None:
            recommendations.append("Set EQEMU_DOCS_PATH to avoid cloning documentation on first use.")
        elif not DOCS_PATH.is_dir():
            recommendations.append(f"EQEMU_DOCS_PATH does not exist: {DOCS_PATH}")

        return DevelopmentEnvironment(
            access_mode=ACCESS_MODE,
            source=statuses["source"],
            quests=statuses["quests"],
            server=statuses["server"],
            docs=_path_status(DOCS_PATH) if DOCS_PATH is not None else None,
            database=DatabaseTarget(
                host=str(DB_CONFIG["host"]),
                port=int(DB_CONFIG["port"]),
                database=str(DB_CONFIG["database"]),
                user=str(DB_CONFIG["user"]),
            ),
            recommendations=recommendations,
        )

    @mcp.resource(
        "eqemu://development/workflows",
        title="EQEmu Development Workflows",
        description="Recommended tool sequences for common EQEmu development tasks.",
        mime_type="text/markdown",
    )
    def development_workflows() -> str:
        return """# EQEmu Development Workflows

## Quest debugging
1. Inspect the configured environment with `inspect_development_environment`.
2. Read the quest with `read_quest_file` and search related scripts with `search_quests`.
3. Verify event and method signatures with `get_quest_api_doc` and `get_quest_api_methods`.
4. Trace referenced NPCs, items, factions, tasks, and data buckets with entity tools.
5. Search server logs for the zone and reproduce only after the evidence agrees.

## Content tracing
1. Resolve the entity with a targeted search tool.
2. Follow database relationships with `table_relationships` and schema documentation.
3. Inspect the complete spawn, loot, merchant, faction, grid, or task chain.
4. Search source and quests for the relevant IDs and names.

## Safe content changes
1. Read the current rows or file first.
2. Verify schema and valid values from local documentation and source.
3. Prefer a focused domain write tool over unrestricted SQL.
4. Re-read the changed entity and report the exact reload or repop action required.
"""

    @mcp.prompt(
        name="debug_quest",
        title="Debug an EQEmu Quest",
        description="Build an evidence-driven quest debugging workflow for one zone.",
    )
    def debug_quest(zone: str, symptom: str = "") -> str:
        issue = symptom or "the reported quest behavior"
        return (
            f"Debug {issue} in EQEmu zone '{zone}'. Start with inspect_development_environment. "
            f"Use list_quest_files and search_quests scoped to '{zone}', then read the relevant scripts. "
            "Validate every quest event and API method against local source and official docs. Trace referenced "
            "NPCs, items, factions, tasks, and data buckets in the live database. Check the matching zone logs. "
            "Separate confirmed evidence from hypotheses, identify the smallest fix, and do not mutate content "
            "until the root cause is demonstrated."
        )

    @mcp.prompt(
        name="trace_entity",
        title="Trace an EQEmu Entity",
        description="Trace an entity through database, source, quests, and related content.",
    )
    def trace_entity(entity_type: str, identifier: str) -> str:
        return (
            f"Trace EQEmu {entity_type} '{identifier}' end to end. Resolve its canonical ID and row first, "
            "consult table_relationships and get_schema_doc, then follow every relevant spawn, loot, merchant, "
            "faction, task, spell, grid, source, and quest reference. Summarize the dependency chain, flag broken "
            "or ambiguous references, and cite the exact IDs, files, and tables used."
        )
