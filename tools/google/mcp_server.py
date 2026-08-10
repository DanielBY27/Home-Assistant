"""Model Context Protocol (MCP) Server for Google Drive & Google Sheets."""

import json
from typing import Any, List, Optional
from mcp.server.mcpserver import MCPServer
from tools.google.drive_sheets import GoogleDriveSheetsManager

server = MCPServer("google-workspace-local")


@server.tool()
def read_sheet(spreadsheet_id: str, range_name: str) -> Any:
    """Reads rows and cell values from a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (from the URL).
        range_name: The A1 range including sheet name (e.g. 'Import!A1:E5' or 'Sheet1!A:Z').
    """
    try:
        mgr = GoogleDriveSheetsManager()
        return mgr.read_sheet(spreadsheet_id, range_name)
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def append_sheet(spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> Any:
    """Appends rows to the end of a Google Spreadsheet sheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        range_name: The sheet or range to append to (e.g. 'Import!A1' or 'Import').
        values: 2D array of rows to append, e.g. [["2026-10-11", 123.4, "ok"]].
    """
    try:
        mgr = GoogleDriveSheetsManager()
        return mgr.append_sheet(spreadsheet_id, range_name, values)
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def update_sheet(spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> Any:
    """Updates specific cells or a range of cells in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        range_name: The target range to overwrite (e.g. 'Sheet1!B2:C4').
        values: 2D array of new values matching the range dimensions.
    """
    try:
        mgr = GoogleDriveSheetsManager()
        return mgr.update_sheet(spreadsheet_id, range_name, values)
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def clear_sheet(spreadsheet_id: str, range_name: str) -> Any:
    """Clears values from the specified range in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        range_name: The range to clear (e.g. 'Import!A2:Z100').
    """
    try:
        mgr = GoogleDriveSheetsManager()
        return mgr.clear_sheet(spreadsheet_id, range_name)
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def list_drive_files(query: str = "", page_size: int = 50) -> Any:
    """Searches or lists files in Google Drive.
    
    Args:
        query: Optional Google Drive search query (e.g. "mimeType = 'application/vnd.google-apps.spreadsheet'").
        page_size: Maximum number of files to return (default 50).
    """
    try:
        mgr = GoogleDriveSheetsManager()
        return mgr.list_files(query=query, page_size=page_size)
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def get_drive_file(file_id: str) -> Any:
    """Retrieves metadata for a specific file in Google Drive.
    
    Args:
        file_id: The Google Drive file ID.
    """
    try:
        mgr = GoogleDriveSheetsManager()
        return mgr.get_file_metadata(file_id)
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def create_drive_file(
    name: str,
    mime_type: str = "application/vnd.google-apps.spreadsheet",
    folder_id: Optional[str] = None,
    content: Optional[str] = None,
) -> Any:
    """Creates a new file or spreadsheet in Google Drive.
    
    Args:
        name: Name of the file.
        mime_type: MIME type (default 'application/vnd.google-apps.spreadsheet' for Sheets).
        folder_id: Optional parent folder ID in Drive.
        content: Optional text or CSV content to initialize the file with.
    """
    try:
        mgr = GoogleDriveSheetsManager()
        f_id = folder_id if folder_id else None
        return mgr.create_file(name, mime_type=mime_type, folder_id=f_id, content=content)
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def update_drive_file(file_id: str, content: str, mime_type: Optional[str] = None) -> Any:
    """Updates the content of an existing text or data file in Google Drive.
    
    Args:
        file_id: The ID of the file to update.
        content: The new text/data content.
        mime_type: Optional MIME type of the content.
    """
    try:
        mgr = GoogleDriveSheetsManager()
        return mgr.update_file_content(file_id, content, mime_type=mime_type)
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def delete_drive_file(file_id: str, permanent: bool = False) -> Any:
    """Deletes a file from Google Drive (moves to trash by default).
    
    Args:
        file_id: The ID of the file to delete.
        permanent: If True, permanently deletes the file; if False, moves to trash.
    """
    try:
        mgr = GoogleDriveSheetsManager()
        mgr.delete_file(file_id, permanent=permanent)
        return {"status": "success", "file_id": file_id, "permanent": permanent}
    except Exception as e:
        return {"error": str(e)}


def main():
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
