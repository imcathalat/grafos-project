async function load_form(){

    const estadoSelect = document.getElementById("estado");
    const cidadeSelect = document.getElementById("cidade");
    
    try {
        const response = await fetch("https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome");
        if(!response.ok) throw new Error("Erro ao carregar estados");
        const estados = await response.json();
        estadoSelect.innerHTML = `<option value="">Selecione o estado</option>`;
        estados.forEach(estado => {
          const option = document.createElement("option");
          option.value = estado.id;
          option.textContent = estado.nome;
          estadoSelect.appendChild(option);
        });
    } catch (error) {
        console.error(error);
    }

    estadoSelect.addEventListener("change", async () => {
        const estadoId = estadoSelect.value;
        if (!estadoId) return;

        cidadeSelect.disabled = true;
        cidadeSelect.innerHTML = `<option>Carregando...</option>`;

        cities_response = await fetch(`https://servicodados.ibge.gov.br/api/v1/localidades/estados/${estadoId}/municipios`);

        if (!cities_response.ok) {
            cidadeSelect.innerHTML = `<option>Erro ao carregar cidades</option>`;
            return;
        }

        const cidades = await cities_response.json();
        cidadeSelect.disabled = false;
            cidadeSelect.innerHTML = `<option value="">Selecione a cidade</option>`;
            cidades.forEach(cidade => {
                const option = document.createElement("option");
                option.value = cidade.nome;
                option.textContent = cidade.nome;
                cidadeSelect.appendChild(option);
            });
        });
    }



    // Enviar dados para o backend Python
    form.addEventListener("submit", e => {
      e.preventDefault();

      const estadoNome = estadoSelect.options[estadoSelect.selectedIndex].text;
      const cidadeNome = cidadeSelect.value;

      fetch("http://localhost:5055/json/cidade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cidade: cidadeNome, estado: estadoNome})
      })
        .then(res => res.json())
        .then(data => {
          statusDiv.textContent = `Dados enviados com sucesso: ${JSON.stringify(data)}`;
        })
        .catch(err => {
          statusDiv.textContent = "Erro ao enviar dados.";
          console.error(err);
        });
    });

document.addEventListener('DOMContentLoaded', load_form);