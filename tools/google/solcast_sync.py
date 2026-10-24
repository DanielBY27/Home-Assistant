"""Solcast Data Sync & Damp Factor calculation logic."""

import csv
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.google.auth import get_services

SPREADSHEET_ID = "1Iq5dkjayb4yvALm_uNDdIcQKYLmsaXzeTYg05pACqgQ"

GERMAN_MONTHS = {
    1: "Januar",
    2: "Februar",
    3: "März",
    4: "April",
    5: "Mai",
    6: "Juni",
    7: "Juli",
    8: "August",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Dezember",
}


def parse_csv_content(content: str) -> List[List[str]]:
    """Parses semicolon- or comma-separated CSV text into cleaned rows."""
    rows = []
    lines = content.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Split by semicolon if present, else comma
        delim = ";" if ";" in line else ","
        parts = [p.strip() for p in line.split(delim)]
        # Skip header if it starts with 'Datum'
        if parts and parts[0].lower() in ("datum", "date"):
            continue
        if len(parts) >= 2:  # valid row with at least Datum and Zeit
            rows.append(parts)
    return rows


def sync_solcast_data(csv_content: str) -> Dict[str, Any]:
    """Appends CSV rows to 'Import' and expands formulas in 'Auswertung'."""
    new_rows = parse_csv_content(csv_content)
    if not new_rows:
        return {"status": "no_data", "message": "Keine neuen Daten im CSV gefunden.", "rows_added": 0}

    _, sheets = get_services()

    # 1. Determine current row count of Import
    imp_meta = (
        sheets.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range="Import!A:A")
        .execute()
    )
    old_rows = len(imp_meta.get("values", []))

    # 2. Append new rows to Import
    append_res = (
        sheets.spreadsheets()
        .values()
        .append(
            spreadsheetId=SPREADSHEET_ID,
            range="Import!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": new_rows},
        )
        .execute()
    )

    new_total_rows = old_rows + len(new_rows)

    # 3. Expand formulas in Auswertung for new rows
    formulas = []
    for r in range(old_rows + 1, new_total_rows + 1):
        formulas.append(
            [
                f"=Import!A{r}",
                f'=TEXT(A{r}; "MMMM")',
                f"=Import!B{r}",
                f"=SUM(Import!D{r}:F{r})",
                f"=Import!C{r} / MAX(0,01; Import!M{r})",
                f"=if(Import!M{r} = 0; 0,1; if(E{r} > 0,1; MIN(1; D{r} / E{r}); 1))",
                f"=Import!J{r}",
                f"=Import!M{r}",
            ]
        )

    if formulas:
        sheets.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"Auswertung!A{old_rows + 1}:H{new_total_rows}",
            valueInputOption="USER_ENTERED",
            body={"values": formulas},
        ).execute()

    return {
        "status": "success",
        "rows_added": len(new_rows),
        "old_total_rows": old_rows,
        "new_total_rows": new_total_rows,
    }


def get_pivot_damp_factors(month_number: Optional[int] = None) -> Dict[str, Any]:
    """Reads 'Pivot-Tabelle 1' and extracts the damp factors for the specified month."""
    if month_number is None:
        month_number = datetime.now().month

    target_month_name = GERMAN_MONTHS.get(month_number, "Oktober")
    _, sheets = get_services()

    # Ensure target_month_name is expanded (not collapsed) in Pivot-Tabelle 1
    meta = (
        sheets.spreadsheets()
        .get(
            spreadsheetId=SPREADSHEET_ID,
            ranges=["'Pivot-Tabelle 1'!A1:B20"],
            includeGridData=True,
        )
        .execute()
    )
    for s in meta.get("sheets", []):
        if s.get("properties", {}).get("title") == "Pivot-Tabelle 1":
            sheet_id = s["properties"]["sheetId"]
            grid = s.get("data", [{}])[0].get("rowData", [])
            if grid and grid[0].get("values") and "pivotTable" in grid[0]["values"][0]:
                pt = grid[0]["values"][0]["pivotTable"]
                needs_update = False
                for vm in pt.get("rows", [{}])[0].get("valueMetadata", []):
                    val = vm.get("value", {}).get("stringValue", "")
                    should_collapse = not val.lower().startswith(target_month_name.lower())
                    if vm.get("collapsed") != should_collapse:
                        vm["collapsed"] = should_collapse
                        needs_update = True
                if needs_update:
                    req = {
                        "updateCells": {
                            "rows": [{"values": [{"pivotTable": pt}]}],
                            "start": {"sheetId": sheet_id, "rowIndex": 0, "columnIndex": 0},
                            "fields": "pivotTable",
                        }
                    }
                    sheets.spreadsheets().batchUpdate(
                        spreadsheetId=SPREADSHEET_ID, body={"requests": [req]}
                    ).execute()

    pivot_data = (
        sheets.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range="'Pivot-Tabelle 1'!A1:N60")
        .execute()
        .get("values", [])
    )

    # Find the block for target_month_name
    # Header format: row 2 has weathers, row 3 has 'Damp ALT', 'Damp NEU'
    hourly_factors: Dict[str, Dict[str, str]] = {}
    in_target_month = False

    for row in pivot_data[3:]:  # Skip headers (rows 1-3)
        if not row:
            continue
        col_month = row[0].strip() if len(row) > 0 and row[0] else ""
        col_time = row[1].strip() if len(row) > 1 and row[1] else ""

        # Check if new month starts
        if col_month:
            if col_month.lower().startswith(target_month_name.lower()):
                in_target_month = True
            else:
                if in_target_month:
                    # We left the target month block
                    break
                in_target_month = False

        if in_target_month and col_time:
            # Extract hour, e.g. "07:59" -> "7"
            hour_match = re.match(r"^0?(\d+):", col_time)
            hour_key = hour_match.group(1) if hour_match else col_time
            # Store row details
            hourly_factors[hour_key] = {
                "time": col_time,
                "values": row[2:] if len(row) > 2 else [],
            }

    return {
        "month_number": month_number,
        "month_name": target_month_name,
        "hourly_factors": hourly_factors,
        "raw_pivot": pivot_data,
    }
