API app for Fuel Stop Route assessment.

Endpoints:
- `GET /api/route/?start=ORIGIN&finish=DEST` - returns route geojson, stops and cost estimate.

Notes:
- Uses Nominatim (OpenStreetMap) for geocoding and project-osrm.org for routing.
- The CSV `fuel-prices-for-be-assessment.csv` is used to select cheapest station per state.
