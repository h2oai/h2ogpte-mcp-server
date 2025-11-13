import httpx
import yaml
from fastmcp import FastMCP
from fastmcp.server.openapi import FastMCPOpenAPI
from fastmcp.utilities.openapi import OpenAPIParser
from fastmcp.server.openapi import MCPType, RouteMap
from fastmcp.resources.resource_manager import ResourceManager
from .settings import settings, basic_endpoints
from .tools import register_custom_tools
from .settings import EndpointSet
from typing import List

async def start_server():
    print(f"Starting H2OGPTe MCP API server with endpoint set '{settings.endpoint_set.value}'.")
    mux_service_url = settings.server_url

    # Load your OpenAPI spec
    openapi_spec = await load_openapi_spec(mux_service_url)

    # Create an HTTP client for your API
    headers = {"Authorization": f"Bearer {settings.api_key}"}
    client = httpx.AsyncClient(base_url=f"{mux_service_url}/api/v1", headers=headers)

    # Default route maps for FastMCP 2.6.1
    route_maps = [
        RouteMap(methods=["GET"], pattern=r".*\{.*\}.*", mcp_type=MCPType.RESOURCE_TEMPLATE),
        RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.RESOURCE),
        RouteMap(methods="*", pattern=r".*", mcp_type=MCPType.TOOL),
    ]

    if settings.all_endpoints_as_tools:
        route_maps = [RouteMap(methods="*", pattern=r".*", mcp_type=MCPType.TOOL)]
        
    # Create the MCP server
    # Enforcing the old parser, the experimental parser does not work as expected.
    mcp = FastMCPOpenAPI(
        openapi_spec=openapi_spec, 
        client=client,
        name="H2OGPTe MCP API server",
        route_maps=route_maps,
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

async def load_openapi_spec(mux_service_url):
    if settings.custom_openapi_spec_file:
        with open(settings.custom_openapi_spec_file, "r") as f:
            custom_openapi_spec = yaml.load(f, Loader=yaml.CLoader)
        return custom_openapi_spec
    else:
        client = httpx.AsyncClient(base_url=f"{mux_service_url}")
        response = await client.get("/api-spec.yaml")
        yaml_spec = response.content
        openapi_spec = yaml.load(yaml_spec, Loader=yaml.CLoader)
        return openapi_spec


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
    resource_templates = await mcp.get_resource_templates()
    mcp._resource_manager = ResourceManager()

    for resource_name, resource in resources.items():
        if resource_name in endpoints:
            mcp.add_resource(resource)
        else:
            print(f"Skipping resource {resource_name}")

    for resource_template_name, resource_template in resource_templates.items():
        if resource_template_name in endpoints:
            mcp.add_resource_template(resource_template)
        else:
            print(f"Skipping resource template {resource_template_name}")
