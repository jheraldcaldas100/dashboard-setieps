from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# CONFIGURACIÓN VISUAL
# ============================================================

COLOR_PRIMARIO = "#0B4F6C"
COLOR_SECUNDARIO = "#01949A"
COLOR_TERCIARIO = "#5BC0BE"
COLOR_ALERTA = "#E15554"
COLOR_MEDIO = "#F4A259"
COLOR_BAJO = "#A8C686"
COLOR_FONDO = "#FAFBFC"
COLOR_TEXTO_SUAVE = "#5C6B73"

PALETA_COMPONENTES = [
    "#0B4F6C", "#01949A", "#5BC0BE", "#F4A259", "#E15554", "#9B7EDE"
]

PALETA_IMPACTO = {
    "ALTO IMPACTO": COLOR_ALERTA,
    "IMPACTO MEDIO": COLOR_MEDIO,
    "BAJO IMPACTO": COLOR_BAJO,
}

st.set_page_config(
    page_title="Dashboard SETIEPS-EPS",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    f"""
    <style>
    .main {{ background-color: {COLOR_FONDO}; }}
    h1, h2, h3 {{ color: {COLOR_PRIMARIO}; }}
    .small-note {{ color: {COLOR_TEXTO_SUAVE}; font-size: 0.90rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def formato_soles(valor: float) -> str:
    if pd.isna(valor):
        return "S/ 0"
    return f"S/ {valor:,.0f}".replace(",", "@").replace(".", ",").replace("@", ".")


def validar_columnas(df: pd.DataFrame, columnas_requeridas: list[str], nombre_archivo: str):
    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]

    if columnas_faltantes:
        st.error(
            f"El archivo {nombre_archivo} no tiene las columnas requeridas: "
            f"{', '.join(columnas_faltantes)}"
        )
        st.stop()


@st.cache_data(show_spinner=False)
def cargar_csv(nombre_archivo: str, columnas_requeridas: list[str]) -> pd.DataFrame:
    ruta = DATA_DIR / nombre_archivo

    if not ruta.exists():
        st.error(f"No se encontró el archivo requerido: data/{nombre_archivo}")
        st.stop()

    try:
        df = pd.read_csv(ruta)
    except Exception as e:
        st.error(f"No se pudo leer el archivo data/{nombre_archivo}.")
        st.exception(e)
        st.stop()

    if df.empty:
        st.error(f"El archivo data/{nombre_archivo} está vacío.")
        st.stop()

    validar_columnas(df, columnas_requeridas, nombre_archivo)

    return df


@st.cache_data(show_spinner=False)
def cargar_datos():
    q4 = cargar_csv(
        "q4.csv",
        ["IPRESS", "TOTAL_PRESTACIONES", "TOTAL_LIQUIDADO_SIN_IGV"]
    )

    q19 = cargar_csv(
        "q19.csv",
        ["FECHA_PRESTACION", "TOTAL_PRESTACIONES_DIA", "TOTAL_LIQUIDADO_DIA", "LIQUIDADO_ACUMULADO"]
    )

    q24 = cargar_csv(
        "q24.csv",
        ["COBERTURA", "COMPONENTE_GASTO", "MONTO_COMPONENTE", "PORC_PARTICIPACION"]
    )

    q13 = cargar_csv(
        "q13.csv",
        ["CODCIE10", "TOTAL_PRESTACIONES", "TOTAL_LIQUIDADO", "CLASIFICACION_IMPACTO"]
    )

    q19["FECHA_PRESTACION"] = pd.to_datetime(q19["FECHA_PRESTACION"], errors="coerce")

    tablas = [q4, q19, q24, q13]

    for df in tablas:
        for col in df.columns:
            col_upper = col.upper()
            if (
                col_upper.startswith("TOTAL")
                or col_upper.startswith("MONTO")
                or col_upper.startswith("PORC")
                or col_upper.startswith("LIQUIDADO")
            ):
                df[col] = pd.to_numeric(df[col], errors="coerce")

    q19 = q19.dropna(subset=["FECHA_PRESTACION"])

    if q19.empty:
        st.error("El archivo q19.csv no tiene fechas válidas en la columna FECHA_PRESTACION.")
        st.stop()

    return q4, q19, q24, q13


# ============================================================
# CARGA DE DATOS CSV
# ============================================================

st.title("Dashboard SETIEPS-EPS")
st.markdown(
    "<div class='small-note'>Gráficos dinámicos cargados de consultas SQL.</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Configuración")
    st.success("Origen de datos: Extraidos de consultas SQL")
    st.caption("Grupo 2")

df_q4, df_q19, df_q24, df_q13 = cargar_datos()


# ============================================================
# INDICADORES GENERALES
# ============================================================

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "Total liquidado IPRESS",
    formato_soles(df_q4["TOTAL_LIQUIDADO_SIN_IGV"].sum())
)

k2.metric(
    "Prestaciones IPRESS",
    f"{df_q4['TOTAL_PRESTACIONES'].sum():,.0f}".replace(",", ".")
)

k3.metric(
    "Último acumulado",
    formato_soles(df_q19["LIQUIDADO_ACUMULADO"].max())
)

k4.metric(
    "Diagnósticos CIE10",
    f"{df_q13['CODCIE10'].nunique():,.0f}".replace(",", ".")
)

st.divider()


# ============================================================
# PESTAÑAS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "Q4 · Top IPRESS",
    "Q19 · Acumulado diario",
    "Q24 · Gasto por cobertura",
    "Q13 · CIE10 prevalentes",
])


# ============================================================
# Q4
# ============================================================

with tab1:
    st.subheader("Q4 - Top IPRESS con mayor monto liquidado")

    max_ipress = len(df_q4)

    if max_ipress < 1:
        st.error("q4.csv no tiene registros para graficar.")
        st.stop()

    top_n = st.slider(
        "Número de IPRESS",
        min_value=1,
        max_value=min(15, max_ipress),
        value=min(3, max_ipress)
    )

    df = (
        df_q4
        .sort_values("TOTAL_LIQUIDADO_SIN_IGV", ascending=False)
        .head(top_n)
    )

    df_plot = df.sort_values("TOTAL_LIQUIDADO_SIN_IGV", ascending=True)

    fig = px.bar(
        df_plot,
        x="TOTAL_LIQUIDADO_SIN_IGV",
        y="IPRESS",
        orientation="h",
        text="TOTAL_LIQUIDADO_SIN_IGV",
        color="TOTAL_LIQUIDADO_SIN_IGV",
        color_continuous_scale=[
            [0, COLOR_TERCIARIO],
            [0.5, COLOR_SECUNDARIO],
            [1, COLOR_PRIMARIO],
        ],
        title="Top IPRESS por monto liquidado sin IGV",
        labels={
            "TOTAL_LIQUIDADO_SIN_IGV": "Monto liquidado sin IGV",
            "IPRESS": "IPRESS",
        },
    )

    fig.update_traces(
        texttemplate="S/ %{x:,.0f}",
        textposition="outside",
        hovertemplate="IPRESS: %{y}<br>Monto: S/ %{x:,.0f}<extra></extra>",
    )

    fig.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        height=460,
        margin=dict(l=10, r=40, t=70, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# Q19
# ============================================================

with tab2:
    st.subheader("Q19 - Monto liquidado acumulado día a día")

    df = df_q19.copy().sort_values("FECHA_PRESTACION")

    fecha_min = df["FECHA_PRESTACION"].min().date()
    fecha_max = df["FECHA_PRESTACION"].max().date()

    inicio, fin = st.slider(
        "Selecciona el rango de fechas",
        min_value=fecha_min,
        max_value=fecha_max,
        value=(fecha_min, fecha_max),
        format="DD/MM/YYYY"
    )

    df = df[
        (df["FECHA_PRESTACION"].dt.date >= inicio)
        & (df["FECHA_PRESTACION"].dt.date <= fin)
    ]

    if df.empty:
        st.warning("No hay datos para el rango de fechas seleccionado.")
        st.stop()

    df["LIQUIDADO_ACUMULADO_FILTRADO"] = df["TOTAL_LIQUIDADO_DIA"].cumsum()

    col_a, col_b, col_c = st.columns(3)

    col_a.metric(
        "Monto del período",
        formato_soles(df["TOTAL_LIQUIDADO_DIA"].sum())
    )

    col_b.metric(
        "Días analizados",
        f"{len(df):,.0f}".replace(",", ".")
    )

    col_c.metric(
        "Prestaciones",
        f"{df['TOTAL_PRESTACIONES_DIA'].sum():,.0f}".replace(",", ".")
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["FECHA_PRESTACION"],
            y=df["LIQUIDADO_ACUMULADO_FILTRADO"],
            mode="lines",
            fill="tozeroy",
            line=dict(color=COLOR_PRIMARIO, width=3),
            name="Liquidado acumulado",
            hovertemplate=(
                "Fecha: %{x|%d/%m/%Y}<br>"
                "Acumulado: S/ %{y:,.0f}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title="Evolución del gasto liquidado acumulado",
        xaxis_title="Fecha de prestación",
        yaxis_title="Monto liquidado acumulado",
        height=500,
        margin=dict(l=10, r=30, t=70, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# Q24
# ============================================================

with tab3:
    st.subheader("Q24 - Composición del gasto por componente y cobertura")

    df = df_q24.copy()

    coberturas = sorted(df["COBERTURA"].dropna().unique())
    componentes = sorted(df["COMPONENTE_GASTO"].dropna().unique())

    col_f1, col_f2 = st.columns(2)

    with col_f1:
        sel_cob = st.multiselect(
            "Coberturas",
            coberturas,
            default=coberturas
        )

    with col_f2:
        sel_comp = st.multiselect(
            "Componentes",
            componentes,
            default=componentes
        )

    df = df[
        df["COBERTURA"].isin(sel_cob)
        & df["COMPONENTE_GASTO"].isin(sel_comp)
    ]

    if df.empty:
        st.warning("No hay datos para los filtros seleccionados.")
        st.stop()

    fig = px.bar(
        df,
        x="PORC_PARTICIPACION",
        y="COBERTURA",
        color="COMPONENTE_GASTO",
        orientation="h",
        text="PORC_PARTICIPACION",
        title="Composición porcentual del gasto por cobertura",
        labels={
            "PORC_PARTICIPACION": "Participación (%)",
            "COBERTURA": "Cobertura",
            "COMPONENTE_GASTO": "Componente",
        },
        color_discrete_sequence=PALETA_COMPONENTES,
    )

    fig.update_traces(
        texttemplate="%{x:.1f}%",
        textposition="inside",
        hovertemplate=(
            "Cobertura: %{y}<br>"
            "Participación: %{x:.2f}%<extra></extra>"
        ),
    )

    fig.update_layout(
        barmode="stack",
        height=500,
        xaxis_range=[0, 100],
        margin=dict(l=10, r=30, t=70, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# Q13
# ============================================================

with tab4:
    st.subheader("Q13 - Diagnósticos CIE10 prevalentes con clasificación de impacto")

    df = df_q13.copy().sort_values("TOTAL_LIQUIDADO", ascending=False)

    impactos_orden = ["ALTO IMPACTO", "IMPACTO MEDIO", "BAJO IMPACTO"]

    impactos_disponibles = [
        impacto
        for impacto in impactos_orden
        if impacto in df["CLASIFICACION_IMPACTO"].unique()
    ]

    if not impactos_disponibles:
        st.error("q13.csv no tiene valores válidos en CLASIFICACION_IMPACTO.")
        st.stop()

    col_f1, col_f2 = st.columns(2)

    with col_f1:
        top_diag = st.slider(
            "Número de diagnósticos",
            min_value=1,
            max_value=min(30, len(df)),
            value=min(10, len(df))
        )

    with col_f2:
        sel_impacto = st.multiselect(
            "Impacto",
            impactos_disponibles,
            default=impactos_disponibles
        )

    df = df[
        df["CLASIFICACION_IMPACTO"].isin(sel_impacto)
    ].head(top_diag)

    if df.empty:
        st.warning("No hay diagnósticos para los filtros seleccionados.")
        st.stop()

    df_plot = df.sort_values("TOTAL_LIQUIDADO", ascending=True)

    fig = px.bar(
        df_plot,
        x="TOTAL_LIQUIDADO",
        y="CODCIE10",
        orientation="h",
        color="CLASIFICACION_IMPACTO",
        color_discrete_map=PALETA_IMPACTO,
        text="TOTAL_LIQUIDADO",
        title="Diagnósticos CIE10 por monto liquidado e impacto económico",
        labels={
            "TOTAL_LIQUIDADO": "Monto liquidado",
            "CODCIE10": "CIE10",
            "CLASIFICACION_IMPACTO": "Impacto",
        },
        hover_data={"TOTAL_PRESTACIONES": True},
    )

    fig.update_traces(
        texttemplate="S/ %{x:,.0f}",
        textposition="outside"
    )

    fig.update_layout(
        height=560,
        margin=dict(l=10, r=40, t=70, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# FUENTE
# ============================================================

st.divider()

st.markdown(
    "<div class='small-note'>Fuente: Base de datos SETIEPS-EPS · IAFAS / IPRESS · Elaboración propia.</div>",
    unsafe_allow_html=True,
)