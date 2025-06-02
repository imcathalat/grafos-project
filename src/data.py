import json
import os
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

class Data:
    def baixar_osm(self, place: str):
        """
        Baixa dados de infraestrutura viária do OpenStreetMap para uma localidade específica.

        Este método realiza os seguintes passos:
        1. Cria (se necessário) um diretório 'cache' para armazenar os dados baixados.
        2. Converte o nome da localidade em um nome de arquivo padronizado.
        3. Utiliza o geocodificador Nominatim (via geopy) para obter a caixa delimitadora (bounding box) da localidade.
        4. Monta e envia uma consulta Overpass API para obter todas as vias ("highway") na área definida.
        5. Salva o JSON retornado em disco no diretório de cache.
        6. Retorna os dados OSM em formato de dicionário Python e o caminho do arquivo salvo.

        Parâmetros:
            place (str): Nome da localidade a ser pesquisada (por exemplo, "São Paulo, Brasil").

        Retorno:
            tuple:
                osm_data (dict): Estrutura de dados carregada a partir do JSON retornado pela Overpass API.
                filename (str): Caminho do arquivo onde o JSON foi salvo localmente.

        Exceções:
            geopy.exc.GeocoderServiceError:
                Caso ocorra erro ao obter a caixa delimitadora via Nominatim.
            requests.exceptions.RequestException:
                Em caso de falha na requisição HTTP à Overpass API.
            OSError:
                Se ocorrer erro ao criar o diretório de cache ou ao salvar o arquivo.
        """
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
