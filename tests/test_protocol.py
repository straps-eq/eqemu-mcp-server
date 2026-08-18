"""Protocol-level tests that do not require an EQEmu installation."""

from mcp import Client
from starlette.testclient import TestClient

import server as server_module
from eqemu_mcp import __version__, tools_database, tools_entities_write, tools_quests, tools_server
from eqemu_mcp.mcp_server import EQEmuMCPServer
from server import _network_app, _parser, _transport_security, health, mcp


async def test_server_negotiates_current_protocol_and_identity() -> None:
    async with Client(mcp) as client:
        assert client.protocol_version == "2026-07-28"
        assert client.server_info is not None
        assert client.server_info.name == "eqemu"
        assert client.server_info.version == __version__


async def test_server_retains_legacy_handshake_support() -> None:
    async with Client(mcp, mode="legacy") as client:
        tools = await client.list_tools()
        protocol_version = client.protocol_version

    assert protocol_version != "2026-07-28"
    assert len(tools.tools) >= 50


async def test_read_tool_catalog_has_schemas_and_annotations() -> None:
    async with Client(mcp) as client:
        result = await client.list_tools()

    names = {tool.name for tool in result.tools}
    assert len(result.tools) >= 50
    assert {"search_source", "run_query", "get_npc", "search_docs"} <= names
    for tool in result.tools:
        assert tool.input_schema["type"] == "object"
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True


async def test_tool_call_uses_public_client_api() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("list_quest_api_classes")

    assert result.is_error is False
    assert result.content


async def test_development_primitives_are_exposed() -> None:
    async with Client(mcp) as client:
        tool_result = await client.call_tool("inspect_development_environment")
        resources = await client.list_resources()
        prompts = await client.list_prompts()
        prompt = await client.get_prompt(
            "debug_quest",
            {"zone": "qeynos2", "symptom": "an NPC does not respond"},
        )

    assert tool_result.is_error is False
    assert tool_result.structured_content is not None
    assert tool_result.structured_content["access_mode"] in {"read", "readwrite"}
    assert "password" not in tool_result.structured_content["database"]
    assert "eqemu://development/workflows" in {str(resource.uri) for resource in resources.resources}
    assert {"debug_quest", "trace_entity"} <= {item.name for item in prompts.prompts}
    assert prompt.messages
    assert "qeynos2" in str(prompt.messages[0].content)

    tool_catalog = {tool.name: tool for tool in (await _list_tools()).tools}
    assert tool_catalog["inspect_development_environment"].output_schema is not None


async def _list_tools():
    async with Client(mcp) as client:
        return await client.list_tools()


async def test_write_tools_advertise_mutating_behavior() -> None:
    write_server = EQEmuMCPServer("eqemu-write-test")
    tools_quests.register_write(write_server)
    tools_server.register_write(write_server)
    tools_database.register_write(write_server)
    tools_entities_write.register_write(write_server)

    async with Client(write_server) as client:
        result = await client.list_tools()

    tools = {tool.name: tool for tool in result.tools}
    assert tools["write_quest_file"].annotations.read_only_hint is False
    assert tools["write_quest_file"].annotations.idempotent_hint is True
    assert tools["create_npc"].annotations.destructive_hint is False
    assert tools["run_write_query"].annotations.destructive_hint is True
    assert tools["get_data_buckets"].annotations.read_only_hint is True


async def test_health_response_contains_version() -> None:
    response = await health(None)  # type: ignore[arg-type]
    assert response.status_code == 200
    assert __version__.encode() in response.body


def test_cli_defaults_and_transport_selection() -> None:
    parser = _parser()
    assert parser.parse_args([]).http is None
    assert parser.parse_args(["--http"]).http == 8888
    assert parser.parse_args(["--http", "9000"]).http == 9000
    assert parser.parse_args(["--sse", "9001"]).sse == 9001


def test_network_apps_expose_expected_routes() -> None:
    http_paths = {route.path for route in _network_app("streamable-http", "127.0.0.1").routes}
    sse_paths = {route.path for route in _network_app("sse", "127.0.0.1").routes}
    assert {"/mcp", "/health"} <= http_paths
    assert {"/sse", "/messages", "/health"} <= sse_paths


def test_network_token_protects_mcp_but_not_health(monkeypatch) -> None:
    monkeypatch.setattr(server_module, "MCP_TOKEN", "test-secret")
    app = _network_app("streamable-http", "127.0.0.1")

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/mcp").status_code == 401
        authorized = client.post(
            "/mcp",
            headers={"Authorization": "Bearer test-secret"},
            json={},
        )

    assert authorized.status_code != 401


def test_transport_allowlists_enable_dns_rebinding_protection(monkeypatch) -> None:
    monkeypatch.setenv("EQEMU_MCP_ALLOWED_HOSTS", "mcp.example.com:*, localhost:*")
    monkeypatch.setenv("EQEMU_MCP_ALLOWED_ORIGINS", "https://mcp.example.com:*")

    settings = _transport_security()

    assert settings.enable_dns_rebinding_protection is True
    assert settings.allowed_hosts == ["mcp.example.com:*", "localhost:*"]
    assert settings.allowed_origins == ["https://mcp.example.com:*"]
