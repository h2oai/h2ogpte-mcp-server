import httpx
import yaml
from fastmcp import FastMCP
from fastmcp.utilities.openapi import OpenAPIParser
from .settings import settings
from .tools import register_custom_tools

async def start_server():
    mux_service_url = settings.h2ogpte_server_url

    # Load your OpenAPI spec
    client = httpx.AsyncClient(base_url=f"{mux_service_url}")
    response = await client.get("/api-spec.yaml")
    yaml_spec = response.content
    openapi_spec = yaml.load(yaml_spec, Loader=yaml.CLoader)

    # Create an HTTP client for your API
    headers = {"Authorization": f"Bearer {settings.api_key}"}
    client = httpx.AsyncClient(base_url=f"{mux_service_url}/api/v1", headers=headers)

    OpenAPIParser._convert_to_parameter_location = _patched_convert_to_parameter_location

    # Create the MCP server
    mcp = FastMCP.from_openapi(
        openapi_spec=openapi_spec, client=client, name="H2OGPTe MCP API server"
    )

    await register_custom_tools(mcp)
    await remove_create_job_tools(mcp)

    await mcp.run_async()


def _patched_convert_to_parameter_location(self, param_in: "ParameterLocation") -> str:
    return param_in.value


async def remove_create_job_tools(mcp: FastMCP):
    tools = await mcp.get_tools()
    for tool in tools.keys():
        if tool.startswith("create_") and tool.endswith("_job"):
            print(f"Skipping tool {tool}")
            mcp.remove_tool(tool)