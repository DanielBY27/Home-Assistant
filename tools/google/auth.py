"""Authentication helper for Google Drive & Sheets APIs."""

import json
import os
from pathlib import Path
from typing import Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

# Full permissions for Drive and Sheets (read, write, create, delete)
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_base_dir() -> Path:
    """Returns the base project directory."""
    # Try current directory first, or parent of tools
    cwd = Path.cwd()
    if (cwd / "credentials").exists() or (cwd / "tests").exists():
        return cwd
    return Path(__file__).resolve().parent.parent.parent


def get_credentials_dir() -> Path:
    """Returns the credentials directory path."""
    creds_dir = get_base_dir() / "credentials"
    creds_dir.mkdir(parents=True, exist_ok=True)
    return creds_dir


def find_service_account_file() -> Optional[Path]:
    """Finds a service account JSON file in the credentials directory."""
    env_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_creds and Path(env_creds).exists():
        return Path(env_creds)

    creds_dir = get_credentials_dir()
    sa_default = creds_dir / "service_account.json"
    if sa_default.exists():
        return sa_default

    # Scan for any json file containing "type": "service_account"
    for json_file in creds_dir.glob("*.json"):
        if json_file.name in ("token.json", "client_secret.json"):
            continue
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data.get("type") == "service_account":
                    return json_file
        except Exception:
            continue

    return None


def find_client_secret_file() -> Optional[Path]:
    """Finds an OAuth client secret JSON file."""
    creds_dir = get_credentials_dir()
    cs_default = creds_dir / "client_secret.json"
    if cs_default.exists():
        return cs_default

    for json_file in creds_dir.glob("*.json"):
        if json_file.name in ("token.json", "service_account.json"):
            continue
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and ("installed" in data or "web" in data):
                    return json_file
        except Exception:
            continue

    return None


def get_credentials():
    """Retrieves authenticated Google credentials (Service Account or OAuth2)."""
    # 1. Try Service Account (preferred for Docker / headless environments)
    sa_file = find_service_account_file()
    if sa_file:
        return service_account.Credentials.from_service_account_file(
            str(sa_file), scopes=SCOPES
        )

    # 2. Try existing OAuth token
    creds_dir = get_credentials_dir()
    token_file = creds_dir / "token.json"
    creds = None

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if creds and creds.valid:
        return creds

    # Refresh expired OAuth token if possible
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_file, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            return creds
        except Exception as e:
            print(f"Warning: Failed to refresh token: {e}")

    # No valid credentials found
    client_secret_file = find_client_secret_file()
    hint_client = f"\n- OAuth Client Secret found at {client_secret_file.name}. Run 'python -m tools.google.cli auth' to authorize." if client_secret_file else ""

    raise FileNotFoundError(
        f"Keine gültigen Google-Zugangsdaten gefunden!\n"
        f"Bitte hinterlegen Sie Ihre Zugangsdaten in '{creds_dir}':\n"
        f"- Option 1 (Empfohlen für Docker): Service-Account Schlüsseldatei als 'service_account.json'\n"
        f"- Option 2: OAuth 2.0 Client Secret als 'client_secret.json'{hint_client}\n"
        f"Siehe credentials/README.md für Details."
    )


def run_oauth_flow(port: int = 8080) -> Credentials:
    """Runs interactive OAuth 2.0 flow to create credentials/token.json."""
    client_secret_file = find_client_secret_file()
    if not client_secret_file:
        raise FileNotFoundError(
            f"Keine 'client_secret.json' in '{get_credentials_dir()}' gefunden. "
            f"Bitte laden Sie die OAuth-Client-ID JSON aus der Google Cloud Console herunter."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secret_file), SCOPES
    )
    print(f"\nStarte OAuth 2.0 Autorisierungs-Server auf Port {port}...")
    print(f"Falls ein Browser nicht automatisch öffnet, kopieren Sie den Link in Ihren Browser auf dem Host:")

    creds = flow.run_local_server(
        host="0.0.0.0",
        port=port,
        open_browser=False,
        bind_addr="0.0.0.0"
    )

    token_file = get_credentials_dir() / "token.json"
    with open(token_file, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    print(f"Erfolgreich autorisiert! Token gespeichert unter: {token_file}")
    return creds


def get_services() -> Tuple[Resource, Resource]:
    """Returns initialized (drive_service, sheets_service) instances."""
    creds = get_credentials()
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return drive, sheets
