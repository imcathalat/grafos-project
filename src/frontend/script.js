let osmFilename = null;
let bbox = null; // [S, W, N, E]
let map, originMarker = null, destMarker = null, routeLine = null;
let routeLayer = null;            // polyline única
let circleGroup  = null; 

const spinner   = document.getElementById('spinner');
const spinnerMsg = document.getElementById('spinnerMsg');
function showSpinner(msg="Carregando...") {
      spinnerMsg.textContent = msg;
      spinner.classList.add('show');
    }
const hideSpin  = () => spinner.classList.remove('show');

// prettier-ignore
const API_LOCALIDADES = "https://servicodados.ibge.gov.br/api/v1/localidades";

document.getElementById("btnReset").addEventListener("click", () => {
  // limpa mapa / rota
  resetMap(true);            // hideContainer = true
  // some com o grafo renderizado
  document.getElementById("grafoContainer").innerHTML = "";
});


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

    resetMap(true); 
    showSpinner("Seu mapa está sendo carregado..."); 

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
    hideSpin(); 
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

    if (isNaN(olat) || isNaN(olng) || isNaN(dlat) || isNaN(dlng)) {
        alert("Coordenadas inválidas");
        return;
    }

    showSpinner("Calculando a menor rota...");

    const res = await fetch("http://127.0.0.1:5055/dijkstra/shortest-path", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: osmFilename,
      origem: { lat: olat, lng: olng },
      destino: { lat: dlat, lng: dlng },
    }),
  });
  
    const instr = document.getElementById("instructions");
    const stat  = document.getElementById("status");
    const data  = await res.json();
    if (!res.ok) {
      instr.innerHTML = `<strong>${data.error}</strong>` || "Falha na rota";
      hideSpin();
      return;
    }

    const km = (parseFloat(data.distancia) / 1000).toFixed(2);
    stat.innerText = `Menor distância: ${km} km`;

    /* atualiza instruções */
    const nArestas   = data.arestas.length;
    const nVertices  = nArestas + 1;
    instr.classList.remove("d-none");   // garante visível
    instr.innerHTML = `
        Rota calculada com <strong>${nVertices}</strong> vértices
        e <strong>${nArestas}</strong> arestas.<br>
        Menor distância encontrada: <strong>${km} km</strong>.<br>
        As bolinhas vermelhas representam os <strong>vértices do grafo</strong>.<br>
        As linhas vermelhas representam as <strong>arestas do grafo</strong>.
    `;

    // desenha rota
    // const latlngs = data.menor_caminho.map(([lat, lng]) => [lat, lng]);
    // L.polyline(latlngs, { weight: 4, color: "#ffd500" }).addTo(map);
    // stat.innerText = `Distância: ${data.distancia}`;

    desenharRota(data.arestas);
    hideSpin(); 
});

function resetMap(hideContainer = false) {
  if (map) {
    map.off();
    map.remove();
    map = null;
  }
  if (routeLine) { routeLine.remove(); routeLine = null; }
  originMarker = destMarker = null;

  document.getElementById("origemCoord").value = "";
  document.getElementById("destinoCoord").value = "";
  document.getElementById("btnCalcular").disabled = true;
  document.getElementById("status").innerText = "";

  if (hideContainer) {
    document.getElementById("map").classList.add("d-none");
    document.getElementById("instructions").classList.add("d-none");
  }
}

function desenharRota(arestas) {
  if (!map || !Array.isArray(arestas) || arestas.length === 0) return;

  // limpa rota anterior
  if (routeLayer) { map.removeLayer(routeLayer); routeLayer = null; }
  if (originMarker) { map.removeLayer(originMarker); originMarker = null; }
  if (destMarker)   { map.removeLayer(destMarker);   destMarker  = null; }
  if (circleGroup) { map.removeLayer(circleGroup); circleGroup = null; }

  // converte arestas -> lista contínua de vértices
  const latlngs = [];
  const toLatLng = (s) => s.split(",").map(Number);
  const toLL = (s) => s.split(",").map(Number);

  arestas.forEach((e, i) => {
    const pA = toLL(e.origem);
    const pB = toLL(e.destino);
    if (i === 0) latlngs.push(pA);
    latlngs.push(pB);
  });

  /* rota vermelha */
  routeLayer = L.polyline(latlngs, { color: "red", weight: 6, opacity: 0.7 }).addTo(map);

  /* bolinhas azuis em cada vértice */
  circleGroup = L.layerGroup();
  latlngs.forEach((p) =>
    L.circleMarker(p, { radius: 6, color:  "#ff0000", fillColor: "#ff0000", weight: 2, fillOpacity: 1 })
      .addTo(circleGroup)
  );
  circleGroup.addTo(map);

  /* marcadores início/fim */
  const iconBase = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img";
  const mkIcon = (c) => new L.Icon({
    iconUrl : `${iconBase}/marker-icon-${c}.png`,
    shadowUrl:"https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    iconSize:[25,41], iconAnchor:[12,41],
  });
  originMarker = L.marker(latlngs[0],                 { icon: mkIcon("green") }).addTo(map);
  destMarker   = L.marker(latlngs[latlngs.length-1],  { icon: mkIcon("red")   }).addTo(map);

  map.fitBounds(routeLayer.getBounds());
   map.once("idle", exportarImagem);  // gera PNG depois que tiles carregarem
}

function exportarImagem() {
  leafletImage(map, (err, canvas) => {
    if (err) { console.error("Falha na imagem:", err); return; }

    const container = document.getElementById("grafoContainer");
    container.innerHTML = "";                    // limpa saída anterior

    /* título */
    const h4 = document.createElement("h4");
    h4.textContent = "Grafo de Menor Caminho";
    container.appendChild(h4);

    /* transforma canvas em <img> */
    const img = document.createElement("img");
    img.src = canvas.toDataURL("image/png");
    img.alt = "Rota calculada";
    img.style.maxWidth = "100%";
    img.style.border = "1px solid #ccc";
    container.appendChild(img);
  });
}

/* botão opcional continua funcionando */
document.getElementById("btnExport")?.addEventListener("click", exportarImagem);




document.addEventListener("DOMContentLoaded", loadForm);