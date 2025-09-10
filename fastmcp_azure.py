import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.azure import AzureProvider
from fastapi import FastAPI

# Load environment variables from .env file
load_dotenv()

# Azure OAuth Configuration from .env
auth_provider = AzureProvider(
    client_id=os.getenv("AZURE_CLIENT_ID"),
    client_secret=os.getenv("AZURE_CLIENT_SECRET"),
    tenant_id=os.getenv("AZURE_TENANT_ID"),
    base_url=os.getenv("AZURE_BASE_URL", "http://localhost:8000"),
    required_scopes=["User.Read", "email", "openid", "profile"],
)

# Initialize FastMCP with Azure Authentication
mcp = FastMCP(
    name="Azure Secured MCP Server",
    auth=auth_provider
)

# Get the FastAPI app and add docs
app = FastAPI()
app.mount("/", mcp.http_app())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    #mcp.run(transport="http", host="0.0.0.0", port=8000)