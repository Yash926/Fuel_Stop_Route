import math
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from . import utils


MPG = 10.0
RANGE_MILES = 500.0


@require_http_methods(["GET"])
def route_view(request):
    start = request.GET.get('start')
    finish = request.GET.get('finish')
    if not start or not finish:
        return JsonResponse({'error': 'Provide start and finish query parameters'}, status=400)

    # geocode start/finish
    s = utils.geocode_place(f"{start}, USA")
    f = utils.geocode_place(f"{finish}, USA")
    if s is None or f is None:
        return JsonResponse({'error': 'Could not geocode start or finish'}, status=400)

    # call OSRM once
    route = utils.osrm_route(s['lon'], s['lat'], f['lon'], f['lat'])
    routes = route.get('routes') or []
    if not routes:
        return JsonResponse({'error': 'Routing failed'}, status=500)
    r0 = routes[0]
    distance_m = r0.get('distance', 0.0)
    distance_miles = distance_m / 1609.34
    geometry = r0.get('geometry')

    # load cheapest per state
    cheapest = utils.load_prices()

    # compute stop points every RANGE_MILES
    stops = []
    if distance_miles > RANGE_MILES:
        # create stop distances at multiples of RANGE_MILES up to distance - small epsilon
        mult = 1
        while mult * RANGE_MILES < distance_miles:
            stops.append({'target_miles': mult * RANGE_MILES})
            mult += 1

    # for each stop find coordinate and state, then pick cheapest in that state
    chosen_stops = []
    prev_m = 0.0
    coords = geometry.get('coordinates') if geometry else []
    for si, sstop in enumerate(stops):
        target_m = sstop['target_miles'] * 1609.34
        latlon = utils.point_along_line(coords, target_m)
        state = utils.reverse_geocode(latlon[0], latlon[1])
        state_abbr = None
        if state:
            # try to match by abbreviation in cheapest dict
            if state in cheapest:
                state_abbr = state
            else:
                # try mapping full state name to abbreviation (simple match by uppercase)
                # where CSV uses abbreviations, we check keys for a match by name
                for k in cheapest.keys():
                    if k.lower() == (state or '').lower() or (state or '').lower().startswith(k.lower()):
                        state_abbr = k
                        break
        if state_abbr is None and cheapest:
            # fallback: choose globally cheapest
            state_abbr = min(cheapest.keys(), key=lambda x: cheapest[x]['price'])

        station = cheapest.get(state_abbr)
        station_coord = None
        if station:
            # geocode station city+state
            place = f"{station.get('city')}, {state_abbr}, USA"
            geo = utils.geocode_place(place)
            if geo:
                station_coord = {'lat': geo['lat'], 'lon': geo['lon']}

        # compute segment length from prev to this stop
        seg_miles = sstop['target_miles'] - prev_m
        prev_m = sstop['target_miles']
        chosen_stops.append({
            'index': si + 1,
            'distance_from_start_miles': sstop['target_miles'],
            'coord': {'lat': latlon[0], 'lon': latlon[1]},
            'state': state,
            'chosen_state_abbr': state_abbr,
            'station': station,
            'station_coord': station_coord,
            'segment_miles': seg_miles,
        })

    # compute costs: assume vehicle starts full (no purchase at origin).
    total_cost = 0.0
    total_gallons = distance_miles / MPG if MPG > 0 else 0.0
    stops_sequence = chosen_stops

    if not stops_sequence:
        # No refuel stops required: estimate cost by using cheapest station in the start state if available,
        # otherwise fall back to globally cheapest price from the CSV.
        start_state = utils.reverse_geocode(s['lat'], s['lon'])
        chosen_price = None
        if start_state and cheapest.get(start_state):
            chosen_price = cheapest[start_state]['price']
        else:
            # global cheapest
            if cheapest:
                chosen_price = min((v['price'] for v in cheapest.values()))
        total_cost = round(total_gallons * (chosen_price or 0.0), 2)
    else:
        # For each stop, buy enough to reach the next stop or finish. This is a greedy approximation.
        for i, cs in enumerate(stops_sequence):
            next_miles = distance_miles if i == len(stops_sequence)-1 else stops_sequence[i+1]['distance_from_start_miles']
            # miles to cover after fueling at this stop
            need_miles = next_miles - cs['distance_from_start_miles']
            gallons = max(0.0, need_miles / MPG)
            price = 0.0
            if cs.get('station') and isinstance(cs['station'].get('price'), (int, float)):
                price = cs['station']['price']
            total_cost += gallons * price
        total_cost = round(total_cost, 2)

    result = {
        'distance_miles': round(distance_miles, 2),
        'route_geojson': geometry,
        'stops': stops_sequence,
        'estimated_total_fuel_gallons': round(total_gallons, 2),
        'estimated_total_cost': total_cost
    }
    return JsonResponse(result, json_dumps_params={'indent': 2})


def frontend(request):
    # Serve the simple map frontend
    return render(request, 'api/index.html')
