import httpx
import yaml
import requests
from fastmcp import FastMCP
from fastmcp.utilities.openapi import OpenAPIParser
from .settings import settings
from .tools import ExtraTools


def start_server():
    mux_service_url = settings.h2ogpte_server_url

    # Load your OpenAPI spec
    yaml_spec = requests.get(f"{mux_service_url}/api-spec.yaml").content
    openapi_spec = yaml.load(yaml_spec, Loader=yaml.CLoader)
    remove_create_job_endpoints(openapi_spec)

    # Create an HTTP client for your API
    headers = {"Authorization": f"Bearer {settings.api_key}"}
    client = httpx.AsyncClient(base_url=f"{mux_service_url}/api/v1", headers=headers)

    OpenAPIParser._convert_to_parameter_location = _patched_convert_to_parameter_location

    # Create the MCP server
    mcp = FastMCP.from_openapi(
        openapi_spec=openapi_spec, client=client, name="H2OGPTe MCP API server"
    )

    extra_tools = ExtraTools(client)
    extra_tools.register_tools(mcp)

    mcp.run()


def _patched_convert_to_parameter_location(self, param_in: "ParameterLocation") -> str:
    return param_in.value


def remove_create_job_endpoints(openapi_spec):
    paths = openapi_spec["paths"]
    to_be_deleted = []
    for path in paths:
        if path.endswith("/job") or path.endswith("_job"):
            to_be_deleted.append(path)
    for path in to_be_deleted:
        print(f"Skipping path {path}")
        del paths[path]
