# Fuel Stop Route API

Minimal Django API that accepts `start` and `finish` locations (within USA) and returns a route (GeoJSON), suggested fuel stops based on a 500-mile range, and an estimated fuel cost assuming 10 mpg.

Quick start

1. Create a virtualenv and install requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the server:

```bash
python manage.py runserver 0.0.0.0:8000
```

3. Example request:

```bash
curl "http://127.0.0.1:8000/api/route/?start=San+Francisco,CA&finish=Los+Angeles,CA"
```

Notes
- Uses Nominatim (OpenStreetMap) for geocoding and `router.project-osrm.org` for routing.
- The implementation minimizes external calls: one OSRM route call plus a few geocode/reverse-geocode calls per request.
- The CSV `fuel-prices-for-be-assessment.csv` is used to pick the cheapest station per state (no per-station exhaustive geocoding).

Important: Nominatim requires a valid contact. Set the environment variable `NOMINATIM_EMAIL` to your email before running the server, for example:

```bash
export NOMINATIM_EMAIL="your-email@example.com"
python manage.py runserver 0.0.0.0:8000
```

If you don't set this, the app uses a default contact but you may still get HTTP 403 responses from Nominatim if rate-limited.
