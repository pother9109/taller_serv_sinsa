import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from PIL import Image
from urllib.parse import quote
import requests
import io
import zipfile

# Configuración de la página
st.set_page_config(page_title="Taller de Servicio", layout="wide")

# URL directa de descarga del ZIP en Google Drive
def get_drive_download_url(file_id):
    return f"https://drive.google.com/uc?export=download&id={file_id}"

ZIP_FILE_ID = "1acS7WYpi3J-z9P3cNwLv20YXRtPw8JKT"
ZIP_URL = get_drive_download_url(ZIP_FILE_ID)
EXCEL_NAME = "Registro de productos y repuestos.xlsx"

@st.cache_data
def descargar_y_extraer_excel(zip_url=ZIP_URL, excel_name=EXCEL_NAME):
    """
    Descarga el archivo ZIP desde Google Drive, lo extrae en memoria,
    y lee el Excel especificado dentro.
    """
    # Descargar ZIP
    response = requests.get(zip_url)
    response.raise_for_status()
    zip_bytes = io.BytesIO(response.content)

    # Extraer con zipfile
    with zipfile.ZipFile(zip_bytes) as zf:
        if excel_name in zf.namelist():
            data = zf.read(excel_name)
        else:
            xlsx_list = [f for f in zf.namelist() if f.lower().endswith(".xlsx")]
            if not xlsx_list:
                raise FileNotFoundError(f"No se encontró ningún .xlsx en el ZIP: {zf.namelist()}")
            data = zf.read(xlsx_list[0])

    xls = pd.ExcelFile(io.BytesIO(data))
    productos_df = xls.parse(xls.sheet_names[1])
    repuestos_df = xls.parse(xls.sheet_names[0])
    return productos_df, repuestos_df

# Carga de imágenes de logo e íconos
logo = Image.open("logo_taller.png")
ico_admin = Image.open("ico_admin.png")
ico_consulta = Image.open("ico_consulta.png")

# Cabecera
st.image(logo, width=80)
st.markdown(
    """<h1 style='text-align:center; color:#333;'>Taller de Servicio</h1>
    <h4 style='text-align:center; color:#777;'>Silva Internacional S.A</h4>""",
    unsafe_allow_html=True
)

# Estado de página
pagina = st.session_state.get("pagina", "inicio")

if pagina == "inicio":
    st.markdown(
        "<br><h5 style='text-align:center; color:darkorange;'>¿Qué deseas hacer?</h5>",
        unsafe_allow_html=True
    )
    col1, col2 = st.columns(2, gap="large")

    with col1:
        if st.button("Administrar catálogo", use_container_width=True):
            st.session_state.pagina = "admin"
            st.rerun()
        st.image(ico_admin, width=100)

    with col2:
        if st.button("Consultar catálogo", use_container_width=True):
            st.session_state.pagina = "consulta"
            st.rerun()
        st.image(ico_consulta, width=100)

elif pagina == "consulta":
    st.markdown(
        "<h5 style='color:darkorange;'>Sección de consulta de catálogo de productos y repuestos</h5>",
        unsafe_allow_html=True
    )

    try:
        productos_df, repuestos_df = descargar_y_extraer_excel()
    except Exception as e:
        st.error(f"Error al descargar o leer los datos: {e}")
        st.stop()

    # --- Catálogo de productos ---
    st.subheader("Catálogo de productos")
    col1, col2 = st.columns([3, 1])
    with col1:
        busqueda_prod = st.text_input("Buscar producto")
    with col2:
        criterio_prod = st.radio("Buscar por:", ["Código", "Descripción", "Numero de Parte"], horizontal=True)

    def filtrar_tabla(df, criterio, texto, columnas):
        if not texto:
            return df
        texto = texto.lower()
        if criterio in columnas:
            return df[df[criterio].astype(str).str.lower().str.contains(texto)]
        return df

    productos_filtrados = filtrar_tabla(productos_df, criterio_prod, busqueda_prod, productos_df.columns)

    gb = GridOptionsBuilder.from_dataframe(productos_filtrados)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    grid_response = AgGrid(
        productos_filtrados,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=250,
        theme="material"
    )

    # Manejo de selección
    selected_rows = grid_response.get("selected_rows", [])
    df_selected = pd.DataFrame(selected_rows)
    sku = None
    if not df_selected.empty:
        fila = df_selected.iloc[0]
        sku = fila.get("Código")

        col_ficha, col_diagrama = st.columns(2)
        with col_ficha:
            link_ficha = fila.get("Link Ficha", "")
            if pd.notna(link_ficha):
                url = quote(link_ficha, safe=":/%?=&")
                st.markdown(f"[📄 Ver Ficha Técnica]({url})", unsafe_allow_html=True)
        with col_diagrama:
            link_diagrama = fila.get("Link Diagrama", "")
            if pd.notna(link_diagrama):
                url = quote(link_diagrama, safe=":/%?=&")
                st.markdown(f"[🗺️ Ver Diagrama]({url})", unsafe_allow_html=True)

        # Mostrar imagen directamente con Streamlit
        link_imagen = fila.get("Imagen(link)", "")
        if link_imagen and str(link_imagen).strip():
            st.image(link_imagen, width=600, caption="Imagen del producto")

    # --- Catálogo de repuestos ---
    st.subheader("Catálogo de repuestos")
    col3, col4 = st.columns([3, 1])
    with col3:
        busqueda_rep = st.text_input("Buscar repuesto")
    with col4:
        criterio_rep = st.radio("Buscar por:", ["Numero de parte del repuesto", "Descripción Repuesto"], horizontal=True)

    if sku is not None:
        repuestos = repuestos_df[repuestos_df.get("Código") == sku].copy()
    else:
        repuestos = repuestos_df.copy()

    repuestos_filtrados = filtrar_tabla(repuestos, criterio_rep, busqueda_rep, repuestos_df.columns)
    st.dataframe(repuestos_filtrados, height=250)

elif pagina == "admin":
    st.warning("Pantalla de administración aún no implementada.")
    if st.button("Volver al inicio"):
        st.session_state.pagina = "inicio"
        st.rerun()
