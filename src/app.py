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

    cidade = data.get('cidade')
    origem = data.get('origem')
    destino = data.get('destino')

    if not all([cidade, origem, destino]):
        return jsonify({"error": "Missing required parameters: 'cidade', 'origem', 'destino'"}), 400

    try:
        graph = Graph()
        path, distance, filename = graph.execute(cidade, origem, destino)
    except ValueError as ve:
        if str(ve).startswith("Não foi possível geocodificar"):
            return jsonify({"error": "Origem ou destino não encontrado"}), 404
    except Exception as exc:
        app.logger.error("Erro no", exc)
        return jsonify({"error": "An error occurred while processing your request"}), 500

    if not path:
        return jsonify({"error": "Menor caminho não encontrado"}), 404

    return jsonify({"distancia": f"{distance:.2f} metros", "menor_caminho": path, "filename": filename}), 200

@app.route('/dijkstra/filtered-json', methods=['POST'])
def get_filtered_json():
    """
    Rota POST /dijkstra/filtered-json.
    Recebe via JSON os parâmetros:
        filename (str): caminho/nome do arquivo que contém o grafo.
        shortest_path (list): sequência de nós que compõem o caminho mais curto.
    Valida a presença de ambos os parâmetros, carrega os dados do arquivo informado
    e filtra o JSON original mantendo somente os nós especificados em shortest_path.
    Retorna:
        200: JSON resultante da filtragem dos dados.
        400: erro de parâmetros vazios ou ausentes.
        500: erro interno ao filtrar os dados do JSON, registrado em log.
    """
    data = request.get_json(force=True)
    filename = data.get('filename')
    shortest_path = data.get('shortest_path')

    if not filename or not shortest_path:
        return jsonify({"error": "Parâmetros vazios: 'filename', 'shortest_path'"}), 400

    try:
        data = Data(filename)
        json_filtrado = data.filter_json_with_nodes(shortest_path)
    except Exception as exc:
        app.logger.error("Error filtering JSON data: %s", exc)
        return jsonify({"error": "Erro na filtragem dos dados do json"}), 500

    return jsonify(json_filtrado), 200
if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=5055)