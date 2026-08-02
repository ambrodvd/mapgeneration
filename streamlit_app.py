"""
Genera un file grafico ad alta risoluzione (poster A1/A2) con basemap
OpenTopoMap, centrato su un punto con un dato raggio in km.

Dipendenze (da installare nel tuo ambiente, es. dutrailpredictor):
    uv add contextily matplotlib geopy pyproj

Esecuzione:
    uv run genera_mappa_stampa.py
"""

import math
import contextily as cx
import matplotlib.pyplot as plt
from pyproj import Transformer
from geopy.geocoders import Nominatim

# =========================================================
# PARAMETRI DA MODIFICARE
# =========================================================

# Opzione A: inserisci un nome di luogo (via, città, monte, rifugio, ecc.)
# e le coordinate verranno trovate automaticamente.
PLACE_NAME = "Rifugio Gilberti, Italia"   # <-- cambia qui, o metti None per usare CENTER_LAT/LON manuali

# Opzione B: se preferisci coordinate manuali, imposta PLACE_NAME = None
# e valorizza questi due campi.
CENTER_LAT = 45.4642
CENTER_LON = 9.1900

RADIUS_KM = 15.0            # raggio dell'area da inquadrare (dal centro al bordo)

PAPER_SIZE = "A1"           # "A1" o "A2"
DPI = 300                   # 300 DPI = qualità stampa professionale

OUTPUT_FILE = "mappa_stampa.png"
PREVIEW_FILE = "mappa_stampa_ANTEPRIMA.png"
PREVIEW_MAX_WIDTH_PX = 900   # larghezza max dell'anteprima, in pixel

# Provider basemap "outdoor" (curve di livello, sentieri, rifugi)
BASEMAP_PROVIDER = cx.providers.OpenTopoMap
# Alternative valide:
#   cx.providers.Esri.WorldTopoMap
#   cx.providers.CyclOSM

# =========================================================
# Dimensioni carta in pollici (orientamento orizzontale)
# =========================================================
PAPER_SIZES_IN = {
    "A1": (33.1, 23.4),
    "A2": (23.4, 16.5),
}

# =========================================================
# Geocoding automatico (se PLACE_NAME è impostato)
# =========================================================
if PLACE_NAME:
    print(f"Cerco le coordinate di: {PLACE_NAME} ...")
    geolocator = Nominatim(user_agent="du_coaching_map_generator")
    location = geolocator.geocode(PLACE_NAME, timeout=10)
    if location is None:
        raise ValueError(
            f"Nessun risultato trovato per '{PLACE_NAME}'. "
            "Prova a essere più specifico (es. aggiungi la provincia o il paese)."
        )
    CENTER_LAT = location.latitude
    CENTER_LON = location.longitude
    print(f"Trovato: {location.address}")
    print(f"Coordinate: {CENTER_LAT:.5f}, {CENTER_LON:.5f}")

# =========================================================
# Calcolo bounding box in metri (Web Mercator EPSG:3857)
# =========================================================
transformer_to_merc = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
transformer_to_wgs = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

cx_m, cy_m = transformer_to_merc.transform(CENTER_LON, CENTER_LAT)

radius_m = RADIUS_KM * 1000

# Adatta il bounding box al rapporto d'aspetto del formato carta scelto
w_in, h_in = PAPER_SIZES_IN[PAPER_SIZE]
aspect = w_in / h_in

if aspect >= 1:
    half_w = radius_m * aspect
    half_h = radius_m
else:
    half_w = radius_m
    half_h = radius_m / aspect

xmin, xmax = cx_m - half_w, cx_m + half_w
ymin, ymax = cy_m - half_h, cy_m + half_h

# =========================================================
# Generazione figura
# =========================================================
fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=DPI)
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)
ax.set_axis_off()

print("Scarico i tile da OpenTopoMap (può richiedere qualche minuto per aree grandi)...")
cx.add_basemap(
    ax,
    source=BASEMAP_PROVIDER,
    crs="EPSG:3857",
    zoom="auto",       # contextily sceglie lo zoom migliore per la risoluzione richiesta
    attribution_size=6,
)

fig.tight_layout(pad=0)
fig.savefig(OUTPUT_FILE, dpi=DPI, bbox_inches="tight", pad_inches=0)
print(f"Salvato: {OUTPUT_FILE} ({w_in}x{h_in} in @ {DPI} DPI)")

# =========================================================
# Anteprima leggera (per controllo rapido senza aprire il file grande)
# =========================================================
from PIL import Image

with Image.open(OUTPUT_FILE) as img:
    ratio = PREVIEW_MAX_WIDTH_PX / img.width
    preview_size = (PREVIEW_MAX_WIDTH_PX, int(img.height * ratio))
    preview = img.resize(preview_size, Image.LANCZOS)
    preview.save(PREVIEW_FILE)

print(f"Anteprima salvata: {PREVIEW_FILE} ({preview_size[0]}x{preview_size[1]} px)")