import httpx
from pathlib import Path
from fastmcp import FastMCP

class ExtraTools:
    def __init__(self, client: httpx.Client):
        self._client = client

    def upload_file(self, file_path: str) -> str:
        path = Path(file_path)

        mtime = ""
        try:
            mtime = str(
                int(path.stat().st_mtime) * 1000
            )  # millis since Epoch
        except:
            pass


        with open(path, "rb") as file:
            file_name = path.name
            files_data = {
                "file": (file_name, file.read()),
                "mtime": (None, mtime),
            }

        response = self._client.put("/uploads", files=files_data)
        return response.text()
    
    def update_collection_thumbnail(self, collection_id: str, file_path: str, timeout: int = 600) -> str:
        path = Path(file_path)
    
        size = path.stat().st_size
        if size >= 5242880:
            raise ValueError("File is too large. Please use an image smaller than 5MB")

        with open(path, "rb") as file:
            files_data = {
                "file": (path.name, file.read()),
            }

        response = self._client.put(f"/collections/{collection_id}/thumbnail?timeout={timeout}", files=files_data)
        return response.text()

    def register_tools(self, mcp: FastMCP):
        tools = mcp.get_tools()
        if "upload_file" in tools:
            mcp.remove_tool("upload_file")
            tool = tools["upload_file"]
            mcp.add_tool(self.upload_file, name="upload_file", description=tool.description)

        if "update_collection_thumbnail" in tools:
            mcp.remove_tool("update_collection_thumbnail")  
            tool = tools["update_collection_thumbnail"]
            mcp.add_tool(self.update_collection_thumbnail, name="update_collection_thumbnail", description=tool.description)