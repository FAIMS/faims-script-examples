# Python examples

Python demos for calling FAIMS3 REST APIs with a [long-lived API token](https://github.com/FAIMS/FAIMS3/blob/main/docs/developer/docs/source/markdown/Long-lived-tokens.md).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (manages Python and dependencies)
- A FAIMS3 deployment with the Conductor API reachable from your machine
- A long-lived API token and a project (notebook) ID you can read

## Setup

```bash
cd python
cp .env.example .env
# Edit .env with your API URL, token, and project ID
uv sync
```

## Scripts

### `fetch_records_demo.py`

Read-only demo of the [Records CRUD API](https://github.com/FAIMS/FAIMS3/blob/main/docs/developer/docs/source/markdown/RecordsCRUDApi.md):

1. Exchanges the long-lived token for a short-lived access token
2. Lists record metadata (`GET /api/notebooks/:id/records/metadata`)
3. Fetches full data for one record (`GET /api/notebooks/:id/records/:recordId`)

```bash
uv run fetch_records_demo.py
uv run fetch_records_demo.py --limit 10
uv run fetch_records_demo.py --record-id rec-abc123
uv run fetch_records_demo.py --form-id FORM2
```

CLI flags override values from `.env`.

## Authentication flow

Long-lived tokens are not sent on every API call. Exchange them for a short-lived Bearer token first:

```
Long-lived token  →  POST /api/auth/exchange-long-lived-token  →  Bearer token  →  API calls
```

Access tokens expire after about five minutes; the demo refreshes automatically.
