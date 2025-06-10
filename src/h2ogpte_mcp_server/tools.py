from pathlib import Path
from fastmcp import FastMCP, Context


async def upload_file(file: str, context: Context) -> str:
    path = Path(file)

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

    response = await context.fastmcp._client.put("/uploads", files=files_data)
    if response.is_error:
        raise Exception(response.text)
    return response.text
    

async def update_collection_thumbnail(collection_id: str, file: str, context: Context) -> str:
    path = Path(file)

    size = path.stat().st_size
    if size >= 5242880:
        raise ValueError("File is too large. Please use an image smaller than 5MB")

    with open(path, "rb") as file:
        files_data = {
            "file": (path.name, file.read()),
        }

    response = await context.fastmcp._client.put(f"/collections/{collection_id}/thumbnail", files=files_data)
    if response.is_error:
        raise Exception(response.text)
    return "OK"


async def register_tools(mcp: FastMCP):
    tools = await mcp.get_tools()
    if "upload_file" in tools:
        print("Overriding upload_file tool")
        mcp.remove_tool("upload_file")
        tool = tools["upload_file"]
        mcp.add_tool(upload_file, name="upload_file", description=tool.description)
        
    if "update_collection_thumbnail" in tools:
        print("Overriding update_collection_thumbnail tool")
        mcp.remove_tool("update_collection_thumbnail")  
        tool = tools["update_collection_thumbnail"]
        mcp.add_tool(update_collection_thumbnail, name="update_collection_thumbnail", description=tool.description)
