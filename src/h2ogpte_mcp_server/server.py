import httpx
import yaml
from fastmcp import FastMCP
from fastmcp.utilities.openapi import OpenAPIParser
from .settings import settings, basic_endpoints
from .tools import register_custom_tools
from .settings import EndpointSet
from typing import List

async def start_server():
    print(f"Starting H2OGPTe MCP API server with endpoint set '{settings.endpoint_set.value}'.")
    mux_service_url = settings.server_url

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
        openapi_spec=openapi_spec, 
        client=client,
        name="H2OGPTe MCP API server",
        all_routes_as_tools=settings.all_endpoints_as_tools
    )

    await register_custom_tools(mcp)

    if settings.endpoint_set == EndpointSet.ALL_WITHOUT_ASYNC_INGEST:
        await remove_create_job_tools(mcp)
    elif settings.endpoint_set == EndpointSet.BASIC:
        await reduce_tools_and_resources(mcp, basic_endpoints)
    elif settings.endpoint_set == EndpointSet.CUSTOM:
        if not settings.custom_endpoint_set_file:
            raise ValueError("Custom endpoint set file is not set. Please set the CUSTOM_ENDPOINT_SET_FILE environment variable.")
        with open(settings.custom_endpoint_set_file, "r") as f:
            custom_endpoints = [endpoint.strip() for endpoint in f.readlines()]
            print(f"Custom endpoints: {custom_endpoints}")
            await reduce_tools_and_resources(mcp, custom_endpoints)
    elif settings.endpoint_set == EndpointSet.ALL:
        pass


    await mcp.run_async()


def _patched_convert_to_parameter_location(self, param_in: "ParameterLocation") -> str:
    return param_in.value


async def remove_create_job_tools(mcp: FastMCP):
    tools = await mcp.get_tools()
    for tool in tools.keys():
        if tool.startswith("create_") and tool.endswith("_job"):
            print(f"Skipping tool {tool}")
            mcp.remove_tool(tool)


async def reduce_tools_and_resources(mcp: FastMCP, endpoints: List[str]):
    tools = await mcp.get_tools()
    for tool in tools.keys():
        if tool not in endpoints:
            print(f"Skipping tool {tool}")
            mcp.remove_tool(tool)

    resources = await mcp.get_resources()
    for resource in resources.keys():
        if resource not in endpoints:
            print(f"Skipping resource {resource}")
            mcp.remove_resource(resource)
