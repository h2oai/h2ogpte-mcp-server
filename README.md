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
- **API_KEY** - (required) H2OGPTe access key. See [documentation](https://docs.h2o.ai/enterprise-h2ogpte/guide/apis#create-an-api-key) on how to get the key.
- **H2OGPTE_SERVER_URL** - The url of H2OGPTe server. Default value is [https://h2ogpte.genai.h2o.ai](https://h2ogpte.genai.h2o.ai).
- **ALL_ENDPOINTS_AS_TOOLS** - A boolean flag, specifing whether all REST API endpoints should be represented as MCP tools. If disabled, GET endpoints will be represented as resources. Default value is `true`.

### Example Configuration
An example MCP server configuration for MCP clients. E.g.: Cursor, Claude Desktop

```json
{
  "mcpServers": {
    "h2ogpte-mcp-server": {
      "command": "h2ogpte-mcp-server",
      "env": {
        "API_KEY": "sk-...",
        "H2OGPTE_SERVER_URL": "https://h2ogpte.genai.h2o.ai",
        "ALL_ENDPOINTS_AS_TOOLS": true
      }
    }
  }
}
```

