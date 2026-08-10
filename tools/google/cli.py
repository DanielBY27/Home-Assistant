"""Command-line interface for Google Drive & Google Sheets operations."""

import argparse
import json
import sys
from tools.google.auth import get_credentials_dir, run_oauth_flow
from tools.google.drive_sheets import GoogleDriveSheetsManager


def cmd_auth(args):
    """Executes the OAuth2 interactive login."""
    print("Starte interaktiven OAuth 2.0 Login...")
    try:
        run_oauth_flow(port=args.port)
        print("Authentifizierung erfolgreich abgeschlossen!")
    except Exception as e:
        print(f"Fehler bei Authentifizierung: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_read_sheet(args):
    """Reads rows from a Google Sheet."""
    try:
        mgr = GoogleDriveSheetsManager()
        rows = mgr.read_sheet(args.id, args.range)
        if not rows:
            print("Keine Daten in diesem Bereich gefunden.")
            return

        print(f"\n--- Gefundene Zeilen ({len(rows)}) aus '{args.range}' ---")
        for i, row in enumerate(rows, start=1):
            print(f"Zeile {i}: {row}")
    except Exception as e:
        print(f"\nFehler beim Lesen des Google Sheets: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_list_files(args):
    """Lists files in Google Drive."""
    try:
        mgr = GoogleDriveSheetsManager()
        files = mgr.list_files(query=args.query, page_size=args.limit)
        print(f"\n--- Google Drive Dateien ({len(files)}) ---")
        for f in files:
            size_str = f" ({f.get('size')} Bytes)" if "size" in f else ""
            print(f"- [{f.get('mimeType')}] {f.get('name')} (ID: {f.get('id')}){size_str}")
    except Exception as e:
        print(f"\nFehler beim Auflisten der Dateien: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_create_sheet(args):
    """Creates a new Google Sheet."""
    try:
        mgr = GoogleDriveSheetsManager()
        f = mgr.create_file(
            name=args.name,
            mime_type="application/vnd.google-apps.spreadsheet",
            folder_id=args.folder,
        )
        print(f"\nGoogle Sheet erfolgreich erstellt:")
        print(f"Name: {f.get('name')}")
        print(f"ID:   {f.get('id')}")
        if f.get("webViewLink"):
            print(f"Link: {f.get('webViewLink')}")
    except Exception as e:
        print(f"\nFehler beim Erstellen der Datei: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_delete_file(args):
    """Deletes a file from Google Drive."""
    try:
        mgr = GoogleDriveSheetsManager()
        mgr.delete_file(args.id, permanent=args.permanent)
        action = "endgültig gelöscht" if args.permanent else "in den Papierkorb verschoben"
        print(f"Datei '{args.id}' wurde erfolgreich {action}.")
    except Exception as e:
        print(f"\nFehler beim Löschen der Datei: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_sync_solcast(args):
    """Synchronizes CSV data into Google Sheets (Import + Auswertung)."""
    from tools.google.solcast_sync import sync_solcast_data

    content = ""
    if args.csv_file:
        with open(args.csv_file, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        if not sys.stdin.isatty():
            content = sys.stdin.read()

    if not content.strip():
        print("Keine Daten empfangen. Bitte --csv-file angeben oder Daten über stdin übergeben.")
        sys.exit(0)

    try:
        res = sync_solcast_data(content)
        if res.get("status") == "no_data":
            print(res.get("message"))
        else:
            print(f"Erfolg: {res.get('rows_added')} Zeilen in 'Import' eingefügt.")
            print(f"Formeln in 'Auswertung' erweitert (Zeilen {res.get('old_total_rows')+1} bis {res.get('new_total_rows')}).")
    except Exception as e:
        print(f"Fehler beim Synchronisieren: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_get_pivot(args):
    """Reads damp factors from Pivot-Tabelle 1."""
    from tools.google.solcast_sync import get_pivot_damp_factors

    try:
        res = get_pivot_damp_factors(month_number=args.month)
        print(f"\n--- Pivot-Tabelle 1: Dämpfungsfaktoren für {res['month_name']} (Monat {res['month_number']}) ---")
        hourly = res["hourly_factors"]
        if not hourly:
            print(f"Keine stündliche Aufschlüsselung für '{res['month_name']}' gefunden.")
            return

        print(f"{'Stunde':<8} | {'Zeit':<8} | {'Werte (Damp ALT / Damp NEU je Wetter)':<40}")
        print("-" * 70)
        for h in sorted(hourly.keys(), key=lambda x: int(x) if x.isdigit() else 99):
            row_data = hourly[h]
            vals_str = " | ".join(row_data["values"])
            print(f"{h:<8} | {row_data['time']:<8} | {vals_str}")
    except Exception as e:
        print(f"Fehler beim Lesen der Pivot-Tabelle: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Google Drive & Sheets Tool für Home-Assistant Projekt"
    )
    subparsers = parser.add_subparsers(dest="command", help="Verfügbare Befehle")

    # auth
    parser_auth = subparsers.add_parser("auth", help="OAuth 2.0 Browser-Login ausführen")
    parser_auth.add_argument("--port", type=int, default=8080, help="Lokaler Port (Default: 8080)")

    # read-sheet
    parser_read = subparsers.add_parser("read-sheet", help="Daten aus Google Sheet lesen")
    parser_read.add_argument("--id", required=True, help="Google Sheet ID")
    parser_read.add_argument("--range", default="Import!A1:Z5", help="Bereich (z. B. 'Import!A1:E5')")

    # list-files
    parser_list = subparsers.add_parser("list-files", help="Dateien in Google Drive auflisten")
    parser_list.add_argument("--query", default="", help="Suchfilter (z. B. mimeType = 'application/vnd.google-apps.spreadsheet')")
    parser_list.add_argument("--limit", type=int, default=50, help="Maximale Anzahl (Default: 50)")

    # create-sheet
    parser_create = subparsers.add_parser("create-sheet", help="Neues Google Sheet erstellen")
    parser_create.add_argument("--name", required=True, help="Name der Tabelle")
    parser_create.add_argument("--folder", default=None, help="Optionale Ordner-ID")

    # delete-file
    parser_del = subparsers.add_parser("delete-file", help="Datei löschen oder in den Papierkorb verschieben")
    parser_del.add_argument("--id", required=True, help="Google Drive Datei-ID")
    parser_del.add_argument("--permanent", action="store_true", help="Endgültig löschen statt Papierkorb")

    # sync-solcast
    parser_sync = subparsers.add_parser("sync-solcast", help="CSV-Daten in 'Import' & 'Auswertung' synchronisieren")
    parser_sync.add_argument("--csv-file", default=None, help="Pfad zur CSV-Datei (oder stdin verwenden)")

    # get-pivot
    parser_pivot = subparsers.add_parser("get-pivot", help="Dämpfungsfaktoren aus Pivot-Tabelle 1 auslesen")
    parser_pivot.add_argument("--month", type=int, default=None, help="Monatsnummer 1-12 (Default: aktueller Monat)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "auth":
        cmd_auth(args)
    elif args.command == "read-sheet":
        cmd_read_sheet(args)
    elif args.command == "list-files":
        cmd_list_files(args)
    elif args.command == "create-sheet":
        cmd_create_sheet(args)
    elif args.command == "delete-file":
        cmd_delete_file(args)
    elif args.command == "sync-solcast":
        cmd_sync_solcast(args)
    elif args.command == "get-pivot":
        cmd_get_pivot(args)


if __name__ == "__main__":
    main()
