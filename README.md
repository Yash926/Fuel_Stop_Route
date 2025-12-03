# Fuel_Stop_Route

...existing code...

## Introduction
Fuel_Stop_Route is a lightweight Django-based utility that helps find fuel stops along a driving route and returns the cheapest stations by state. It combines CSV-based fuel price data with online geocoding (Nominatim) and routing (OSRM) to locate stops along a route and pick optimal refueling points. The project is intended as a backend prototype for route-aware fuel price lookups and demonstration of integrating public routing/geocoding APIs.

## Features
- Load fuel price data from a CSV and determine the cheapest station per state.
- Geocode place names or accept coordinate inputs.
- Use OSRM to compute driving routes and sample points along the route.
- Reverse-geocode coordinates to determine states for price lookup.
- Simple in-memory caching for geocoding and price lookups to speed up repeated requests.

## Contents
- api/utils.py — geocoding, reverse geocoding, OSRM routing helpers, CSV loader, geometry helpers
- fuel-prices-for-be-assessment.csv — source data (placed in project root)
- requirements.txt — Python dependencies
- README.md — this file

## Prerequisites
- Python 3.9+
- Linux (development/tested)
- Network access for Nominatim and OSRM APIs

## Setup
1. From project root:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Set a contact email for Nominatim (recommended to avoid 403/rate-limit issues):
   ```bash
   export NOMINATIM_EMAIL=you@example.com
   ```
3. Ensure `fuel-prices-for-be-assessment.csv` is present in the project root and includes headers like:
   - State
   - Retail Price
   - Truckstop Name
   - City
   - Address

## Run
Start the Django dev server:
```bash
python manage.py runserver
```
By default the server runs at http://127.0.0.1:8000.

## API testing (Postman / curl)
Check `urls.py` for real endpoint paths. Typical usage:

Example POST payload:
```json
{
  "start": "37.7749,-122.4194",
  "finish": "34.0522,-118.2437",
  "fuel_type": "Diesel"
}
```

curl example:
```bash
curl -X POST http://127.0.0.1:8000/api/route/ \
  -H "Content-Type: application/json" \
  -d '{"start":"37.7749,-122.4194","finish":"34.0522,-118.2437"}'
```

If geocoding fails you may see:
```json
{"error":"Could not geocode start or finish"}
```
Workarounds: pass coordinates directly, set `NOMINATIM_EMAIL`, or retry later.

## Troubleshooting
- "Could not geocode start or finish": ensure `NOMINATIM_EMAIL` is set, network access is available, or provide lat,lon directly.
- CSV load errors: verify file path and headers.
- Rate limits: Nominatim enforces limits; add delays and provide a contact email.

## Development tips
- In-memory caches in `api/utils.py` speed up repeated operations during a dev session.
- To avoid external API calls during testing, pass coordinates directly.
- Check the Django terminal for tracebacks and helpful log messages.

## License & Contact
- Adapt as needed for your use; default to MIT-style / internal use.
- Set `NOMINATIM_EMAIL` to a valid address when using public Nominatim to comply with usage policy.