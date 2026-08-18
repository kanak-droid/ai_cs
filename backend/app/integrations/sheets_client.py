"""Real Google Sheets API client — reads the ops team's astrologer sheets.

Unlike everything else in app/integrations/, this is never mocked: it's only
ever called from the sync service (a script or an admin-triggered route),
never from the live chat request path, so there's no MOCK_MODE short-circuit
here the way payout_client.py etc. have one.

Rows come back as plain lists, not name-keyed dicts — some of these tabs
(the KYC tab, notably) repeat a column name like "Status" more than once in
the same header row, so a name lookup would silently pick whichever one a
dict happened to keep. The sync service maps columns by their fixed position
in the header row instead, having already been checked against the sheet.
"""

import time
from http.client import IncompleteRead
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.core.config import settings
from app.core.google_credentials import parse_service_account_json

_MAX_ATTEMPTS = 3

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _credentials_path() -> Path:
    path = Path(settings.GOOGLE_SHEETS_CREDENTIALS_PATH)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    return path


def _credentials_info_from_env() -> dict | None:
    """GOOGLE_SHEETS_CREDENTIALS_JSON — the credential file's content, for
    deployments (e.g. a k8s Secret) that hand us env vars, not files. See
    app/core/google_credentials.py for the actual (defensive) parsing."""
    return parse_service_account_json(settings.GOOGLE_SHEETS_CREDENTIALS_JSON)


def _get_service():
    info = _credentials_info_from_env()
    if info is not None:
        creds = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
        return build("sheets", "v4", credentials=creds)

    path = _credentials_path()
    if not path.exists():
        raise RuntimeError(
            f"Google Sheets service-account credentials not found at {path}, and "
            "GOOGLE_SHEETS_CREDENTIALS_JSON is not set — set one of the two."
        )
    creds = service_account.Credentials.from_service_account_file(str(path), scopes=_SCOPES)
    return build("sheets", "v4", credentials=creds)


def read_tab(
    spreadsheet_id: str, tab_title: str, header_row: int, max_rows: int = 20000
) -> tuple[list[str], list[list[str]]]:
    """Read one tab starting at header_row (1-indexed, as shown in the Sheets UI).

    Returns (header_row_values, data_rows) — each data row is padded/truncated
    to line up positionally with header_row_values isn't guaranteed (Sheets
    omits trailing empty cells), so callers must index defensively.
    """
    service = _get_service()
    range_ = f"'{tab_title}'!{header_row}:{header_row + max_rows}"
    request = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_)

    # Large tabs (thousands of rows) occasionally hit a transient socket
    # timeout/incomplete-read over this connection — a plain retry clears it
    # every time it's been observed to happen, so this isn't masking a real
    # bug, just absorbing an occasional slow/flaky read.
    last_error: Exception | None = None
    result = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            result = request.execute()
            break
        except (TimeoutError, OSError, IncompleteRead) as exc:
            last_error = exc
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(2**attempt)
    if result is None:
        raise last_error

    values = result.get("values", [])
    if not values:
        return [], []
    return values[0], values[1:]


def list_tab_titles(spreadsheet_id: str) -> list[str]:
    """Every tab's title in the spreadsheet, in whatever order the Sheets API
    returns them — not necessarily chronological, since ops adds each new
    payout cycle tab by hand. Used to auto-detect the latest payout cycle
    rather than requiring a manually-updated tab name in settings every
    time a new one is added (see sheets_sync_service._latest_payout_cycle).
    """
    service = _get_service()
    result = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id, fields="sheets.properties.title"
    ).execute()
    return [sheet["properties"]["title"] for sheet in result.get("sheets", [])]


def cell(row: list[str], index: int) -> str | None:
    """Sheets omits trailing empty cells, so a short row is normal, not an error."""
    if index < 0 or index >= len(row):
        return None
    value = row[index]
    return value if value != "" else None
