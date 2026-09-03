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

import csv
import io
import re
import time
import urllib.request
from http.client import IncompleteRead
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.core.config import settings
from app.core.google_credentials import parse_service_account_json

_MAX_ATTEMPTS = 3

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Public-sheet fallback: when no service-account credential is configured but
# the sheet is shared "anyone with the link can view", it can still be read
# over the same unauthenticated CSV export / htmlview endpoints a browser uses.
# This keeps the sync runnable in local/dev without provisioning a service
# account, and is a no-op whenever a real credential IS set (see _get_service).
_PUBLIC_TIMEOUT = 30
_PUBLIC_UA = "Mozilla/5.0 (compatible; AstroHelpSheetsSync/1.0)"
_public_tab_gids: dict[str, dict[str, str]] = {}


def _has_service_account() -> bool:
    """True when a real Google credential is available (env JSON or file)."""
    if _credentials_info_from_env() is not None:
        return True
    return _credentials_path().exists()


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _PUBLIC_UA})
    with urllib.request.urlopen(req, timeout=_PUBLIC_TIMEOUT) as resp:  # noqa: S310 (fixed https host)
        return resp.read().decode("utf-8", "replace")


def _public_tab_gid_map(spreadsheet_id: str) -> dict[str, str]:
    """{tab_title: gid} for a public spreadsheet, parsed from its htmlview page
    (the same JSON blob the Sheets htmlview UI builds its tab bar from). Cached
    per spreadsheet id for the process's lifetime.
    """
    cached = _public_tab_gids.get(spreadsheet_id)
    if cached is not None:
        return cached
    html = _http_get(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/htmlview")
    gids = re.findall(r'gid: "(\d+)",initialSheet', html)
    names = re.findall(r'items\.push\(\{name: "((?:[^"\\]|\\.)*)"', html)
    unescape = lambda s: re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), s)
    mapping = {unescape(n): g for g, n in zip(gids, names)}
    _public_tab_gids[spreadsheet_id] = mapping
    return mapping


def _public_read_tab(
    spreadsheet_id: str, tab_title: str, header_row: int, max_rows: int
) -> tuple[list[str], list[list[str]]]:
    gid = _public_tab_gid_map(spreadsheet_id).get(tab_title)
    if gid is None:
        raise RuntimeError(
            f"Public spreadsheet {spreadsheet_id} has no tab titled {tab_title!r} "
            f"(available: {sorted(_public_tab_gid_map(spreadsheet_id))[:15]})"
        )
    text = _http_get(
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    )
    all_rows = list(csv.reader(io.StringIO(text)))
    # header_row is 1-indexed (as shown in the Sheets UI); mirror the
    # authenticated path's "header line + data lines" return shape.
    window = all_rows[header_row - 1 : header_row - 1 + max_rows + 1]
    if not window:
        return [], []
    return window[0], window[1:]


def _public_list_tab_titles(spreadsheet_id: str) -> list[str]:
    return list(_public_tab_gid_map(spreadsheet_id))


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
    if not _has_service_account():
        return _public_read_tab(spreadsheet_id, tab_title, header_row, max_rows)

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
    if not _has_service_account():
        return _public_list_tab_titles(spreadsheet_id)

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
