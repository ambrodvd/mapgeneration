import streamlit as st
import math
import contextily as cx
import matplotlib.pyplot as plt
from pyproj import Transformer
from io import BytesIO
from PIL import Image
import fitparse
import numpy as np
import gc

st.set_page_config(page_title="Mappa da file FIT", layout="wide")
st.title("🗺️ Generatore mappa da traccia FIT")

# ------------------------------------------------------------
# 1. Caricamento file FIT
# ------------------------------------------------------------
uploaded_files = st.file_uploader(
    "Carica uno o più file .fit",
    type=["fit"],
    accept_multiple_files=True,
    help="Trascina qui i file FIT con le tue tracce GPS"
)

if uploaded_files:
    st.success(f"{len(uploaded_files)} file caricato/i")
else:
    st.info("Nessun file caricato. Inserisci un file FIT per iniziare.")
    st.stop()

# ------------------------------------------------------------
# 2. Parametri di stampa e qualità
# ------------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    size = st.selectbox("Formato carta", ["A1", "A2"])
with col2:
    dpi = st.slider("DPI per la stampa", 100, 600, 200, 10, help="Più alto = più dettaglio, ma file più pesante")
with col3:
    zoom_option = st.selectbox("Zoom mappa", ["Auto"] + [str(z) for z in range(10, 18)], index=0,
                               help="Se 'Auto' non mostra i sentieri, scegli un numero più alto (es. 15-16)")

# Avviso per DPI elevato
if dpi > 250:
    st.warning(
        "⚠️ Con DPI > 250 la generazione in‑app potrebbe fallire per limiti di memoria. "
        "Se il download non funziona, usa il comando da terminale che troverai in fondo alla pagina."
    )

PREVIEW_DPI = 40
PREVIEW_MAX_WIDTH = 1200

MARGIN_METERS = 1000   # 1 km
BASEMAP = cx.providers.OpenTopoMap   # sentieri, curve di livello, rifugi
PAPER_SIZES = {"A1": (33.1, 23.4), "A2": (23.4, 16.5)}

# Converti zoom_option in numero o None per auto
zoom_level = None if zoom_option == "Auto" else int(zoom_option)

# ------------------------------------------------------------
# 3. Lettura punti dai file FIT
# ------------------------------------------------------------
def extract_points_from_fit(files):
    points = []
    for uploaded_file in files:
        content = uploaded_file.read()
        try:
            fitfile = fitparse.FitFile(BytesIO(content))
            for record in fitfile.get_messages("record"):
                lat = record.get_value("position_lat")
                lon = record.get_value("position_long")
                if lat is not None and lon is not None:
                    lat_deg = lat * (180.0 / 2**31)
                    lon_deg = lon * (180.0 / 2**31)
                    points.append((lon_deg, lat_deg))
        except Exception as e:
            st.warning(f"Errore nella lettura di {uploaded_file.name}: {e}")
    return points

# ------------------------------------------------------------
# 4. Calcolo bounding box con margine e adattamento formato
# ------------------------------------------------------------
def compute_extent(points_wgs84, margin_m=1000, paper_size="A1"):
    if not points_wgs84:
        raise ValueError("Nessun punto GPS valido trovato.")
    
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    x_coords, y_coords = transformer.transform(
        [p[0] for p in points_wgs84],
        [p[1] for p in points_wgs84]
    )
    xmin, xmax = min(x_coords), max(x_coords)
    ymin, ymax = min(y_coords), max(y_coords)
    
    xmin -= margin_m
    xmax += margin_m
    ymin -= margin_m
    ymax += margin_m
    
    w, h = PAPER_SIZES[paper_size]
    aspect = w / h
    width = xmax - xmin
    height = ymax - ymin
    
    if width / height > aspect:
        new_height = width / aspect
        pad = (new_height - height) / 2
        ymin -= pad
        ymax += pad
    else:
        new_width = height * aspect
        pad = (new_width - width) / 2
        xmin -= pad
        xmax += pad
        
    return xmin, xmax, ymin, ymax

# ------------------------------------------------------------
# 5. Generazione mappa (con supporto zoom manuale)
# ------------------------------------------------------------
def genera_mappa(xmin, xmax, ymin, ymax, paper_size, dpi_value, for_preview=False, zoom=None):
    w_in, h_in = PAPER_SIZES[paper_size]
    
    fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=dpi_value)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_axis_off()
    
    zoom_param = zoom if zoom is not None else "auto"
    cx.add_basemap(
        ax,
        source=BASEMAP,
        crs="EPSG:3857",
        zoom=zoom_param,
        attribution_size=6,
    )
    fig.tight_layout(pad=0)
    
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi_value, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    gc.collect()
    
    buf.seek(0)
    img = Image.open(buf)
    
    if for_preview:
        img.thumbnail((PREVIEW_MAX_WIDTH, PREVIEW_MAX_WIDTH), Image.LANCZOS)
        if img.mode == "RGBA":
            img = img.convert("RGB")
    
    return img, buf

# ------------------------------------------------------------
# 6. Interfaccia principale
# ------------------------------------------------------------
if st.button("🗺️ Genera mappa"):
    with st.spinner("Leggo i file FIT..."):
        points = extract_points_from_fit(uploaded_files)
    
    if not points:
        st.error("Nessuna coordinata GPS trovata nei file caricati.")
        st.stop()
    
    st.success(f"Trovati {len(points)} punti GPS.")
    
    try:
        with st.spinner("Calcolo l'area della mappa..."):
            xmin, xmax, ymin, ymax = compute_extent(points, MARGIN_METERS, size)
    except Exception as e:
        st.error(f"Errore nel calcolo dell'estensione: {e}")
        st.stop()
    
    with st.spinner("Creo anteprima..."):
        img_preview, _ = genera_mappa(xmin, xmax, ymin, ymax, size, PREVIEW_DPI, for_preview=True, zoom=zoom_level)
    
    st.image(img_preview, caption="Anteprima della mappa", width='stretch')
    
    # Salva parametri nella sessione
    st.session_state["bounds"] = (xmin, xmax, ymin, ymax)
    st.session_state["size"] = size
    st.session_state["dpi"] = dpi
    st.session_state["zoom"] = zoom_level
    st.session_state["anteprima_ok"] = True

# ------------------------------------------------------------
# 7. Download PNG e PDF
# ------------------------------------------------------------
if st.session_state.get("anteprima_ok", False):
    st.markdown("---")
    st.subheader("📥 Scarica la mappa pronta per la stampa")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📷 Scarica PNG"):
            xmin, xmax, ymin, ymax = st.session_state["bounds"]
            size = st.session_state["size"]
            dpi_val = st.session_state["dpi"]
            zoom_val = st.session_state["zoom"]
            with st.spinner(f"Creo PNG a {dpi_val} DPI..."):
                img_hd, buf_png = genera_mappa(xmin, xmax, ymin, ymax, size, dpi_val, for_preview=False, zoom=zoom_val)
            st.download_button(
                label="📥 Clicca qui per scaricare il PNG",
                data=buf_png.getvalue(),
                file_name="mappa_stampa.png",
                mime="image/png"
            )
    
    with col2:
        if st.button("📄 Scarica PDF"):
            xmin, xmax, ymin, ymax = st.session_state["bounds"]
            size = st.session_state["size"]
            dpi_val = st.session_state["dpi"]
            zoom_val = st.session_state["zoom"]
            with st.spinner(f"Creo PDF a {dpi_val} DPI..."):
                w_in, h_in = PAPER_SIZES[size]
                fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=dpi_val)
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin, ymax)
                ax.set_axis_off()
                zoom_param = zoom_val if zoom_val is not None else "auto"
                cx.add_basemap(ax, source=BASEMAP, crs="EPSG:3857", zoom=zoom_param, attribution_size=6)
                fig.tight_layout(pad=0)
                
                buf_pdf = BytesIO()
                fig.savefig(buf_pdf, format="pdf", dpi=dpi_val, bbox_inches="tight", pad_inches=0)
                plt.close(fig)
                buf_pdf.seek(0)
            st.download_button(
                label="📥 Clicca qui per scaricare il PDF",
                data=buf_pdf,
                file_name="mappa_stampa.pdf",
                mime="application/pdf"
            )
    
    # Opzione terminale per DPI molto alti
    if dpi > 250:
        st.markdown("---")
        st.info(
            "💡 **Alternativa stabile:** Se il download diretto non funziona a DPI così alto, "
            "puoi usare lo script da terminale qui sotto. Salva il codice seguente come `genera_hd.py` "
            "ed eseguilo con i parametri indicati."
        )
        st.code(
            f"python genera_hd.py --lat_min {ymin} --lat_max {ymax} --lon_min {xmin} --lon_max {xmax} "
            f"--size {size} --dpi {dpi} --zoom {zoom_level if zoom_level else 'auto'}",
            language="bash"
        )