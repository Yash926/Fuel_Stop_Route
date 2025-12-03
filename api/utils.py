import csv
import math
import threading
from pathlib import Path
import os
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "fuel-prices-for-be-assessment.csv"

# Simple in-memory caches
_prices_lock = threading.Lock()
_cheapest_by_state = None
_geocode_cache = {}

# Contact email to include with Nominatim requests (use env var to set your contact)
NOMINATIM_EMAIL = os.getenv('NOMINATIM_EMAIL', 'dev@example.com')


def load_prices():
    global _cheapest_by_state
    with _prices_lock:
        if _cheapest_by_state is not None:
            return _cheapest_by_state
        d = {}
        with open(CSV_PATH, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                state = (row.get('State') or '').strip()
                try:
                    price = float(row.get('Retail Price') or row.get('Retail Price', 0))
                except Exception:
                    continue
                if not state:
                    continue
                cur = d.get(state)
                if cur is None or price < cur['price']:
                    d[state] = {
                        'price': price,
                        'name': row.get('Truckstop Name'),
                        'city': row.get('City'),
                        'address': row.get('Address')
                    }
        _cheapest_by_state = d
        return d


def geocode_place(place):
    key = ('geocode', place)
    if key in _geocode_cache:
        return _geocode_cache[key]
    url = 'https://nominatim.openstreetmap.org/search'
    params = {'q': place, 'format': 'json', 'limit': 1, 'email': NOMINATIM_EMAIL}
    headers = {'User-Agent': f'FuelStopRoute/1.0 ({NOMINATIM_EMAIL})'}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.HTTPError as e:
        # Nominatim may return 403 if user-agent/email is missing or rate-limited
        _geocode_cache[key] = None
        return None
    except requests.exceptions.RequestException:
        _geocode_cache[key] = None
        return None
    if not data:
        _geocode_cache[key] = None
        return None
    item = data[0]
    res = {'lat': float(item['lat']), 'lon': float(item['lon']), 'display_name': item.get('display_name')}
    _geocode_cache[key] = res
    return res


def reverse_geocode(lat, lon):
    key = ('reverse', lat, lon)
    if key in _geocode_cache:
        return _geocode_cache[key]
    url = 'https://nominatim.openstreetmap.org/reverse'
    params = {'lat': lat, 'lon': lon, 'format': 'json', 'zoom': 5, 'addressdetails': 1, 'email': NOMINATIM_EMAIL}
    headers = {'User-Agent': f'FuelStopRoute/1.0 ({NOMINATIM_EMAIL})'}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.HTTPError:
        _geocode_cache[key] = None
        return None
    except requests.exceptions.RequestException:
        _geocode_cache[key] = None
        return None
    addr = data.get('address', {})
    state = addr.get('state') or addr.get('state_district') or addr.get('region')
    _geocode_cache[key] = state
    return state


def osrm_route(lon1, lat1, lon2, lat2):
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {'overview': 'full', 'geometries': 'geojson'}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def haversine_meters(a, b):
    # a,b are (lat, lon)
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    R = 6371000
    return 2 * R * math.asin(math.sqrt(math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2))


def point_along_line(coords, target_m):
    # coords is list of [lon, lat] from OSRM; return (lat, lon) at distance target_m from start
    if target_m <= 0:
        return (coords[0][1], coords[0][0])
    cum = 0.0
    for i in range(len(coords)-1):
        a = (coords[i][1], coords[i][0])
        b = (coords[i+1][1], coords[i+1][0])
        seg = haversine_meters(a, b)
        if cum + seg >= target_m:
            # interpolate
            remain = target_m - cum
            frac = remain / seg if seg else 0
            lat = a[0] + (b[0]-a[0]) * frac
            lon = a[1] + (b[1]-a[1]) * frac
            return (lat, lon)
        cum += seg
    # fallback: last point
    return (coords[-1][1], coords[-1][0])
