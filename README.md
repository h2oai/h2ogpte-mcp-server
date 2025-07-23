# H2OGPTe MCP Server

H2OGPTe MCP Server is a Model Context Protocol (MCP) server that prifor the [H2OGPTe](https://h2o.ai/platform/enterprise-h2ogpte/) project. 
The server is just a local proxy forwarding traffic to [REST API endpoints of H2OGPTe](https://h2ogpte.genai.h2o.ai/swagger-ui/) executed as commnad.

##  Installation

### From Pypi

```sh
pip install h2ogpte-mcp-server
```

### From Github

```sh
# Clone git repository
git clone https://github.com/h2oai/h2ogpte-mcp-server.git

# Use the latest release version
git checkout $(git describe --tags)

make setup
make build

# The command will install h2ogpte-mcp-server to the current python environment
make install
```

## Usage

### Environment Variables
- **H2OGPTE_API_KEY** - (required) H2OGPTe access key. See [documentation](https://docs.h2o.ai/enterprise-h2ogpte/guide/apis#create-an-api-key) on how to get the key.
- **H2OGPTE_SERVER_URL** - The url of H2OGPTe server. Default value is [https://h2ogpte.genai.h2o.ai](https://h2ogpte.genai.h2o.ai).
- **H2OGPTE_ALL_ENDPOINTS_AS_TOOLS** - A boolean flag, specifing whether all REST API endpoints should be represented as MCP tools. If disabled, GET endpoints will be represented as resources. Default value is `true`.
- **H2OGPTE_ENDPOINT_SET** - A set of REST API endpoints that will be used for MCP tools or resources. The default value is `all_without_async_ingest`. Possible values:
  - `all` - All REST API endpoints on the H2OGPTe server
  - `all_without_async_ingest` - All endpoints without asynchronous ingestion endpoints. These endpoints start  and returns a job. E.g.: `create_ingest_upload_job` 
  - `basic` - A mininal set of endpoints for chatting with collections and ingesting new documents.
  - `custom` - A set of endpoints defined by the user. If chossen, the `H2OGPTE_CUSTOM_ENDPOINT_SET_FILE` variable must be set.
- **H2OGPTE_CUSTOM_ENDPOINT_SET_FILE** - A path to file with the list of REST API endpoints. Each endpoint name must be an a separate line. The name of the endpoint is the `operationId` attribute in REST API spec file (e.g.: [https://h2ogpte.genai.h2o.ai/api-spec.yaml](https://h2ogpte.genai.h2o.ai/api-spec.yaml)) 
- **H2OGPTE_CUSTOM_ENDPOINT_SPEC_FILE** - A path to OpenAPI spec file in YAML format describing REST API of the H2OGPTe server. If not specified, the file is obtained from the H2OGPTe server itself. This environement variable should be used only for debugging purposes.

### Example Configuration
An example MCP server configuration for MCP clients. E.g.: Cursor, Claude Desktop

```json
{
  "mcpServers": {
    "h2ogpte-mcp-server": {
      "command": "h2ogpte-mcp-server",
      "env": {
        "H2OGPTE_API_KEY": "sk-...",
        "H2OGPTE_SERVER_URL": "https://h2ogpte.genai.h2o.ai",
        "H2OGPTE_ALL_ENDPOINTS_AS_TOOLS": "true"
      }
    }
  }
}
```

