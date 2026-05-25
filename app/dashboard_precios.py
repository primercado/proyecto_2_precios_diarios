"""Dashboard local de precios diarios SEPA con Streamlit."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except ImportError:  # pragma: no cover - depende del entorno local.
    px = None


DB_PATH = Path("data/processed/precios_diarios.duckdb")

REQUIRED_MARTS = (
    "mart_resumen_general",
    "mart_evolucion_productos",
    "mart_variacion_productos",
    "mart_resumen_productos",
    "mart_precios_por_comercio",
    "mart_precios_por_ubicacion",
    "mart_promociones",
    "mart_productos_mayor_dispersion",
    "mart_sucursales_geografia",
    "mart_calidad_precios",
    "mart_productos_comparables",
    "mart_precios_sospechosos",
    "mart_canasta_basica_candidatos",
)

SECTION_OPTIONS = (
    "Sobre el proyecto",
    "Resumen general",
    "Precios por comercio",
    "Buscador de productos",
    "Precios por ubicación",
    "Promociones",
    "Mayor dispersión",
    "Sucursales georreferenciadas",
    "Calidad de precios",
    "Buscador avanzado",
    "Canasta básica exploratoria",
    "Comparación entre fechas",
    "Evolución de producto",
)

DISPLAY_COLUMN_NAMES = {
    "fecha_publicacion": "Fecha",
    "id_producto": "ID producto",
    "productos_descripcion": "Producto",
    "productos_marca": "Marca",
    "productos_cantidad_presentacion": "Presentación",
    "productos_unidad_medida_presentacion": "Unidad",
    "productos_precio_lista": "Precio lista",
    "productos_precio_referencia": "Precio referencia",
    "precio_minimo": "Precio mínimo",
    "precio_maximo": "Precio máximo",
    "precio_promedio": "Precio promedio",
    "precio_mediano_aproximado": "Precio mediano aprox.",
    "precio_referencia_promedio": "Precio ref. promedio",
    "precio_promedio_general": "Precio promedio general",
    "precio_promedio_lista": "Precio promedio lista",
    "precio_promedio_promo1": "Precio promo 1",
    "precio_promedio_promo2": "Precio promo 2",
    "precio_promedio_anterior": "Precio promedio anterior",
    "precio_promedio_actual": "Precio promedio actual",
    "cantidad_registros": "Registros",
    "cantidad_registros_actual": "Registros actuales",
    "cantidad_registros_anterior": "Registros anteriores",
    "cantidad_registros_precios": "Registros de precios",
    "cantidad_productos": "Productos",
    "cantidad_productos_unicos": "Productos únicos",
    "cantidad_sucursales": "Sucursales",
    "cantidad_comercios": "Comercios",
    "cantidad_banderas": "Banderas",
    "cantidad_provincias": "Provincias",
    "cantidad_localidades": "Localidades",
    "cantidad_precio_cero": "Precios cero",
    "cantidad_precio_menor_10": "Precios menores a 10",
    "cantidad_registros_con_promo1": "Registros promo 1",
    "cantidad_registros_con_promo2": "Registros promo 2",
    "categoria_canasta": "Categoría",
    "variacion_absoluta": "Variación absoluta",
    "variacion_porcentual": "Variación %",
    "diferencia_absoluta_max_min": "Diferencia absoluta",
    "diferencia_porcentual_max_min": "Diferencia %",
    "comercio_bandera_nombre": "Comercio",
    "sucursales_nombre": "Sucursal",
    "sucursales_localidad": "Localidad",
    "sucursales_provincia": "Provincia",
    "sucursales_latitud": "Latitud",
    "sucursales_longitud": "Longitud",
    "regla_calidad": "Regla de calidad",
    "fechas_disponibles": "Fechas disponibles",
    "registros_totales": "Registros totales",
}

PRICE_COLUMNS = {
    "precio_minimo",
    "precio_maximo",
    "precio_promedio",
    "precio_mediano_aproximado",
    "precio_referencia_promedio",
    "precio_promedio_general",
    "precio_promedio_lista",
    "precio_promedio_promo1",
    "precio_promedio_promo2",
    "precio_promedio_anterior",
    "precio_promedio_actual",
    "productos_precio_lista",
    "productos_precio_referencia",
    "variacion_absoluta",
    "diferencia_absoluta_max_min",
}

PERCENT_COLUMNS = {
    "variacion_porcentual",
    "diferencia_porcentual_max_min",
}


st.set_page_config(page_title="Precios Diarios SEPA", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --portfolio-bg: #f7f8fa;
        --portfolio-panel: #ffffff;
        --portfolio-panel-border: #d8dee8;
        --portfolio-text: #18212f;
        --portfolio-text-muted: #64748b;
        --portfolio-accent: #0f766e;
        --portfolio-accent-soft: #e6fffb;
    }
    .stApp {
        background: var(--portfolio-bg);
        color: var(--portfolio-text);
    }
    .stApp,
    .stApp p,
    .stApp span,
    .stApp label,
    .stApp div,
    .stApp li,
    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4,
    .stApp h5,
    .stApp h6,
    .stMarkdown,
    .stCaptionContainer,
    [data-testid="stMarkdownContainer"],
    [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] {
        color: var(--portfolio-text);
    }
    [data-testid="stCaptionContainer"],
    [data-testid="stWidgetLabel"] p,
    [data-testid="stMarkdownContainer"] small {
        color: var(--portfolio-text-muted);
    }
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1320px;}
    h1, h2, h3 {letter-spacing: 0;}
    h1 {font-size: 2.05rem; margin-bottom: 0.2rem;}
    h2, h3 {margin-top: 0.8rem;}
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--portfolio-panel-border);
    }
    .hero-panel {
        background: linear-gradient(135deg, #ffffff 0%, var(--portfolio-accent-soft) 100%);
        border: 1px solid var(--portfolio-panel-border);
        border-radius: 8px;
        padding: 1.2rem 1.25rem;
        margin: 0.75rem 0 1rem 0;
    }
    .section-card {
        background: var(--portfolio-panel);
        border: 1px solid var(--portfolio-panel-border);
        border-radius: 8px;
        padding: 1rem 1.1rem;
        margin: 0.75rem 0 1rem 0;
    }
    .section-card p, .section-card li, .hero-panel p {color: #334155;}
    .muted {color: var(--portfolio-text-muted);}
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid var(--portfolio-panel-border);
        border-radius: 8px;
        padding: 0.85rem 0.95rem;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
    }
    div[data-testid="stMetric"],
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] p,
    div[data-testid="stMetric"] div {
        color: var(--portfolio-text);
    }
    div[data-testid="stMetricLabel"] {
        color: var(--portfolio-text-muted);
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.35rem;
        color: var(--portfolio-text);
    }
    input,
    textarea,
    [data-baseweb="select"] div,
    [data-baseweb="input"] input {
        color: var(--portfolio-text);
        background: #ffffff;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--portfolio-panel-border);
        border-radius: 8px;
        overflow: hidden;
    }
    div[data-testid="stAlert"] {
        border-radius: 8px;
        border: 1px solid var(--portfolio-panel-border);
    }
    hr {
        border-color: rgba(148, 163, 184, 0.20);
    }
    .sidebar-note {
        border-top: 1px solid var(--portfolio-panel-border);
        margin-top: 1rem;
        padding-top: 0.8rem;
        color: var(--portfolio-text-muted);
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_connection(db_path: str) -> duckdb.DuckDBPyConnection:
    """Open DuckDB in read-only mode for Streamlit sessions."""
    return duckdb.connect(db_path, read_only=True)


def run_query(
    con: duckdb.DuckDBPyConnection,
    query: str,
    params: list[object] | None = None,
) -> pd.DataFrame:
    return con.execute(query, params or []).fetchdf()


def format_integer(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{int(value):,}".replace(",", ".")


def format_number(value: object) -> str:
    return format_integer(value)


def format_currency(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return "$" + f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_money(value: object) -> str:
    return format_currency(value)


def format_percentage(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value: object) -> str:
    return format_percentage(value)


def rename_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={k: v for k, v in DISPLAY_COLUMN_NAMES.items() if k in df.columns})


def prepare_display_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    display_df = df.copy()
    for column in PRICE_COLUMNS & set(display_df.columns):
        display_df[column] = pd.to_numeric(display_df[column], errors="coerce").round(2)
    for column in PERCENT_COLUMNS & set(display_df.columns):
        display_df[column] = pd.to_numeric(display_df[column], errors="coerce").round(2)
    return rename_display_columns(display_df)


def show_dataframe(df: pd.DataFrame, **kwargs: object) -> None:
    st.dataframe(prepare_display_dataframe(df), use_container_width=True, **kwargs)


def show_missing_database_message() -> None:
    st.error(f"No existe la base DuckDB esperada: `{DB_PATH}`.")
    st.markdown(
        "Primero ejecuta:"
        "\n\n```bash\n"
        "python -m src.load.load_duckdb --zip data/raw/sepa_sabado.zip --db data/processed/precios_diarios.duckdb\n"
        "python -m src.analysis.create_dashboard_tables --db data/processed/precios_diarios.duckdb\n"
        "```"
    )


def get_existing_marts(con: duckdb.DuckDBPyConnection) -> set[str]:
    rows = con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
            AND table_name = ANY(?)
        """,
        [list(REQUIRED_MARTS)],
    ).fetchall()
    return {row[0] for row in rows}


def mart_exists(con: duckdb.DuckDBPyConnection, mart_name: str) -> bool:
    row = con.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'main'
            AND table_name = ?
        """,
        [mart_name],
    ).fetchone()
    return bool(row and row[0] > 0)


def get_publication_date(con: duckdb.DuckDBPyConnection) -> str:
    result = con.execute(
        "SELECT max(fecha_publicacion) FROM mart_resumen_general"
    ).fetchone()
    return str(result[0]) if result and result[0] is not None else "Sin fecha"


def get_publication_dates(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.execute(
        """
        SELECT DISTINCT fecha_publicacion
        FROM mart_resumen_general
        WHERE fecha_publicacion IS NOT NULL
        ORDER BY fecha_publicacion DESC
        """
    ).fetchall()
    return [str(row[0]) for row in rows]


def render_sidebar(
    con: duckdb.DuckDBPyConnection,
    db_status: str,
) -> tuple[str, str, str | None, str | None]:
    st.sidebar.header("Precios SEPA")
    st.sidebar.write(f"Estado de la base: **{db_status}**")
    date_options = get_publication_dates(con)
    selected_date = st.sidebar.selectbox(
        "Fecha de publicación",
        date_options or [get_publication_date(con)],
    )
    section = st.sidebar.selectbox("Sección", SECTION_OPTIONS)
    comparison_start = None
    comparison_end = None
    if section == "Comparación entre fechas":
        st.sidebar.divider()
        st.sidebar.subheader("Comparación entre fechas")
        ascending_dates = list(reversed(date_options))
        if len(ascending_dates) >= 2:
            comparison_start = st.sidebar.selectbox(
                "Fecha inicial",
                ascending_dates,
                index=max(len(ascending_dates) - 2, 0),
            )
            comparison_end = st.sidebar.selectbox(
                "Fecha final",
                ascending_dates,
                index=len(ascending_dates) - 1,
            )
    st.sidebar.markdown(
        """
        <div class="sidebar-note">
            Dashboard local sobre marts analíticos en DuckDB. La base se abre en
            modo solo lectura.
        </div>
        """,
        unsafe_allow_html=True,
    )
    return section, selected_date, comparison_start, comparison_end


def render_plotly_bar(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
) -> None:
    if px is None:
        st.info("Plotly no está instalado en este entorno.")
        return
    if data.empty:
        return
    fig = px.bar(data, x=x, y=y, title=title, color_discrete_sequence=["#0f766e"])
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font_color="#18212f",
        xaxis_tickangle=-35,
        margin=dict(l=20, r=20, t=60, b=80),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_plotly_horizontal_bar(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
) -> None:
    if px is None:
        st.info("Plotly no está instalado en este entorno.")
        return
    if data.empty:
        return
    chart_df = data.sort_values(x)
    fig = px.bar(
        chart_df,
        x=x,
        y=y,
        orientation="h",
        title=title,
        color_discrete_sequence=["#0f766e"],
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font_color="#18212f",
        height=520,
        yaxis_title="",
        xaxis_title="",
        margin=dict(l=20, r=20, t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_comparability_warning() -> None:
    st.warning(
        "Las comparaciones se realizan agrupando productos por ID, descripción, "
        "marca, presentación y unidad. Aun así, pueden existir inconsistencias "
        "de carga o productos no estrictamente equivalentes."
    )


def render_about_project(con: duckdb.DuckDBPyConnection, selected_date: str) -> None:
    st.title("Precios Diarios SEPA Argentina")
    st.markdown(
        """
        <div class="hero-panel">
            <p class="muted">Pipeline de datos y dashboard interactivo</p>
            <p>
                Análisis local de precios diarios de supermercados publicados por
                SEPA Argentina. El proyecto integra extracción, carga incremental
                en DuckDB, marts analíticos y una app Streamlit para explorar
                productos, comercios, ubicaciones y variaciones entre fechas.
            </p>
            <p class="muted">
                Stack: Python, DuckDB, Streamlit, Pandas, Plotly y SQL.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    summary_df = run_query(
        con,
        """
        SELECT
            cantidad_registros_precios,
            cantidad_productos_unicos,
            cantidad_sucursales
        FROM mart_resumen_general
        WHERE fecha_publicacion = ?
        ORDER BY fecha_publicacion DESC
        LIMIT 1
        """,
        [selected_date],
    )
    dates_loaded = run_query(
        con,
        "SELECT COUNT(DISTINCT fecha_publicacion) AS fechas_cargadas FROM mart_resumen_general",
    ).iloc[0]["fechas_cargadas"]

    if not summary_df.empty:
        row = summary_df.iloc[0]
        cols = st.columns(4)
        cols[0].metric("Registros procesados", format_integer(row["cantidad_registros_precios"]))
        cols[1].metric("Productos únicos", format_integer(row["cantidad_productos_unicos"]))
        cols[2].metric("Sucursales", format_integer(row["cantidad_sucursales"]))
        cols[3].metric("Fechas cargadas", format_integer(dates_loaded))

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Qué permite hacer")
        st.markdown(
            """
            - Comparar precios por fecha.
            - Buscar productos.
            - Analizar evolución temporal.
            - Detectar promociones.
            - Revisar calidad de datos.
            - Explorar una canasta básica aproximada.
            """
        )
    with col_b:
        st.markdown("#### Alcance")
        st.warning(
            "Este proyecto es exploratorio y de portfolio. Las comparaciones "
            "dependen de la calidad y consistencia de los datos publicados."
        )


def render_summary(con: duckdb.DuckDBPyConnection, selected_date: str) -> None:
    st.subheader("Resumen general")
    df = run_query(
        con,
        """
        SELECT *
        FROM mart_resumen_general
        WHERE fecha_publicacion = ?
        ORDER BY fecha_publicacion DESC
        """,
        [selected_date],
    )

    if df.empty:
        st.warning("El mart de resumen general no tiene filas.")
        return

    row = df.iloc[0]
    metrics = [
        ("Registros de precios", "cantidad_registros_precios"),
        ("Productos únicos", "cantidad_productos_unicos"),
        ("Comercios", "cantidad_comercios"),
        ("Banderas", "cantidad_banderas"),
        ("Sucursales", "cantidad_sucursales"),
        ("Provincias", "cantidad_provincias"),
        ("Localidades", "cantidad_localidades"),
    ]

    cols = st.columns(4)
    for index, (label, column) in enumerate(metrics):
        cols[index % 4].metric(label, format_integer(row[column]))

    show_dataframe(df)


def render_prices_by_store(con: duckdb.DuckDBPyConnection, selected_date: str) -> None:
    st.subheader("Precios por comercio")
    columns = [
        "comercio_bandera_nombre",
        "cantidad_registros",
        "cantidad_productos",
        "cantidad_sucursales",
        "precio_promedio",
        "precio_minimo",
        "precio_maximo",
    ]
    df = run_query(
        con,
        f"""
        SELECT {", ".join(columns)}
        FROM mart_precios_por_comercio
        WHERE fecha_publicacion = ?
        ORDER BY cantidad_productos DESC, comercio_bandera_nombre
        LIMIT 100
        """,
        [selected_date],
    )
    show_dataframe(df)
    render_plotly_bar(
        df,
        x="comercio_bandera_nombre",
        y="cantidad_productos",
        title="Cantidad de productos por comercio",
    )


def render_product_search(con: duckdb.DuckDBPyConnection, selected_date: str) -> None:
    st.subheader("Buscador de productos")
    product_text = st.text_input("Producto buscado", value="COCA COLA")
    limit = st.slider("Límite de resultados", min_value=10, max_value=500, value=100, step=10)

    columns = [
        "id_producto",
        "productos_descripcion",
        "productos_marca",
        "cantidad_registros",
        "precio_minimo",
        "precio_maximo",
        "precio_promedio",
        "precio_mediano_aproximado",
        "diferencia_absoluta_max_min",
        "diferencia_porcentual_max_min",
    ]
    search_pattern = f"%{product_text.strip()}%"
    df = run_query(
        con,
        f"""
        SELECT {", ".join(columns)}
        FROM mart_resumen_productos
        WHERE fecha_publicacion = ?
            AND productos_descripcion ILIKE ?
        ORDER BY precio_minimo ASC NULLS LAST
        LIMIT ?
        """,
        [selected_date, search_pattern, limit],
    )
    show_dataframe(df)


def render_price_quality(con: duckdb.DuckDBPyConnection, selected_date: str) -> None:
    st.subheader("Calidad de precios")
    st.markdown(
        "Los precios sospechosos no se eliminan automáticamente; se marcan "
        "para análisis y pueden requerir revisión."
    )

    df = run_query(
        con,
        """
        SELECT *
        FROM mart_calidad_precios
        WHERE fecha_publicacion = ?
        ORDER BY fecha_publicacion DESC
        """,
        [selected_date],
    )
    if df.empty:
        st.warning("El mart de calidad de precios no tiene filas.")
        return

    row = df.iloc[0]
    metrics = [
        ("Precios cero", "cantidad_precio_cero"),
        ("Precios menores a 10", "cantidad_precio_menor_10"),
        ("Precio mínimo", "precio_minimo"),
        ("Precio máximo", "precio_maximo"),
        ("Precio promedio", "precio_promedio"),
    ]
    cols = st.columns(len(metrics))
    for index, (label, column) in enumerate(metrics):
        formatter = format_currency if column.startswith("precio_") else format_integer
        cols[index].metric(label, formatter(row[column]))

    show_dataframe(df)

    if mart_exists(con, "mart_precios_sospechosos"):
        suspicious_df = run_query(
            con,
            """
            SELECT
                fecha_publicacion,
                regla_calidad,
                id_producto,
                productos_descripcion,
                productos_marca,
                productos_cantidad_presentacion,
                productos_unidad_medida_presentacion,
                productos_precio_lista,
                productos_precio_referencia
            FROM mart_precios_sospechosos
            WHERE fecha_publicacion = ?
            LIMIT 1000
            """,
            [selected_date],
        )
        st.markdown("Registros marcados para revisión")
        show_dataframe(suspicious_df)


def render_advanced_product_search(con: duckdb.DuckDBPyConnection, selected_date: str) -> None:
    st.subheader("Buscador avanzado")
    st.markdown("Comparar productos requiere revisar presentación y unidad de medida.")

    brand_options = run_query(
        con,
        """
        SELECT DISTINCT productos_marca
        FROM mart_productos_comparables
        WHERE fecha_publicacion = ?
            AND productos_marca IS NOT NULL
            AND productos_marca <> ''
        ORDER BY productos_marca
        LIMIT 1000
        """,
        [selected_date],
    )["productos_marca"].tolist()
    unit_options = run_query(
        con,
        """
        SELECT DISTINCT productos_unidad_medida_presentacion
        FROM mart_productos_comparables
        WHERE fecha_publicacion = ?
            AND productos_unidad_medida_presentacion IS NOT NULL
            AND productos_unidad_medida_presentacion <> ''
        ORDER BY productos_unidad_medida_presentacion
        """,
        [selected_date],
    )["productos_unidad_medida_presentacion"].tolist()

    col_a, col_b, col_c = st.columns(3)
    product_text = col_a.text_input("Texto de búsqueda", value="LECHE")
    selected_brand = col_b.selectbox("Marca", ["Todas"] + brand_options)
    selected_unit = col_c.selectbox("Unidad de medida", ["Todas"] + unit_options)

    col_d, col_e, col_f = st.columns(3)
    max_price = col_d.number_input(
        "Precio máximo opcional",
        min_value=0.0,
        value=0.0,
        step=100.0,
        help="Usa 0 para no aplicar filtro.",
    )
    min_records = col_e.number_input(
        "Cantidad mínima de registros",
        min_value=1,
        value=20,
        step=1,
    )
    limit = col_f.slider("Límite de resultados", min_value=10, max_value=1000, value=100, step=10)

    where_clauses = ["fecha_publicacion = ?", "cantidad_registros >= ?"]
    params: list[object] = [selected_date, int(min_records)]
    if product_text.strip():
        where_clauses.append("productos_descripcion ILIKE ?")
        params.append(f"%{product_text.strip()}%")
    if selected_brand != "Todas":
        where_clauses.append("productos_marca = ?")
        params.append(selected_brand)
    if selected_unit != "Todas":
        where_clauses.append("productos_unidad_medida_presentacion = ?")
        params.append(selected_unit)
    if max_price > 0:
        where_clauses.append("precio_minimo <= ?")
        params.append(float(max_price))
    params.append(int(limit))

    columns = [
        "productos_descripcion",
        "productos_marca",
        "productos_cantidad_presentacion",
        "productos_unidad_medida_presentacion",
        "cantidad_registros",
        "precio_minimo",
        "precio_maximo",
        "precio_promedio",
        "precio_referencia_promedio",
        "diferencia_porcentual_max_min",
    ]
    df = run_query(
        con,
        f"""
        SELECT {", ".join(columns)}
        FROM mart_productos_comparables
        WHERE {" AND ".join(where_clauses)}
        ORDER BY precio_minimo ASC NULLS LAST, cantidad_registros DESC
        LIMIT ?
        """,
        params,
    )
    show_dataframe(df)


def render_basic_basket_candidates(con: duckdb.DuckDBPyConnection, selected_date: str) -> None:
    st.subheader("Canasta básica exploratoria")
    st.warning(
        "Esta canasta es exploratoria. Se basa en búsquedas por texto y no "
        "representa una canasta oficial."
    )

    categories = [
        "LECHE",
        "ARROZ",
        "FIDEO",
        "YERBA",
        "ACEITE",
        "AZUCAR",
        "HARINA",
        "HUEVO",
    ]
    unit_options = run_query(
        con,
        """
        SELECT DISTINCT productos_unidad_medida_presentacion
        FROM mart_canasta_basica_candidatos
        WHERE fecha_publicacion = ?
            AND productos_unidad_medida_presentacion IS NOT NULL
            AND productos_unidad_medida_presentacion <> ''
        ORDER BY productos_unidad_medida_presentacion
        """,
        [selected_date],
    )["productos_unidad_medida_presentacion"].tolist()

    selected_categories = st.multiselect(
        "Categorías de canasta",
        categories,
        default=categories,
    )

    col_a, col_b, col_c, col_d = st.columns(4)
    min_records = col_a.number_input(
        "Cantidad mínima de registros",
        min_value=1,
        value=20,
        step=1,
    )
    max_price = col_b.number_input(
        "Precio máximo",
        min_value=0.0,
        value=0.0,
        step=100.0,
        help="Usa 0 para no aplicar filtro.",
    )
    selected_unit = col_c.selectbox("Unidad de medida", ["Todas"] + unit_options)
    limit_per_category = col_d.slider(
        "Candidatos por categoría",
        min_value=5,
        max_value=100,
        value=20,
        step=5,
    )

    if not selected_categories:
        st.info("Seleccioná al menos una categoría.")
        return

    where_clauses = [
        "fecha_publicacion = ?",
        "categoria_canasta = ANY(?)",
        "cantidad_registros >= ?",
    ]
    params: list[object] = [selected_date, selected_categories, int(min_records)]
    if max_price > 0:
        where_clauses.append("precio_minimo <= ?")
        params.append(float(max_price))
    if selected_unit != "Todas":
        where_clauses.append("productos_unidad_medida_presentacion = ?")
        params.append(selected_unit)
    params.append(int(limit_per_category))

    df = run_query(
        con,
        f"""
        WITH ordenados AS (
            SELECT
                categoria_canasta,
                productos_descripcion,
                productos_marca,
                productos_cantidad_presentacion,
                productos_unidad_medida_presentacion,
                precio_minimo,
                precio_promedio,
                cantidad_registros,
                row_number() OVER (
                    PARTITION BY categoria_canasta
                    ORDER BY cantidad_registros DESC, precio_minimo ASC NULLS LAST
                ) AS orden_categoria
            FROM mart_canasta_basica_candidatos
            WHERE {" AND ".join(where_clauses)}
        )
        SELECT
            categoria_canasta,
            productos_descripcion,
            productos_marca,
            productos_cantidad_presentacion,
            productos_unidad_medida_presentacion,
            precio_minimo,
            precio_promedio,
            cantidad_registros
        FROM ordenados
        WHERE orden_categoria <= ?
        ORDER BY categoria_canasta, cantidad_registros DESC, precio_minimo ASC NULLS LAST
        """,
        params,
    )
    show_dataframe(df)


def render_date_comparison(
    con: duckdb.DuckDBPyConnection,
    start_date: str | None,
    end_date: str | None,
) -> None:
    st.subheader("Comparación entre fechas")
    st.caption(
        "Compara productos presentes en ambas fechas y calcula variación promedio."
    )
    st.warning(
        "Las variaciones pueden reflejar cambios reales, diferencias de carga "
        "o productos no estrictamente equivalentes."
    )

    date_options = get_publication_dates(con)
    if len(date_options) < 2:
        st.info(
            "Todavía no hay suficientes fechas cargadas para comparar días. "
            "Cargá más fechas con el pipeline incremental."
        )
        return
    if start_date is None or end_date is None:
        st.info("Seleccioná fecha inicial y fecha final en la barra lateral.")
        return
    if start_date == end_date:
        st.warning("Seleccioná dos fechas distintas para comparar.")
        return
    if start_date > end_date:
        st.warning("La fecha inicial debe ser anterior a la fecha final.")
        return

    summary_df = run_query(
        con,
        """
        SELECT
            fecha_publicacion,
            cantidad_registros_precios,
            cantidad_productos_unicos,
            precio_promedio_general
        FROM mart_resumen_general
        WHERE fecha_publicacion = ANY(?)
        """,
        [[start_date, end_date]],
    )
    if len(summary_df) < 2:
        st.warning("No hay resumen general completo para las fechas seleccionadas.")
        return

    summary_df["fecha_key"] = pd.to_datetime(
        summary_df["fecha_publicacion"]
    ).dt.strftime("%Y-%m-%d")
    by_date = {row.fecha_key: row for row in summary_df.itertuples()}
    start_row = by_date[start_date]
    end_row = by_date[end_date]
    registros_diff = (
        end_row.cantidad_registros_precios - start_row.cantidad_registros_precios
    )
    productos_diff = (
        end_row.cantidad_productos_unicos - start_row.cantidad_productos_unicos
    )
    precio_diff = end_row.precio_promedio_general - start_row.precio_promedio_general
    precio_pct = (
        (precio_diff / start_row.precio_promedio_general) * 100
        if start_row.precio_promedio_general
        else None
    )

    with st.container():
        st.markdown("#### Métricas generales")
        cols = st.columns(4)
        cols[0].metric("Registros fecha inicial", format_integer(start_row.cantidad_registros_precios))
        cols[1].metric("Registros fecha final", format_integer(end_row.cantidad_registros_precios))
        cols[2].metric("Diferencia registros", format_integer(registros_diff))
        cols[3].metric("Productos únicos inicial", format_integer(start_row.cantidad_productos_unicos))

        cols = st.columns(4)
        cols[0].metric("Productos únicos final", format_integer(end_row.cantidad_productos_unicos))
        cols[1].metric("Diferencia productos", format_integer(productos_diff))
        cols[2].metric("Precio promedio inicial", format_currency(start_row.precio_promedio_general))
        cols[3].metric(
            "Precio promedio final",
            format_currency(end_row.precio_promedio_general),
            delta=format_percentage(precio_pct),
        )

    st.divider()
    unit_options = run_query(
        con,
        """
        SELECT DISTINCT productos_unidad_medida_presentacion
        FROM mart_variacion_productos
        WHERE fecha_publicacion = ?
            AND fecha_anterior = ?
            AND productos_unidad_medida_presentacion IS NOT NULL
            AND productos_unidad_medida_presentacion <> ''
        ORDER BY productos_unidad_medida_presentacion
        LIMIT 100
        """,
        [end_date, start_date],
    )["productos_unidad_medida_presentacion"].tolist()

    col_a, col_b, col_c = st.columns(3)
    min_records = col_a.number_input(
        "Cantidad mínima de registros",
        min_value=1,
        value=20,
        step=1,
    )
    limit = col_b.slider("Límite de resultados", min_value=10, max_value=200, value=50, step=10)
    selected_unit = col_c.selectbox("Unidad de medida", ["Todas"] + unit_options)

    where_clauses = [
        "fecha_publicacion = ?",
        "fecha_anterior = ?",
        "cantidad_registros_actual >= ?",
        "cantidad_registros_anterior >= ?",
        "variacion_porcentual IS NOT NULL",
    ]
    params: list[object] = [end_date, start_date, int(min_records), int(min_records)]
    if selected_unit != "Todas":
        where_clauses.append("productos_unidad_medida_presentacion = ?")
        params.append(selected_unit)

    columns = [
        "productos_descripcion",
        "productos_marca",
        "productos_cantidad_presentacion",
        "productos_unidad_medida_presentacion",
        "precio_promedio_anterior",
        "precio_promedio_actual",
        "variacion_absoluta",
        "variacion_porcentual",
        "cantidad_registros_anterior",
        "cantidad_registros_actual",
    ]

    increases = run_query(
        con,
        f"""
        SELECT {", ".join(columns)}
        FROM mart_variacion_productos
        WHERE {" AND ".join(where_clauses)}
            AND variacion_absoluta > 0
        ORDER BY variacion_porcentual DESC, cantidad_registros_actual DESC
        LIMIT ?
        """,
        params + [int(limit)],
    )
    decreases = run_query(
        con,
        f"""
        SELECT {", ".join(columns)}
        FROM mart_variacion_productos
        WHERE {" AND ".join(where_clauses)}
            AND variacion_absoluta < 0
        ORDER BY variacion_porcentual ASC, cantidad_registros_actual DESC
        LIMIT ?
        """,
        params + [int(limit)],
    )

    if increases.empty and decreases.empty:
        st.info(
            "No hay productos comparables para esas fechas con los filtros actuales. "
            "Probá bajar la cantidad mínima de registros."
        )
        return

    col_up, col_down = st.columns(2)
    with col_up:
        st.markdown("#### Mayores subas")
        show_dataframe(increases, height=360)
    with col_down:
        st.markdown("#### Mayores bajas")
        show_dataframe(decreases, height=360)

    def add_chart_label(df: pd.DataFrame) -> pd.DataFrame:
        chart_df = df.head(20).copy()
        chart_df["producto"] = (
            chart_df["productos_descripcion"].fillna("").str.slice(0, 58)
            + " | "
            + chart_df["productos_marca"].fillna("S/M")
        )
        return chart_df

    st.divider()
    col_up_chart, col_down_chart = st.columns(2)
    with col_up_chart:
        render_plotly_horizontal_bar(
            add_chart_label(increases),
            x="variacion_porcentual",
            y="producto",
            title="Mayor aumento porcentual",
        )
    with col_down_chart:
        render_plotly_horizontal_bar(
            add_chart_label(decreases),
            x="variacion_porcentual",
            y="producto",
            title="Mayor baja porcentual",
        )


def render_product_evolution(con: duckdb.DuckDBPyConnection) -> None:
    st.subheader("Evolución de producto")
    st.caption(
        "Buscá un producto y observá cómo cambia su precio promedio entre fechas cargadas."
    )
    render_comparability_warning()

    date_options = get_publication_dates(con)
    has_temporal_depth = len(date_options) >= 2
    if not has_temporal_depth:
        st.info(
            "Hay una sola fecha cargada. Se muestra el dato disponible, pero la "
            "evolución temporal requiere más fechas cargadas."
        )
    elif len(date_options) == 2:
        st.info(
            "Hay solo dos fechas cargadas. La evolución temporal todavía es inicial "
            "y conviene interpretarla como una primera comparación."
        )

    col_a, col_b, col_c = st.columns(3)
    product_text = col_a.text_input("Buscar producto por texto", value="LECHE")

    brand_options: list[str] = []
    unit_options: list[str] = []
    if product_text.strip():
        search_pattern = f"%{product_text.strip()}%"
        brand_options = run_query(
            con,
            """
            SELECT DISTINCT productos_marca
            FROM mart_evolucion_productos
            WHERE productos_descripcion ILIKE ?
                AND productos_marca IS NOT NULL
                AND productos_marca <> ''
            ORDER BY productos_marca
            LIMIT 200
            """,
            [search_pattern],
        )["productos_marca"].tolist()
        unit_options = run_query(
            con,
            """
            SELECT DISTINCT productos_unidad_medida_presentacion
            FROM mart_evolucion_productos
            WHERE productos_descripcion ILIKE ?
                AND productos_unidad_medida_presentacion IS NOT NULL
                AND productos_unidad_medida_presentacion <> ''
            ORDER BY productos_unidad_medida_presentacion
            LIMIT 100
            """,
            [search_pattern],
        )["productos_unidad_medida_presentacion"].tolist()

    selected_brand = col_b.selectbox("Marca opcional", ["Todas"] + brand_options)
    selected_unit = col_c.selectbox("Unidad opcional", ["Todas"] + unit_options)

    if not product_text.strip():
        st.info("Ingresá un texto para buscar productos.")
        return

    where_clauses = ["productos_descripcion ILIKE ?"]
    params: list[object] = [f"%{product_text.strip()}%"]
    if selected_brand != "Todas":
        where_clauses.append("productos_marca = ?")
        params.append(selected_brand)
    if selected_unit != "Todas":
        where_clauses.append("productos_unidad_medida_presentacion = ?")
        params.append(selected_unit)

    products_df = run_query(
        con,
        f"""
        SELECT
            id_producto,
            productos_descripcion,
            productos_marca,
            productos_cantidad_presentacion,
            productos_unidad_medida_presentacion,
            COUNT(DISTINCT fecha_publicacion) AS fechas_disponibles,
            SUM(cantidad_registros) AS registros_totales
        FROM mart_evolucion_productos
        WHERE {" AND ".join(where_clauses)}
        GROUP BY
            id_producto,
            productos_descripcion,
            productos_marca,
            productos_cantidad_presentacion,
            productos_unidad_medida_presentacion
        ORDER BY fechas_disponibles DESC, registros_totales DESC
        LIMIT 100
        """,
        params,
    )
    if products_df.empty:
        st.warning("No se encontraron productos con esos filtros.")
        return

    products_df["opcion"] = (
        products_df["productos_descripcion"].fillna("")
        + " | "
        + products_df["productos_marca"].fillna("S/M")
        + " | "
        + products_df["productos_cantidad_presentacion"].astype(str)
        + " "
        + products_df["productos_unidad_medida_presentacion"].fillna("")
        + " | fechas: "
        + products_df["fechas_disponibles"].astype(str)
    )
    selected_option = st.selectbox("Producto", products_df["opcion"].tolist())
    product_row = products_df.loc[products_df["opcion"] == selected_option].iloc[0]

    evolution_df = run_query(
        con,
        """
        SELECT
            fecha_publicacion,
            cantidad_registros,
            precio_minimo,
            precio_maximo,
            precio_promedio,
            precio_referencia_promedio
        FROM mart_evolucion_productos
        WHERE id_producto = ?
            AND productos_descripcion IS NOT DISTINCT FROM ?
            AND productos_marca IS NOT DISTINCT FROM ?
            AND productos_cantidad_presentacion IS NOT DISTINCT FROM ?
            AND productos_unidad_medida_presentacion IS NOT DISTINCT FROM ?
        ORDER BY fecha_publicacion
        LIMIT 500
        """,
        [
            product_row["id_producto"],
            product_row["productos_descripcion"],
            product_row["productos_marca"],
            product_row["productos_cantidad_presentacion"],
            product_row["productos_unidad_medida_presentacion"],
        ],
    )

    first = evolution_df.iloc[0]
    last = evolution_df.iloc[-1]
    variation_abs = last["precio_promedio"] - first["precio_promedio"]
    variation_pct = (
        (variation_abs / first["precio_promedio"]) * 100
        if first["precio_promedio"]
        else None
    )

    cols = st.columns(6)
    first_date = pd.to_datetime(first["fecha_publicacion"]).strftime("%Y-%m-%d")
    last_date = pd.to_datetime(last["fecha_publicacion"]).strftime("%Y-%m-%d")
    cols[0].metric("Primera fecha", first_date)
    cols[1].metric("Última fecha", last_date)
    cols[2].metric("Promedio inicial", format_currency(first["precio_promedio"]))
    cols[3].metric("Promedio final", format_currency(last["precio_promedio"]))
    cols[4].metric("Variación absoluta", format_currency(variation_abs))
    cols[5].metric("Variación porcentual", format_percentage(variation_pct))

    st.markdown("#### Evolución por fecha")
    show_dataframe(evolution_df, height=280)

    if px is None:
        st.info("Plotly no está instalado en este entorno.")
        return
    chart_df = evolution_df.melt(
        id_vars=["fecha_publicacion"],
        value_vars=["precio_promedio", "precio_minimo", "precio_maximo"],
        var_name="metrica",
        value_name="precio",
    )
    fig = px.line(
        chart_df,
        x="fecha_publicacion",
        y="precio",
        color="metrica",
        markers=True,
        title="Precio del producto por fecha",
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font_color="#18212f",
        height=520,
        xaxis_title="Fecha",
        yaxis_title="Precio",
        margin=dict(l=20, r=20, t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_prices_by_location(con: duckdb.DuckDBPyConnection, selected_date: str) -> None:
    st.subheader("Precios por ubicación")
    province_options = run_query(
        con,
        """
        SELECT DISTINCT sucursales_provincia
        FROM mart_precios_por_ubicacion
        WHERE fecha_publicacion = ?
            AND sucursales_provincia IS NOT NULL
        ORDER BY sucursales_provincia
        """,
        [selected_date],
    )["sucursales_provincia"].tolist()

    selected_province = st.selectbox("Provincia", ["Todas"] + province_options)

    if selected_province == "Todas":
        locality_options: list[str] = []
    else:
        locality_options = run_query(
            con,
            """
            SELECT DISTINCT sucursales_localidad
            FROM mart_precios_por_ubicacion
            WHERE fecha_publicacion = ?
                AND sucursales_provincia = ?
                AND sucursales_localidad IS NOT NULL
            ORDER BY sucursales_localidad
            """,
            [selected_date, selected_province],
        )["sucursales_localidad"].tolist()

    selected_locality = st.selectbox("Localidad", ["Todas"] + locality_options)

    where_clauses = ["fecha_publicacion = ?"]
    params: list[object] = [selected_date]
    if selected_province != "Todas":
        where_clauses.append("sucursales_provincia = ?")
        params.append(selected_province)
    if selected_locality != "Todas":
        where_clauses.append("sucursales_localidad = ?")
        params.append(selected_locality)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    df = run_query(
        con,
        f"""
        SELECT
            sucursales_provincia,
            sucursales_localidad,
            cantidad_registros,
            cantidad_productos,
            cantidad_comercios,
            cantidad_sucursales,
            precio_promedio
        FROM mart_precios_por_ubicacion
        {where_sql}
        ORDER BY cantidad_productos DESC, sucursales_localidad
        LIMIT 200
        """,
        params,
    )
    show_dataframe(df)

    chart_df = df.sort_values("cantidad_productos", ascending=False).head(30)
    render_plotly_bar(
        chart_df,
        x="sucursales_localidad",
        y="cantidad_productos",
        title="Cantidad de productos por localidad",
    )


def render_promotions(con: duckdb.DuckDBPyConnection, selected_date: str) -> None:
    st.subheader("Promociones")
    columns = [
        "productos_descripcion",
        "productos_marca",
        "cantidad_registros_con_promo1",
        "cantidad_registros_con_promo2",
        "precio_promedio_lista",
        "precio_promedio_promo1",
        "precio_promedio_promo2",
    ]
    df = run_query(
        con,
        f"""
        SELECT {", ".join(columns)}
        FROM mart_promociones
        WHERE fecha_publicacion = ?
        ORDER BY
            (cantidad_registros_con_promo1 + cantidad_registros_con_promo2) DESC,
            productos_descripcion
        LIMIT 300
        """,
        [selected_date],
    )
    show_dataframe(df)


def render_price_dispersion(con: duckdb.DuckDBPyConnection, selected_date: str) -> None:
    st.subheader("Mayor dispersión")
    st.markdown(
        "Una alta dispersión puede deberse a productos mal comparados, distintas "
        "presentaciones, errores de carga o diferencias reales entre comercios."
    )
    limit = st.slider("Filas a mostrar", min_value=20, max_value=500, value=100, step=20)
    columns = [
        "productos_descripcion",
        "productos_marca",
        "cantidad_registros",
        "precio_minimo",
        "precio_maximo",
        "precio_promedio",
        "diferencia_absoluta_max_min",
        "diferencia_porcentual_max_min",
    ]
    df = run_query(
        con,
        f"""
        SELECT {", ".join(columns)}
        FROM mart_productos_mayor_dispersion
        WHERE fecha_publicacion = ?
        ORDER BY diferencia_absoluta_max_min DESC, cantidad_registros DESC
        LIMIT ?
        """,
        [selected_date, limit],
    )
    show_dataframe(df)


def render_georeferenced_stores(con: duckdb.DuckDBPyConnection, selected_date: str) -> None:
    st.subheader("Sucursales georreferenciadas")
    columns = [
        "comercio_bandera_nombre",
        "sucursales_nombre",
        "sucursales_localidad",
        "sucursales_provincia",
        "sucursales_latitud",
        "sucursales_longitud",
    ]
    df = run_query(
        con,
        f"""
        SELECT {", ".join(columns)}
        FROM mart_sucursales_geografia
        WHERE fecha_publicacion = ?
        ORDER BY sucursales_provincia, sucursales_localidad, comercio_bandera_nombre
        LIMIT 5000
        """,
        [selected_date],
    )
    show_dataframe(df)

    map_df = df.rename(
        columns={"sucursales_latitud": "lat", "sucursales_longitud": "lon"}
    )[["lat", "lon"]].dropna()
    if not map_df.empty:
        st.map(map_df)


def main() -> None:
    if not DB_PATH.exists():
        show_missing_database_message()
        return

    try:
        con = get_connection(str(DB_PATH))
    except duckdb.Error as exc:
        st.error(f"No se pudo abrir la base DuckDB en modo solo lectura: {exc}")
        return

    existing_marts = get_existing_marts(con)
    missing_marts = sorted(set(REQUIRED_MARTS) - existing_marts)
    if missing_marts:
        st.error("Faltan marts requeridos: " + ", ".join(missing_marts))
        st.markdown(
            "Ejecuta:"
            "\n\n```bash\n"
            "python -m src.analysis.create_dashboard_tables --db data/processed/precios_diarios.duckdb\n"
            "```"
        )
        return

    section, selected_date, comparison_start, comparison_end = render_sidebar(
        con,
        "Disponible",
    )

    if section == "Sobre el proyecto":
        render_about_project(con, selected_date)
        return

    st.title("Precios Diarios SEPA Argentina")
    st.caption(f"Sección: {section} | Fecha seleccionada: {selected_date}")
    st.divider()

    if section == "Resumen general":
        render_summary(con, selected_date)
    elif section == "Precios por comercio":
        render_prices_by_store(con, selected_date)
    elif section == "Buscador de productos":
        render_product_search(con, selected_date)
    elif section == "Precios por ubicación":
        render_prices_by_location(con, selected_date)
    elif section == "Promociones":
        render_promotions(con, selected_date)
    elif section == "Mayor dispersión":
        render_price_dispersion(con, selected_date)
    elif section == "Sucursales georreferenciadas":
        render_georeferenced_stores(con, selected_date)
    elif section == "Calidad de precios":
        render_price_quality(con, selected_date)
    elif section == "Buscador avanzado":
        render_advanced_product_search(con, selected_date)
    elif section == "Canasta básica exploratoria":
        render_basic_basket_candidates(con, selected_date)
    elif section == "Comparación entre fechas":
        render_date_comparison(con, comparison_start, comparison_end)
    elif section == "Evolución de producto":
        render_product_evolution(con)


if __name__ == "__main__":
    main()
