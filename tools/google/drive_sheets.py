"""Google Drive and Sheets operations."""

import io
from typing import Any, Dict, List, Optional

from googleapiclient.http import MediaInMemoryUpload
from tools.google.auth import get_services


class GoogleDriveSheetsManager:
    """Manager for Google Drive and Google Sheets operations."""

    def __init__(self, drive_service=None, sheets_service=None):
        if drive_service is None or sheets_service is None:
            self.drive, self.sheets = get_services()
        else:
            self.drive = drive_service
            self.sheets = sheets_service

    # --- Google Sheets Operations ---

    def read_sheet(self, spreadsheet_id: str, range_name: str) -> List[List[Any]]:
        """Reads cell values from a specified sheet and range (e.g. 'Import!A1:E5')."""
        result = (
            self.sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        return result.get("values", [])

    def append_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> Dict[str, Any]:
        """Appends rows to the specified sheet."""
        body = {"values": values}
        result = (
            self.sheets.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )
        return result

    def update_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> Dict[str, Any]:
        """Updates cell values in a specified range."""
        body = {"values": values}
        result = (
            self.sheets.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body,
            )
            .execute()
        )
        return result

    def clear_sheet(self, spreadsheet_id: str, range_name: str) -> Dict[str, Any]:
        """Clears values from a range in the spreadsheet."""
        result = (
            self.sheets.spreadsheets()
            .values()
            .clear(spreadsheetId=spreadsheet_id, range=range_name, body={})
            .execute()
        )
        return result

    # --- Google Drive Operations ---

    def list_files(
        self,
        query: str = "",
        page_size: int = 50,
        fields: str = "nextPageToken, files(id, name, mimeType, modifiedTime, size)",
    ) -> List[Dict[str, Any]]:
        """Lists or searches files in Google Drive."""
        # By default exclude trashed files if not specified
        final_query = "trashed = false"
        if query:
            final_query = f"{final_query} and ({query})"

        files = []
        page_token = None
        while True:
            response = (
                self.drive.files()
                .list(
                    q=final_query,
                    spaces="drive",
                    fields=fields,
                    pageSize=min(page_size, 100),
                    pageToken=page_token,
                )
                .execute()
            )
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token or len(files) >= page_size:
                break

        return files[:page_size]

    def get_file_metadata(
        self,
        file_id: str,
        fields: str = "id, name, mimeType, modifiedTime, createdTime, size, webViewLink",
    ) -> Dict[str, Any]:
        """Returns metadata for a given file ID."""
        return self.drive.files().get(fileId=file_id, fields=fields).execute()

    def create_file(
        self,
        name: str,
        mime_type: str = "application/vnd.google-apps.spreadsheet",
        folder_id: Optional[str] = None,
        content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a new file or Google Sheet/Doc in Drive."""
        file_metadata: Dict[str, Any] = {"name": name, "mimeType": mime_type}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media = None
        if content is not None:
            # Upload text/csv content
            content_bytes = content.encode("utf-8")
            media = MediaInMemoryUpload(
                content_bytes,
                mimetype=mime_type if "/" in mime_type else "text/plain",
                resumable=False,
            )

        file = (
            self.drive.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id, name, mimeType, webViewLink",
            )
            .execute()
        )
        return file

    def update_file_content(
        self,
        file_id: str,
        content: str,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Updates the content of an existing file."""
        content_bytes = content.encode("utf-8")
        media = MediaInMemoryUpload(
            content_bytes,
            mimetype=mime_type or "text/plain",
            resumable=False,
        )
        file = (
            self.drive.files()
            .update(
                fileId=file_id,
                media_body=media,
                fields="id, name, mimeType, modifiedTime",
            )
            .execute()
        )
        return file

    def delete_file(self, file_id: str, permanent: bool = False) -> bool:
        """Deletes a file permanently or moves it to trash."""
        if permanent:
            self.drive.files().delete(fileId=file_id).execute()
        else:
            self.drive.files().update(fileId=file_id, body={"trashed": True}).execute()
        return True
