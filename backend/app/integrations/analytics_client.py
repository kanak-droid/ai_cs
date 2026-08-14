# Real HTTP client — pulls a saved analytics query's results as CSV (a
# Redash-style "results.csv?api_key=..." URL). Like sheets_client.py, this is
# never mocked: it's only ever called from the sync path (sheets_sync_service),
# never the live chat request path, so there's no MOCK_MODE short-circuit here.
import csv
import io

import httpx

_TIMEOUT_SECONDS = 30.0


def fetch_csv(url: str) -> list[dict[str, str]]:
    response = httpx.get(url, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    reader = csv.DictReader(io.StringIO(response.text))
    return list(reader)
