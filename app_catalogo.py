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

# Inicializar filtro de proveedor
if "filtro_proveedor" not in st.session_state:
    st.session_state.filtro_proveedor = None

# Estilos personalizados para botones (verde claro)
st.markdown(
    """
    <style>
    div.stButton > button, div.stDownloadButton > button {
        background-color: #009E47;
        color: white;
        border-radius: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
    response = requests.get(zip_url)
    response.raise_for_status()
    zip_bytes = io.BytesIO(response.content)

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

# Carga de imágenes
logo = Image.open("logo_taller.png")
ico_admin = Image.open("ico_admin.png")
ico_consulta = Image.open("ico_consulta.png")

# Cabecera con logo, título y botón de actualización
e1, e2, e3 = st.columns([1, 4, 1])
with e1:
    st.image(logo, width=80)
with e2:
    st.markdown(
        """<h1 style='text-align:left; color:#fff; margin-bottom:0;'>Taller de Servicio</h1>""",
        unsafe_allow_html=True
    )
    st.markdown(
        """<h4 style='text-align:left; color:#fff; margin-top:0;'>Silva Internacional S.A</h4>""",
        unsafe_allow_html=True
    )
with e3:
    if st.button("Actualizar datos"):
        st.cache_data.clear()
        st.experimental_rerun()

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
    productos_df, repuestos_df = descargar_y_extraer_excel()

    # Filtro por Proveedor
    proveedores = sorted(productos_df['Proveedor'].dropna().unique())
    opciones = ['Todos'] + proveedores
    cols = st.columns(len(opciones))
    for idx, prov in enumerate(opciones):
        if cols[idx].button(prov):
            st.session_state.filtro_proveedor = None if prov == 'Todos' else prov
    filtro = st.session_state.filtro_proveedor
    df_base = productos_df if not filtro else productos_df[productos_df['Proveedor'] == filtro]

    # Catálogo de productos
    st.subheader("Catálogo de productos")
    col1, col2 = st.columns([3, 1])
    with col1:
        busqueda_prod = st.text_input("Buscar producto")
    with col2:
        criterio_prod = st.radio(
            "Buscar por:",
            ["Proveedor", "Descripción", "Código", "Numero de Parte", "Tipo de producto"],
            horizontal=True
        )
    def filtrar_tabla(df, criterio, texto, columnas):
        if not texto:
            return df
        texto = texto.lower()
        return df[df[criterio].astype(str).str.lower().str.contains(texto)] if criterio in columnas else df
    productos_filtrados = filtrar_tabla(df_base, criterio_prod, busqueda_prod, df_base.columns)

    gb = GridOptionsBuilder.from_dataframe(productos_filtrados)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    grid_response = AgGrid(
        productos_filtrados,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=250,
        theme="material"
    )

    # Manejo de selección y botones
    selected_rows = grid_response.get("selected_rows", [])
    df_selected = pd.DataFrame(selected_rows)
    sku = None
    if not df_selected.empty:
        fila = df_selected.iloc[0]
        sku = fila.get("Código")
        col_ficha, col_diagrama, col_descargar = st.columns(3)
        with col_ficha:
            link_ficha = fila.get("Link Ficha", "")
            if pd.notna(link_ficha):
                url = quote(link_ficha, safe=":/%?=&")
                st.markdown(
                    f'<a href="{url}" target="_blank"><button style="background-color:#009E47;color:white;border:none;padding:6px 12px;border-radius:4px;">📄 Ver Ficha Técnica</button></a>', unsafe_allow_html=True
                )
        with col_diagrama:
            link_diagrama = fila.get("Link Diagrama", "")
            if pd.notna(link_diagrama):
                url = quote(link_diagrama, safe=":/%?=&")
                st.markdown(
                    f'<a href="{url}" target="_blank"><button style="background-color:#009E47;color:white;border:none;padding:6px 12px;border-radius:4px;">🗺️ Ver Diagrama</button></a>', unsafe_allow_html=True
                )
        with col_descargar:
            # Preparar lista de repuestos para el SKU
            df_rep = repuestos_df[repuestos_df['Código'].astype(str) == str(sku)]
            cols_download = [
                "Numero de parte del repuesto",
                "Código Repuesto",
                "Parte en Diagrama",
                "Cantidad de dias para gestion",
                "Descripción Repuesto",
                "Descripción Prov",
                "Tipo de repuesto",
                "Modelo"
            ]
            df_down = df_rep[cols_download] if all(c in df_rep.columns for c in cols_download) else df_rep
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                df_down.to_excel(writer, index=False, sheet_name='Repuestos')
            buf.seek(0)
            st.download_button(
                label="Descargar repuestos",
                data=buf,
                file_name=f"repuestos_{sku}.xlsx",
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        link_imagen = fila.get("Imagen(link)", "")
        if link_imagen and str(link_imagen).strip():
            st.image(link_imagen, width=600, caption="Imagen del producto")

    # Catálogo de repuestos completo
    st.subheader("Catálogo de repuestos")
    col3, col4 = st.columns([3, 1])
    with col3:
        busqueda_rep = st.text_input("Buscar repuesto")
    with col4:
        criterio_rep = st.radio(
            "Buscar por:",
            ["Proveedor", "Descripcion Repuesto"], horizontal=True
        )
    repuestos = repuestos_df[repuestos_df['Código'] == sku].copy() if sku else repuestos_df.copy()
    repuestos_filtrados = filtrar_tabla(repuestos, criterio_rep, busqueda_rep, repuestos_df.columns)
    st.dataframe(repuestos_filtrados, height=250)

elif pagina == "admin":
    st.warning("Pantalla de administración aún no implementada.")
    if st.button("Volver al inicio"):
        st.session_state.pagina = "inicio"
        st.rerun()
