from deepseek_mcp.server import TOOLS, handle


def test_initialize_response():
    response = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert response["result"]["protocolVersion"] == "2024-11-05"
    assert response["result"]["serverInfo"]["name"] == "deepseek-mcp"


def test_tools_list_exposes_deepseek_tool():
    response = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    tools = response["result"]["tools"]
    assert tools == TOOLS
    assert tools[0]["name"] == "deepseek"
    assert tools[0]["inputSchema"]["required"] == ["prompt"]


def test_unknown_method_returns_json_rpc_error():
    response = handle({"jsonrpc": "2.0", "id": 3, "method": "nope"})

    assert response["id"] == 3
    assert response["error"]["code"] == -32601
