import json
class Data:
    def __init__(self, filename):
        self.filename = filename

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
