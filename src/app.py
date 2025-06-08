from flask import Flask, jsonify, request
from flask_cors import CORS
from graph import Graph
from data import Data
app = Flask(__name__)
CORS(app)

@app.route('/dijkstra/shortest-path', methods=['POST'])
def get_shortest_path():
    """
    Endpoint para obter o menor caminho entre dois pontos em uma cidade.
    Descrição:
        Esta função recebe uma requisição com payload JSON contendo os parâmetros 'cidade', 'origem' e 'destino'.
        Em seguida, processa a solicitação para determinar o menor caminho e sua distância utilizando o objeto Graph.
        Caso ocorram erros durante o processamento, são retornadas respostas com códigos de erro apropriados.
    Parâmetros (esperados no JSON da requisição):
        cidade  : Nome da cidade onde será calculado o caminho.
        origem  : Ponto de origem (que será geocodificado).
        destino : Ponto de destino (que será geocodificado).
    Retornos:
        JSON contendo:
            - "distancia": Distância total do caminho formatada com duas casas decimais (em metros).
            - "menor_caminho": Lista ou representação do menor caminho encontrado.
            - "filename": Nome do arquivo associado, conforme retorno da execução.
        Em casos de erro, retorna um JSON com a mensagem de erro e o código HTTP correspondente:
            - Código 400: Para payload JSON inválido ou parâmetros ausentes.
            - Código 404: Se a geocodificação falhar ou o menor caminho não for encontrado.
            - Código 500: Para outros erros inesperados.
    Exceções Tratadas:
        - ValueError: Se ocorrer um erro de geocodificação (mensagem iniciada com "Não foi possível geocodificar"),
                     retornando erro 404.
        - Outras exceções são registradas via log e retornam erro 500.
    Endpoint to get the shortest path between two points in a city.
    Expects a JSON payload with 'cidade', 'origem', and 'destino'.
    Returns a JSON response with the shortest path and distance.
    """
    try:
        data = request.get_json(force=True)
    except Exception as exc:
        app.logger.error("Invalid JSON payload: %s", exc)
        return jsonify({"error": "Invalid JSON payload"}), 400

    origem = data.get('origem')
    destino = data.get('destino')
    filename = data.get('filename')
    
    try:
        olat = float(origem["lat"])
        olng = float(origem["lng"])
        dlat = float(destino["lat"])
        dlng = float(destino["lng"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Coordenadas inválidas"}), 400
    
    if not all([origem, destino, filename]):
        return jsonify({"error": "Missing required parameters: 'origem', 'destino', 'filename'"}), 400

    try:
        graph = Graph()
        path, distance, _, arestas = graph.execute( (olat, olng), (dlat, dlng), filename)
    except ValueError as ve:
        if str(ve).startswith("Não foi possível geocodificar"):
            return jsonify({"error": "Origem ou destino não encontrado"}), 404
        return jsonify({"error": str(ve)}), 400
    except Exception as exc:
        app.logger.error("Erro no", exc)
        return jsonify({"error": "An error occurred while processing your request"}), 500

    if not path:
        return jsonify({"error": "Menor caminho não encontrado"}), 404

    return jsonify({ "distancia": f"{distance:.2f} metros", "menor_caminho": path, "arestas": arestas }), 200

@app.route('/json/cidade', methods=['POST'])
def download_json_map():
    """
    Rota GET /dijkstra/download-json-map.
    Retorna um JSON contendo o mapa da cidade, incluindo nós e arestas.
    Utiliza o método download_json_map da classe Data para obter os dados.
    Retorna:
        200: O caminho do arquivo .json baixado.
        500: erro interno ao baixar o mapa, registrado em log.
    """
    print("Iniciando download do mapa JSON")
    data = request.get_json()
    cidade = data.get('cidade')
    estado = data.get('estado')
    try:
        d = Data()
        _, filename, bbox = d.baixar_osm(cidade, estado)
    except Exception as exc:
        app.logger.error("Error downloading JSON map: %s", exc)
        return jsonify({"error": "Erro ao baixar o mapa"}), 500

    return jsonify({ "filename": filename, "bbox": bbox }), 200

if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=5055)