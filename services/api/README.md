# API Service

Lightweight backend service for the MVP.

## Responsibilities

- load live data when available;
- fall back to `data/sample/`;
- compute factors;
- select strategy;
- build explanation fields;
- prepare or submit Mantle signal records.

## MVP Endpoints

- `GET /api/health`
- `GET /api/assets`
- `POST /api/analyze`
- `POST /api/record-signal`
- `GET /api/demo/sample`

The unprefixed routes are also available for local development and API docs, but
the frontend uses `/api/*` so a single public service can host both UI and API.
