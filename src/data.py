import json
import os
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

class Data:
    def filter_json_with_nodes(self, shortest_path):
        with open(self.filename, 'r') as file:
            data = json.load(file)

        json_filtrado = {
            "elements": [
                element for element in data["elements"]
                if element["id"] in shortest_path
            ]
        }
        return json_filtrado
    
    def baixar_osm(self, place):
        os.makedirs('cache', exist_ok=True)
        filename = os.path.join('cache', f"{place.lower().replace(' ', '_').replace(',', '')}_osm.json")
        from geopy.geocoders import Nominatim
        geo = Nominatim(user_agent="geoapi")
        loc = geo.geocode(place, exactly_one=True)
        south, north, west, east = map(float, loc.raw['boundingbox'])
        query = f"""
            [out:json][timeout:25];
            (
              way["highway"]({south},{west},{north},{east});
            );
            out body;
            >;
            out skel qt;
        """
        resp = requests.get(OVERPASS_URL, params={'data': query})
        resp.raise_for_status()
        osm_data = resp.json()
        with open(filename, 'w') as f:
            json.dump(osm_data, f)
        return osm_data, filename

    def get_json(self, filename):
        with open(filename, 'r') as file:
            return json.load(file)
