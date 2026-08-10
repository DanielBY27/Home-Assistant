"""Tests for Google Drive and Google Sheets tools."""

from unittest.mock import MagicMock, patch
import pytest

from tools.google.auth import get_credentials, find_service_account_file, find_client_secret_file
from tools.google.drive_sheets import GoogleDriveSheetsManager


def test_auth_missing_credentials_raises_error(tmp_path):
    """Test that missing credentials raise FileNotFoundError with helpful message."""
    with patch("tools.google.auth.get_credentials_dir", return_value=tmp_path):
        with pytest.raises(FileNotFoundError) as exc_info:
            get_credentials()
        assert "Keine gültigen Google-Zugangsdaten gefunden" in str(exc_info.value)


def test_read_sheet_mock():
    """Test reading spreadsheet values with mocked Sheets API."""
    mock_sheets = MagicMock()
    mock_values = mock_sheets.spreadsheets().values()
    mock_values.get().execute.return_value = {
        "values": [
            ["Datum", "Uhrzeit", "Ertrag_kW", "Prognose_kW"],
            ["2026-10-11", "10:00", "4.2", "4.1"],
            ["2026-10-11", "10:30", "4.5", "4.4"],
        ]
    }

    mgr = GoogleDriveSheetsManager(drive_service=MagicMock(), sheets_service=mock_sheets)
    result = mgr.read_sheet("test-sheet-id", "Import!A1:D3")

    assert len(result) == 3
    assert result[0] == ["Datum", "Uhrzeit", "Ertrag_kW", "Prognose_kW"]
    assert result[1][0] == "2026-10-11"


def test_append_sheet_mock():
    """Test appending rows to spreadsheet with mocked Sheets API."""
    mock_sheets = MagicMock()
    mock_values = mock_sheets.spreadsheets().values()
    mock_values.append().execute.return_value = {
        "updates": {"updatedRows": 1, "updatedColumns": 4}
    }

    mgr = GoogleDriveSheetsManager(drive_service=MagicMock(), sheets_service=mock_sheets)
    new_row = [["2026-10-11", "11:00", "5.1", "5.0"]]
    result = mgr.append_sheet("test-sheet-id", "Import!A1", new_row)

    assert result["updates"]["updatedRows"] == 1


def test_update_sheet_mock():
    """Test updating cells in spreadsheet with mocked Sheets API."""
    mock_sheets = MagicMock()
    mock_values = mock_sheets.spreadsheets().values()
    mock_values.update().execute.return_value = {
        "updatedCells": 2
    }

    mgr = GoogleDriveSheetsManager(drive_service=MagicMock(), sheets_service=mock_sheets)
    result = mgr.update_sheet("test-sheet-id", "Auswertung!B2:C2", [["Wert1", "Wert2"]])

    assert result["updatedCells"] == 2


def test_list_drive_files_mock():
    """Test listing Google Drive files."""
    mock_drive = MagicMock()
    mock_drive.files().list().execute.return_value = {
        "files": [
            {"id": "file123", "name": "Solcast_Logger", "mimeType": "application/vnd.google-apps.spreadsheet"},
            {"id": "file456", "name": "EMHASS_Backup", "mimeType": "application/json"},
        ],
        "nextPageToken": None,
    }

    mgr = GoogleDriveSheetsManager(drive_service=mock_drive, sheets_service=MagicMock())
    files = mgr.list_files(query="mimeType = 'application/vnd.google-apps.spreadsheet'", page_size=10)

    assert len(files) == 2
    assert files[0]["name"] == "Solcast_Logger"


def test_create_and_delete_file_mock():
    """Test creating and deleting a file in Google Drive."""
    mock_drive = MagicMock()
    mock_drive.files().create().execute.return_value = {
        "id": "new-file-789",
        "name": "Neue Tabelle",
        "mimeType": "application/vnd.google-apps.spreadsheet",
    }
    mock_drive.files().update().execute.return_value = {"id": "new-file-789", "trashed": True}

    mgr = GoogleDriveSheetsManager(drive_service=mock_drive, sheets_service=MagicMock())
    created = mgr.create_file("Neue Tabelle")
    assert created["id"] == "new-file-789"

    # Move to trash
    deleted = mgr.delete_file("new-file-789", permanent=False)
    assert deleted is True


def test_parse_csv_content():
    """Test parsing CSV with semicolons and skipping header."""
    from tools.google.solcast_sync import parse_csv_content

    raw_csv = """Datum; Zeit; Solcast_kWh; PV1_Total
2026-10-10; 17:59; 2,61; 0,3
2026-10-10; 18:59; 0,14; 0,1
"""
    rows = parse_csv_content(raw_csv)
    assert len(rows) == 2
    assert rows[0][0] == "2026-10-10"
    assert rows[0][1] == "17:59"
    assert rows[1][1] == "18:59"


def test_sync_solcast_data_mock():
    """Test syncing solcast rows to Google Sheets."""
    from tools.google.solcast_sync import sync_solcast_data

    mock_sheets = MagicMock()
    mock_values = mock_sheets.spreadsheets().values()
    # Mock current row count of Import as 100
    mock_values.get().execute.return_value = {"values": [["row"]] * 100}
    mock_values.append().execute.return_value = {"updates": {"updatedRows": 1}}
    mock_values.update().execute.return_value = {"updatedRows": 1}

    raw_csv = "2026-10-10; 17:59; 2,61; 0,3; 0,4; 0,0; 4,89; 253,77; False; partlycloudy; 13,6; 0,4; 1,0\n"

    with patch("tools.google.solcast_sync.get_services", return_value=(MagicMock(), mock_sheets)):
        res = sync_solcast_data(raw_csv)

    assert res["status"] == "success"
    assert res["rows_added"] == 1
    assert res["old_total_rows"] == 100
    assert res["new_total_rows"] == 101
