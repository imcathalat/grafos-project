from collections import defaultdict
import osmnx as ox
from geopy.geocoders import Nominatim
import heapq
import os
import math
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

geolocator = Nominatim(user_agent="geoapi")

def baixar_osm(place):
    import os
    import json
    os.makedirs('cache', exist_ok=True)
    filename = os.path.join('cache', f"{place.lower().replace(' ', '_').replace(',', '')}_osm.json")
    if os.path.exists(filename):
        print(f"Carregando OSM de cache para: {place}")
        with open(filename, 'r') as f:
            return json.load(f)

    print(f"Baixando OSM para: {place}")
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
    return osm_data

def construir_grafo(osm_json):
    nodes = {}
    ways = []
    for el in osm_json['elements']:
        if el['type']=='node':
            nodes[el['id']] = (el['lat'], el['lon'])
        elif el['type']=='way':
            ways.append(el)
    grafo = defaultdict(list)
    def haversine(a, b):
        lat1, lon1 = a; lat2, lon2 = b
        R = 6371000
        φ1, φ2 = math.radians(lat1), math.radians(lat2)
        Δφ = math.radians(lat2-lat1); Δλ = math.radians(lon2-lon1)
        d = 2*R*math.asin(math.sqrt(math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2))
        return d

    for way in ways:
        nds = way['nodes']
        oneway = way.get('tags', {}).get('oneway') in ['yes','true','1']
        for u, v in zip(nds, nds[1:]):
            if u in nodes and v in nodes:
                w = haversine(nodes[u], nodes[v])
                grafo[u].append((v, w))
                if not oneway:
                    grafo[v].append((u, w))
    return grafo, nodes

def get_coords(lugar):
    location = geolocator.geocode(lugar)
    if location:
        return (location.latitude, location.longitude)
    else:
        raise ValueError(f"Local não encontrado: {lugar}")

# def baixar_mapa(cidade):
#     slug = cidade.lower().replace(' ', '_').replace(',', '')
#     cache_dir = os.path.join('cache', 'maps')
#     os.makedirs(cache_dir, exist_ok=True)
#     gpkl_path = os.path.join(cache_dir, f'{slug}.gpickle')

#     if os.path.exists(gpkl_path):
#         print(f"Carregando grafo em cache: {gpkl_path}")
#         G = ox.load_graphml(gpkl_path)
#     else:
#         print(f"Baixando mapa de {cidade}...")
#         G = ox.graph_from_place(cidade, network_type='drive')
#         print(f"Salvando grafo em cache: {gpkl_path}")
#         ox.save_graphml(G, gpkl_path)

#     return G

def dijkstra(grafo, inicio, fim):
    all_nodes = set(grafo.keys())
    for adj in grafo.values():
        for viz, _ in adj:
            all_nodes.add(viz)

    dist = {n: float('inf') for n in all_nodes}
    prev = {n: None            for n in all_nodes}
    dist[inicio] = 0
    fila = [(0, inicio)]

    while fila:
        d_atual, atual = heapq.heappop(fila)
        if atual == fim:
            break
        for vizinho, peso in grafo.get(atual, []):
            nova_dist = d_atual + peso
            if nova_dist < dist[vizinho]:
                dist[vizinho] = nova_dist
                prev[vizinho] = atual
                heapq.heappush(fila, (nova_dist, vizinho))

    caminho = []
    u = fim
    while u is not None:
        caminho.insert(0, u)
        u = prev[u]
    return caminho, dist[fim]

def nearest_node(nodes_dict, coord):
    lat, lon = coord
    nearest = None
    min_dist = float('inf')
    for node_id, (node_lat, node_lon) in nodes_dict.items():
        d = math.hypot(lat - node_lat, lon - node_lon)
        if d < min_dist:
            min_dist = d
            nearest = node_id
    return nearest

def encontrar_rota(cidade, origem_nome, destino_nome):
    json = baixar_osm(cidade)
    grafo, nodes = construir_grafo(json)
    print("Geocodificando origem e destino...")
    origem_coords = get_coords(origem_nome)
    destino_coords = get_coords(destino_nome)
    origem_node = nearest_node(nodes, origem_coords)
    destino_node = nearest_node(nodes, destino_coords)
    print("Executando Dijkstra manual...")
    caminho, distancia = dijkstra(grafo, origem_node, destino_node)
    print(f"Distância total: {distancia:.2f} metros")
    return caminho


rota = encontrar_rota(
    "Belo Horizonte, Minas Gerais, Brazil",
    "Bairro Parque São Pedro, Belo Horizonte",
    "Avenida Afonso Pena, Belo Horizonte"
)
print("Caminho de nós:", rota)