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
    "A. Resumen general",
    "B. Precios por comercio",
    "C. Buscador de productos",
    "D. Precios por ubicacion",
    "E. Promociones",
    "F. Productos con mayor dispersion",
    "G. Sucursales georreferenciadas",
    "H. Calidad de precios",
    "I. Buscador avanzado",
    "J. Canasta basica exploratoria",
)


st.set_page_config(page_title="Precios Diarios SEPA", layout="wide")


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


def format_number(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return f"{int(value):,}".replace(",", ".")


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


def render_sidebar(
    con: duckdb.DuckDBPyConnection,
    db_status: str,
) -> str:
    st.sidebar.header("Datos")
    st.sidebar.write(f"Estado de la base: **{db_status}**")
    st.sidebar.write(f"Fecha de publicacion: **{get_publication_date(con)}**")
    return st.sidebar.selectbox("Seccion", SECTION_OPTIONS)


def render_plotly_bar(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
) -> None:
    if px is None:
        st.info("Plotly no esta instalado en este entorno.")
        return
    if data.empty:
        return
    fig = px.bar(data, x=x, y=y, title=title)
    fig.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig, use_container_width=True)


def render_summary(con: duckdb.DuckDBPyConnection) -> None:
    st.subheader("Resumen general")
    df = run_query(con, "SELECT * FROM mart_resumen_general ORDER BY fecha_publicacion DESC")

    if df.empty:
        st.warning("El mart de resumen general no tiene filas.")
        return

    row = df.iloc[0]
    metrics = [
        ("Registros de precios", "cantidad_registros_precios"),
        ("Productos unicos", "cantidad_productos_unicos"),
        ("Comercios", "cantidad_comercios"),
        ("Banderas", "cantidad_banderas"),
        ("Sucursales", "cantidad_sucursales"),
        ("Provincias", "cantidad_provincias"),
        ("Localidades", "cantidad_localidades"),
    ]

    cols = st.columns(4)
    for index, (label, column) in enumerate(metrics):
        cols[index % 4].metric(label, format_number(row[column]))

    st.dataframe(df, use_container_width=True)


def render_prices_by_store(con: duckdb.DuckDBPyConnection) -> None:
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
        ORDER BY cantidad_productos DESC, comercio_bandera_nombre
        LIMIT 100
        """,
    )
    st.dataframe(df, use_container_width=True)
    render_plotly_bar(
        df,
        x="comercio_bandera_nombre",
        y="cantidad_productos",
        title="Cantidad de productos por comercio",
    )


def render_product_search(con: duckdb.DuckDBPyConnection) -> None:
    st.subheader("Buscador de productos")
    product_text = st.text_input("producto_buscado", value="COCA COLA")
    limit = st.slider("Limite de resultados", min_value=10, max_value=500, value=100, step=10)

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
        WHERE productos_descripcion ILIKE ?
        ORDER BY precio_minimo ASC NULLS LAST
        LIMIT ?
        """,
        [search_pattern, limit],
    )
    st.dataframe(df, use_container_width=True)


def render_price_quality(con: duckdb.DuckDBPyConnection) -> None:
    st.subheader("Calidad de precios")
    st.markdown(
        "Los precios sospechosos no se eliminan automaticamente; se marcan "
        "para analisis y pueden requerir revision."
    )

    df = run_query(
        con,
        """
        SELECT *
        FROM mart_calidad_precios
        ORDER BY fecha_publicacion DESC
        """,
    )
    if df.empty:
        st.warning("El mart de calidad de precios no tiene filas.")
        return

    row = df.iloc[0]
    metrics = [
        ("Precios cero", "cantidad_precio_cero"),
        ("Precios menores a 10", "cantidad_precio_menor_10"),
        ("Precio minimo", "precio_minimo"),
        ("Precio maximo", "precio_maximo"),
        ("Precio promedio", "precio_promedio"),
    ]
    cols = st.columns(len(metrics))
    for index, (label, column) in enumerate(metrics):
        cols[index].metric(label, format_number(row[column]))

    st.dataframe(df, use_container_width=True)

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
            LIMIT 1000
            """,
        )
        st.markdown("Registros marcados para revision")
        st.dataframe(suspicious_df, use_container_width=True)


def render_advanced_product_search(con: duckdb.DuckDBPyConnection) -> None:
    st.subheader("Buscador avanzado")
    st.markdown("Comparar productos requiere revisar presentacion y unidad de medida.")

    brand_options = run_query(
        con,
        """
        SELECT DISTINCT productos_marca
        FROM mart_productos_comparables
        WHERE productos_marca IS NOT NULL
            AND productos_marca <> ''
        ORDER BY productos_marca
        LIMIT 1000
        """,
    )["productos_marca"].tolist()
    unit_options = run_query(
        con,
        """
        SELECT DISTINCT productos_unidad_medida_presentacion
        FROM mart_productos_comparables
        WHERE productos_unidad_medida_presentacion IS NOT NULL
            AND productos_unidad_medida_presentacion <> ''
        ORDER BY productos_unidad_medida_presentacion
        """,
    )["productos_unidad_medida_presentacion"].tolist()

    col_a, col_b, col_c = st.columns(3)
    product_text = col_a.text_input("Texto de busqueda", value="LECHE")
    selected_brand = col_b.selectbox("Marca", ["Todas"] + brand_options)
    selected_unit = col_c.selectbox("Unidad de medida", ["Todas"] + unit_options)

    col_d, col_e, col_f = st.columns(3)
    max_price = col_d.number_input(
        "Precio maximo opcional",
        min_value=0.0,
        value=0.0,
        step=100.0,
        help="Usa 0 para no aplicar filtro.",
    )
    min_records = col_e.number_input(
        "Cantidad minima de registros",
        min_value=1,
        value=20,
        step=1,
    )
    limit = col_f.slider("Limite de resultados", min_value=10, max_value=1000, value=100, step=10)

    where_clauses = ["cantidad_registros >= ?"]
    params: list[object] = [int(min_records)]
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
    st.dataframe(df, use_container_width=True)


def render_basic_basket_candidates(con: duckdb.DuckDBPyConnection) -> None:
    st.subheader("Canasta basica exploratoria")
    st.markdown(
        "Esta canasta es exploratoria y se basa en busquedas por texto. No "
        "representa una canasta oficial ni garantiza equivalencia perfecta "
        "entre productos."
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
    selected_categories = st.multiselect(
        "Categorias de canasta",
        categories,
        default=categories,
    )
    limit_per_category = st.slider(
        "Candidatos por categoria",
        min_value=5,
        max_value=100,
        value=20,
        step=5,
    )

    if not selected_categories:
        st.info("Selecciona al menos una categoria.")
        return

    df = run_query(
        con,
        """
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
                    ORDER BY precio_minimo ASC NULLS LAST, cantidad_registros DESC
                ) AS orden_categoria
            FROM mart_canasta_basica_candidatos
            WHERE categoria_canasta = ANY(?)
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
        ORDER BY categoria_canasta, precio_minimo ASC NULLS LAST
        """,
        [selected_categories, int(limit_per_category)],
    )
    st.dataframe(df, use_container_width=True)


def render_prices_by_location(con: duckdb.DuckDBPyConnection) -> None:
    st.subheader("Precios por ubicacion")
    province_options = run_query(
        con,
        """
        SELECT DISTINCT sucursales_provincia
        FROM mart_precios_por_ubicacion
        WHERE sucursales_provincia IS NOT NULL
        ORDER BY sucursales_provincia
        """,
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
            WHERE sucursales_provincia = ?
                AND sucursales_localidad IS NOT NULL
            ORDER BY sucursales_localidad
            """,
            [selected_province],
        )["sucursales_localidad"].tolist()

    selected_locality = st.selectbox("Localidad", ["Todas"] + locality_options)

    where_clauses = []
    params: list[object] = []
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
    st.dataframe(df, use_container_width=True)

    chart_df = df.sort_values("cantidad_productos", ascending=False).head(30)
    render_plotly_bar(
        chart_df,
        x="sucursales_localidad",
        y="cantidad_productos",
        title="Cantidad de productos por localidad",
    )


def render_promotions(con: duckdb.DuckDBPyConnection) -> None:
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
        ORDER BY
            (cantidad_registros_con_promo1 + cantidad_registros_con_promo2) DESC,
            productos_descripcion
        LIMIT 300
        """,
    )
    st.dataframe(df, use_container_width=True)


def render_price_dispersion(con: duckdb.DuckDBPyConnection) -> None:
    st.subheader("Productos con mayor dispersion")
    st.markdown(
        "Una alta dispersion puede deberse a productos mal comparados, distintas "
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
        ORDER BY diferencia_absoluta_max_min DESC, cantidad_registros DESC
        LIMIT ?
        """,
        [limit],
    )
    st.dataframe(df, use_container_width=True)


def render_georeferenced_stores(con: duckdb.DuckDBPyConnection) -> None:
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
        ORDER BY sucursales_provincia, sucursales_localidad, comercio_bandera_nombre
        LIMIT 5000
        """,
    )
    st.dataframe(df, use_container_width=True)

    map_df = df.rename(
        columns={"sucursales_latitud": "lat", "sucursales_longitud": "lon"}
    )[["lat", "lon"]].dropna()
    if not map_df.empty:
        st.map(map_df)


def main() -> None:
    st.title("Dashboard local de precios SEPA")
    st.write(
        "Exploracion local de precios diarios de supermercados a partir de datos "
        "SEPA procesados con DuckDB."
    )

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

    section = render_sidebar(con, "Disponible")

    if section == "A. Resumen general":
        render_summary(con)
    elif section == "B. Precios por comercio":
        render_prices_by_store(con)
    elif section == "C. Buscador de productos":
        render_product_search(con)
    elif section == "D. Precios por ubicacion":
        render_prices_by_location(con)
    elif section == "E. Promociones":
        render_promotions(con)
    elif section == "F. Productos con mayor dispersion":
        render_price_dispersion(con)
    elif section == "G. Sucursales georreferenciadas":
        render_georeferenced_stores(con)
    elif section == "H. Calidad de precios":
        render_price_quality(con)
    elif section == "I. Buscador avanzado":
        render_advanced_product_search(con)
    elif section == "J. Canasta basica exploratoria":
        render_basic_basket_candidates(con)


if __name__ == "__main__":
    main()
