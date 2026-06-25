#!/usr/bin/env python3
"""
Demonstrate fetching FAIMS records via the read-only Records REST API.

Uses a long-lived API token (from Profile -> Manage API Tokens in the web UI).
The token is exchanged for a short-lived access token before each API session.

Configuration is loaded from `.env` in this directory (see `.env.example`).

Examples:
  cp .env.example .env   # then edit with your values
  uv run fetch_records_demo.py
  uv run fetch_records_demo.py --limit 10 --record-id rec-abc123
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


class FaimsClient:
    """Minimal client: exchange long-lived token, then call read-only record routes."""

    def __init__(self, base_url: str, long_lived_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.long_lived_token = long_lived_token
        self._access_token: str | None = None
        self._token_expiry = 0.0

    def exchange_token(self) -> str:
        """POST /api/auth/exchange-long-lived-token -> short-lived Bearer token."""
        data = self._request_json(
            "POST",
            "/api/auth/exchange-long-lived-token",
            body={"token": self.long_lived_token},
            auth=False,
        )
        self._access_token = data["token"]
        # Access tokens expire after ~5 minutes; refresh a minute early.
        self._token_expiry = time.time() + 4 * 60
        return self._access_token

    def get_access_token(self) -> str:
        if not self._access_token or time.time() >= self._token_expiry:
            self.exchange_token()
        return self._access_token  # type: ignore[return-value]

    def list_record_metadata(
        self,
        project_id: str,
        *,
        limit: int | None = None,
        form_id: str | None = None,
    ) -> dict[str, Any]:
        """GET /api/notebooks/:id/records/metadata"""
        params: dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        if form_id:
            params["formId"] = form_id
        return self._request_json(
            "GET",
            f"/api/notebooks/{project_id}/records/metadata",
            params=params,
        )

    def get_record(self, project_id: str, record_id: str) -> dict[str, Any]:
        """GET /api/notebooks/:id/records/:recordId"""
        return self._request_json(
            "GET",
            f"/api/notebooks/{project_id}/records/{record_id}",
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        auth: bool = True,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = {"Accept": "application/json"}
        data: bytes | None = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        if auth:
            headers["Authorization"] = f"Bearer {self.get_access_token()}"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise SystemExit(f"HTTP {exc.code} {method} {path}: {detail}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch FAIMS records using the read-only REST API"
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("FAIMS_API_URL", "http://localhost:8080"),
        help="Conductor API base URL",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("FAIMS_LONG_LIVED_TOKEN"),
        help="Long-lived API token (or set FAIMS_LONG_LIVED_TOKEN in .env)",
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("FAIMS_PROJECT_ID"),
        help="Notebook / project ID (or set FAIMS_PROJECT_ID in .env)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max records to list (default: 5)",
    )
    parser.add_argument(
        "--form-id",
        help="Optional form/viewset ID filter for metadata listing",
    )
    parser.add_argument(
        "--record-id",
        help="Fetch a specific record; otherwise fetches the first listed record",
    )
    args = parser.parse_args()

    if not args.token:
        sys.exit("Error: set FAIMS_LONG_LIVED_TOKEN in .env or pass --token")
    if not args.project_id:
        sys.exit("Error: set FAIMS_PROJECT_ID in .env or pass --project-id")

    client = FaimsClient(args.api_url, args.token)

    print(f"Listing up to {args.limit} records in project {args.project_id}...")
    metadata = client.list_record_metadata(
        args.project_id,
        limit=args.limit,
        form_id=args.form_id,
    )
    records = metadata.get("records", [])
    print(f"Found {len(records)} record(s)\n")

    for rec in records:
        print(
            f"  {rec['recordId']}  "
            f"type={rec['type']}  "
            f"updated={rec['updated']}"
        )

    record_id = args.record_id or (records[0]["recordId"] if records else None)
    if not record_id:
        print("\nNo records to fetch.")
        return

    print(f"\nFetching full data for {record_id}...")
    record = client.get_record(args.project_id, record_id)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
