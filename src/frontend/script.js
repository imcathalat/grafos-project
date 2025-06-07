let osmFilename = null;
let bbox = null; // [S, W, N, E]
let map, originMarker = null, destMarker = null, routeLine = null;;

// prettier-ignore
const API_LOCALIDADES = "https://servicodados.ibge.gov.br/api/v1/localidades";

// =============== carrega estado/cidade ====================
async function loadForm() {
    const estadoSelect = document.getElementById("estado");
    const cidadeSelect = document.getElementById("cidade");
    const form = document.getElementById("locationForm");

    // ---- preenche estados ----
    try {
    const resp = await fetch(`${API_LOCALIDADES}/estados?orderBy=nome`);
    if (!resp.ok) throw new Error("Falha ao carregar estados");
    const estados = await resp.json();
    estadoSelect.innerHTML =
        '<option value="">Selecione o estado</option>';
    estados.forEach((est) => {
        const opt = document.createElement("option");
        opt.value = est.id;
        opt.textContent = est.nome;
        estadoSelect.appendChild(opt);
    });
    } catch (err) {
    console.error(err);
    }

    // ---- ao trocar estado ----
    estadoSelect.addEventListener("change", async () => {
    const id = estadoSelect.value;
    if (!id) return;
    cidadeSelect.disabled = true;
    cidadeSelect.innerHTML = "<option>Carregando...</option>";
    const res = await fetch(`${API_LOCALIDADES}/estados/${id}/municipios`);
    if (!res.ok) return (cidadeSelect.innerHTML =
        "<option>Erro ao carregar</option>");
    const cidades = await res.json();
    cidadeSelect.innerHTML =
        '<option value="">Selecione a cidade</option>';
    cidades.forEach((cid) => {
        const opt = document.createElement("option");
        opt.value = cid.nome;
        opt.textContent = cid.nome;
        cidadeSelect.appendChild(opt);
    });
    cidadeSelect.disabled = false;
    });

    // ---- submit estado/cidade ----
    form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const estadoNome = estadoSelect.options[estadoSelect.selectedIndex].text;
    const cidadeNome = cidadeSelect.value;

    const res = await fetch("http://127.0.0.1:5055/json/cidade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cidade: cidadeNome, estado: estadoNome }),
    });

    if (!res.ok) {
        document.getElementById("status").innerText = "Falha ao baixar mapa";
        return;
    }

    const data = await res.json(); // { filename, bbox }
    console.log('[DEBUG] resposta /json/cidade:', data);
    osmFilename = data.filename;
    bbox = data.bbox;
    initMap();
    });
}

function initMap() {
    if (map) {
        map.off();
        map.remove();
        map = null;
    }
    originMarker = destMarker = null;

    if (routeLine) {
        routeLine.remove();
        routeLine = null;
    }

    document.getElementById("origemCoord").value = "";
    document.getElementById("destinoCoord").value = "";
    document.getElementById("btnCalcular").disabled = true;

    const mapDiv = document.getElementById("map");
    mapDiv.classList.remove("d-none");
    document.getElementById("instructions").classList.remove("d-none");
    void mapDiv.offsetWidth; // reflow

    const [south, west, north, east] = bbox;
    const center = [(south + north) / 2, (west + east) / 2];

    map = L.map("map", { zoomControl: false }).setView(center, 13);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "© OpenStreetMap"
    }).addTo(map);

    map.fitBounds([
    [south, west],
    [north, east],
    ]);
    setTimeout(() => map.invalidateSize(), 0); 

    // ====== geocoder (lupa) ======
      const geocoder = L.Control.geocoder({
        defaultMarkGeocode: false,
        placeholder: "Buscar endereço...",
      }).addTo(map);

      geocoder.on("markgeocode", (e) => {
        handleSelection(e.geocode.center);
      });

    // markers
    const iconBase = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img";
    const markerIcon = (color) =>
    new L.Icon({
      iconUrl: `${iconBase}/marker-icon-${color}.png`,
      shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      iconSize: [25, 41],
      iconAnchor: [12, 41],
    });
    function handleSelection(latlng) {
    const { lat, lng } = latlng;
    const fmt = (v) => v.toFixed(6);

    if (!originMarker) {
      originMarker = L.marker([lat, lng], { icon: markerIcon("green") }).addTo(map);
      document.getElementById("origemCoord").value = `${fmt(lat)}, ${fmt(lng)}`;
      map.setView([lat, lng], 15);          // dá foco
    } else if (!destMarker) {
      destMarker = L.marker([lat, lng], { icon: markerIcon("red") }).addTo(map);
      document.getElementById("destinoCoord").value = `${fmt(lat)}, ${fmt(lng)}`;
      document.getElementById("btnCalcular").disabled = false;
    } else {
      // terceira seleção = reiniciar
      map.removeLayer(originMarker);
      map.removeLayer(destMarker);
      originMarker = destMarker = null;
      handleSelection(latlng);              // usa o clique atual como nova origem
    }
  }

  /* =========================================================
     7. Clique no mapa → mesma lógica
  ========================================================= */
  map.on("click", (e) => handleSelection(e.latlng));
}


document.getElementById("btnCalcular").addEventListener("click", async () => {
    const parseCoord = (id) => document.getElementById(id).value.split(",").map(Number);
    const [olat, olng] = parseCoord("origemCoord");
    const [dlat, dlng] = parseCoord("destinoCoord");

    const res = await fetch("http://127.0.0.1:5055/dijkstra/shortest-path", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        filename: osmFilename,
        origem: { lat: olat, lng: olng },
        destino: { lat: dlat, lng: dlng },
    }),
    });

    const stat = document.getElementById("status");
    const data = await res.json();
    if (!res.ok) {
    stat.innerText = data.error || "Falha na rota";
    return;
    }

    // desenha rota
    const latlngs = data.menor_caminho.map(([lat, lng]) => [lat, lng]);
    L.polyline(latlngs, { weight: 4, color: "#ffd500" }).addTo(map);
    stat.innerText = `Distância: ${data.distancia}`;
});


document.addEventListener("DOMContentLoaded", loadForm);