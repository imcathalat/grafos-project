from collections import defaultdict
from geopy.geocoders import Nominatim
import heapq
import math
from data import Data

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

geolocator = Nominatim(user_agent="geoapi")

class Graph:
    def construir_grafo(self, osm_json):
        """
        Constrói um grafo de adjacência a partir de um JSON do OpenStreetMap.
        Parâmetros
        ----------
        osm_json : dict
            Estrutura JSON contendo elementos de tipo 'node' e 'way' obtidos da API do OSM.
        Retorna
        -------
        grafo : defaultdict(list)
            Grafo representado como dicionário: cada chave é o ID de um nó e o valor é uma lista de tuplas
            (ID_vizinho, distância_em_metros) correspondendo às arestas.
        nodes : dict
            Dicionário que mapeia o ID de cada nó para uma tupla (latitude, longitude).
        """
        nodes = {}
        ways = []
        for el in osm_json['elements']:
            if el['type']=='node':
                nodes[el['id']] = (el['lat'], el['lon'])
            elif el['type']=='way':
                ways.append(el)
        grafo = defaultdict(list)
        def haversine(a, b):
            """
            Calcula a distância em metros entre dois pontos na superfície terrestre
            usando a fórmula de Haversine.

            Parâmetros:
                a (tuple[float, float]): Tupla (latitude, longitude) do ponto de origem em graus.
                b (tuple[float, float]): Tupla (latitude, longitude) do ponto de destino em graus.

            Retorna:
                float: Distância entre os pontos em metros.
            """
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

    def get_coords(self, lugar):
        location = geolocator.geocode(lugar)
        if location:
            return (location.latitude, location.longitude)
        else:
            return None

    def dijkstra(self, grafo: dict, inicio, fim):
        """
        Executa o algoritmo de Dijkstra para encontrar o caminho de custo mínimo entre dois nós.
        Parâmetros
        ----------
        grafo : dict
            Dicionário que mapeia cada nó para uma lista de tuplas (vizinho, peso),
            representando as arestas e seus respectivos custos.
        inicio : hashable
            Nó de partida (origem) para a busca do caminho.
        fim : hashable
            Nó de destino para o qual se deseja encontrar o caminho mínimo.
        Retorna
        -------
        tuple
            Uma tupla (caminho, distancia):
              - caminho (list): lista de nós que compõem o caminho mínimo de `inicio` até `fim`.
                                Se não houver caminho, retorna lista vazia.
              - distancia (float): custo total desse caminho. Se não houver caminho, retorna infinito.
        Observações
        -----------
        - Caso `inicio` ou `fim` não estejam presentes no grafo, o comportamento resulta em
          caminho vazio e distância infinita.
        - Utiliza uma fila de prioridade (heap) para selecionar o próximo nó de menor distância.
        """

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

    def nearest_node(self, nodes_dict: dict, coord: tuple):
        """
        Retorna o identificador do nó mais próximo de uma dada coordenada usando
        distância euclidiana.

        Parâmetros
        ----------
        nodes_dict : dict
            Dicionário onde as chaves são IDs de nós e os valores são tuplas
            (latitude, longitude) de cada nó.
        coord : tuple
            Tupla (latitude, longitude) representando a coordenada de referência.

        Retorna
        -------
        nearest : mesmo tipo que as chaves de nodes_dict
            ID do nó cuja distância até a coordenada fornecida é a menor.
        """
        if isinstance(coord, str):
            try:
                lat, lon = map(float, coord.split(','))
            except ValueError:
                raise ValueError(f"Coordenadas inválidas: {coord}")
        else:
            lat, lon = coord

        nearest = None
        min_dist = float('inf')
        for node_id, (node_lat, node_lon) in nodes_dict.items():
            d = math.hypot(lat - node_lat, lon - node_lon)
            if d < min_dist:
                min_dist = d
                nearest = node_id
        if nearest is None:
            raise ValueError(f"Nenhuma coordenada encontrada para o nó mais próximo do ponto fornecido. Coordenadas: {coord}")
        return nearest

    def execute(self, origem_coords: tuple, destino_coords: tuple, filename: str):
        data = Data()
        try:
            json = data.get_json(filename)
        except FileNotFoundError:
            raise ValueError(f"Arquivo {filename} não encontrado.")

        grafo, nodes = self.construir_grafo(json)
        try:
            origem_node = self.nearest_node(nodes, origem_coords)
            destino_node = self.nearest_node(nodes, destino_coords)
        except ValueError as e:
            raise ValueError(f"Erro ao encontrar nós mais próximos: {e}")

        caminho, distancia = self.dijkstra(grafo, origem_node, destino_node)

        arestas = []
        for u, v in zip(caminho, caminho[1:]):
            peso = next((w for nbr, w in grafo[u] if nbr == v), None)
            arestas.append((u, v, peso))
 
        return caminho, distancia, filename, arestas