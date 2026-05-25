-- Consultas analiticas para dashboard ciudadano de precios diarios.
-- Motor objetivo: DuckDB.
--
-- Estas consultas resumen la capa base cargada por src/load/load_duckdb.py:
--   - dim_comercios
--   - dim_sucursales
--   - fact_precios
--
-- La intencion es validar preguntas de negocio y servir como referencia para
-- los marts creados por src/analysis/create_dashboard_tables.py.


-- A. Resumen general del dataset
-- Mide volumen, cobertura geografica y cardinalidades principales por fecha.
SELECT
    f.fecha_publicacion,
    COUNT(*) AS cantidad_registros_precios,
    COUNT(DISTINCT f.id_producto) AS cantidad_productos_unicos,
    COUNT(DISTINCT f.id_comercio) AS cantidad_comercios,
    COUNT(DISTINCT f.id_comercio || '-' || f.id_bandera) AS cantidad_banderas,
    COUNT(DISTINCT f.id_comercio || '-' || f.id_bandera || '-' || f.id_sucursal) AS cantidad_sucursales,
    COUNT(DISTINCT s.sucursales_provincia) AS cantidad_provincias,
    COUNT(DISTINCT s.sucursales_localidad) AS cantidad_localidades
FROM fact_precios AS f
LEFT JOIN dim_sucursales AS s
    ON f.fecha_publicacion = s.fecha_publicacion
    AND f.id_comercio = s.id_comercio
    AND f.id_bandera = s.id_bandera
    AND f.id_sucursal = s.id_sucursal
GROUP BY f.fecha_publicacion
ORDER BY f.fecha_publicacion;


-- B. Resumen por producto
-- Resume disponibilidad, cobertura comercial y estadisticos de precio.
SELECT
    f.fecha_publicacion,
    f.id_producto,
    ANY_VALUE(f.productos_descripcion) AS productos_descripcion,
    ANY_VALUE(f.productos_marca) AS productos_marca,
    COUNT(*) AS cantidad_registros,
    COUNT(DISTINCT f.id_comercio) AS cantidad_comercios,
    COUNT(DISTINCT f.id_comercio || '-' || f.id_bandera || '-' || f.id_sucursal) AS cantidad_sucursales,
    MIN(f.productos_precio_lista) AS precio_minimo,
    MAX(f.productos_precio_lista) AS precio_maximo,
    AVG(f.productos_precio_lista) AS precio_promedio,
    approx_quantile(f.productos_precio_lista, 0.5) AS precio_mediano_aproximado,
    MAX(f.productos_precio_lista) - MIN(f.productos_precio_lista) AS diferencia_absoluta_max_min,
    CASE
        WHEN MIN(f.productos_precio_lista) > 0
            THEN ((MAX(f.productos_precio_lista) - MIN(f.productos_precio_lista)) / MIN(f.productos_precio_lista)) * 100
        ELSE NULL
    END AS diferencia_porcentual_max_min
FROM fact_precios AS f
WHERE f.productos_precio_lista IS NOT NULL
GROUP BY f.fecha_publicacion, f.id_producto
ORDER BY f.fecha_publicacion, cantidad_registros DESC;


-- C. Precios por comercio
-- Resume actividad y rango de precios por comercio/bandera.
SELECT
    f.fecha_publicacion,
    f.id_comercio,
    f.id_bandera,
    ANY_VALUE(c.comercio_bandera_nombre) AS comercio_bandera_nombre,
    COUNT(*) AS cantidad_registros,
    COUNT(DISTINCT f.id_producto) AS cantidad_productos,
    COUNT(DISTINCT f.id_comercio || '-' || f.id_bandera || '-' || f.id_sucursal) AS cantidad_sucursales,
    AVG(f.productos_precio_lista) AS precio_promedio,
    MIN(f.productos_precio_lista) AS precio_minimo,
    MAX(f.productos_precio_lista) AS precio_maximo
FROM fact_precios AS f
LEFT JOIN dim_comercios AS c
    ON f.fecha_publicacion = c.fecha_publicacion
    AND f.id_comercio = c.id_comercio
    AND f.id_bandera = c.id_bandera
WHERE f.productos_precio_lista IS NOT NULL
GROUP BY f.fecha_publicacion, f.id_comercio, f.id_bandera
ORDER BY f.fecha_publicacion, cantidad_registros DESC;


-- D. Precios por provincia y localidad
-- Resume cobertura y precio promedio por ubicacion.
SELECT
    f.fecha_publicacion,
    s.sucursales_provincia,
    s.sucursales_localidad,
    COUNT(*) AS cantidad_registros,
    COUNT(DISTINCT f.id_producto) AS cantidad_productos,
    COUNT(DISTINCT f.id_comercio) AS cantidad_comercios,
    COUNT(DISTINCT f.id_comercio || '-' || f.id_bandera || '-' || f.id_sucursal) AS cantidad_sucursales,
    AVG(f.productos_precio_lista) AS precio_promedio
FROM fact_precios AS f
LEFT JOIN dim_sucursales AS s
    ON f.fecha_publicacion = s.fecha_publicacion
    AND f.id_comercio = s.id_comercio
    AND f.id_bandera = s.id_bandera
    AND f.id_sucursal = s.id_sucursal
WHERE f.productos_precio_lista IS NOT NULL
GROUP BY f.fecha_publicacion, s.sucursales_provincia, s.sucursales_localidad
ORDER BY f.fecha_publicacion, s.sucursales_provincia, s.sucursales_localidad;


-- E. Productos con promocion
-- Identifica productos con precios promocionales y ejemplos de leyendas.
SELECT
    f.fecha_publicacion,
    f.id_producto,
    ANY_VALUE(f.productos_descripcion) AS productos_descripcion,
    ANY_VALUE(f.productos_marca) AS productos_marca,
    COUNT(*) FILTER (WHERE f.productos_precio_unitario_promo1 IS NOT NULL) AS cantidad_registros_con_promo1,
    COUNT(*) FILTER (WHERE f.productos_precio_unitario_promo2 IS NOT NULL) AS cantidad_registros_con_promo2,
    string_agg(DISTINCT NULLIF(f.productos_leyenda_promo1, ''), ' | ') AS ejemplos_leyendas_promo1,
    string_agg(DISTINCT NULLIF(f.productos_leyenda_promo2, ''), ' | ') AS ejemplos_leyendas_promo2,
    AVG(f.productos_precio_lista) AS precio_promedio_lista,
    AVG(f.productos_precio_unitario_promo1) AS precio_promedio_promo1,
    AVG(f.productos_precio_unitario_promo2) AS precio_promedio_promo2
FROM fact_precios AS f
WHERE f.productos_precio_unitario_promo1 IS NOT NULL
    OR f.productos_precio_unitario_promo2 IS NOT NULL
    OR NULLIF(f.productos_leyenda_promo1, '') IS NOT NULL
    OR NULLIF(f.productos_leyenda_promo2, '') IS NOT NULL
GROUP BY f.fecha_publicacion, f.id_producto
ORDER BY f.fecha_publicacion, cantidad_registros_con_promo1 DESC, cantidad_registros_con_promo2 DESC;


-- F. Productos con mayor dispersion de precios
-- Filtra productos con al menos 20 registros para evitar casos poco representativos.
SELECT
    f.fecha_publicacion,
    f.id_producto,
    ANY_VALUE(f.productos_descripcion) AS productos_descripcion,
    ANY_VALUE(f.productos_marca) AS productos_marca,
    COUNT(*) AS cantidad_registros,
    COUNT(DISTINCT f.id_comercio) AS cantidad_comercios,
    COUNT(DISTINCT f.id_comercio || '-' || f.id_bandera || '-' || f.id_sucursal) AS cantidad_sucursales,
    MIN(f.productos_precio_lista) AS precio_minimo,
    MAX(f.productos_precio_lista) AS precio_maximo,
    AVG(f.productos_precio_lista) AS precio_promedio,
    MAX(f.productos_precio_lista) - MIN(f.productos_precio_lista) AS diferencia_absoluta_max_min,
    CASE
        WHEN MIN(f.productos_precio_lista) > 0
            THEN ((MAX(f.productos_precio_lista) - MIN(f.productos_precio_lista)) / MIN(f.productos_precio_lista)) * 100
        ELSE NULL
    END AS diferencia_porcentual_max_min
FROM fact_precios AS f
WHERE f.productos_precio_lista IS NOT NULL
GROUP BY f.fecha_publicacion, f.id_producto
HAVING COUNT(*) >= 20
ORDER BY diferencia_absoluta_max_min DESC, cantidad_registros DESC;


-- G. Buscador de producto
-- Ejemplo de busqueda por texto. Cambiar 'COCA COLA' por el termino deseado.
SELECT
    f.fecha_publicacion,
    f.id_producto,
    f.productos_descripcion,
    f.productos_marca,
    f.id_comercio,
    f.id_bandera,
    c.comercio_bandera_nombre,
    f.id_sucursal,
    s.sucursales_nombre,
    s.sucursales_localidad,
    s.sucursales_provincia,
    f.productos_precio_lista,
    f.productos_precio_unitario_promo1,
    f.productos_leyenda_promo1,
    f.productos_precio_unitario_promo2,
    f.productos_leyenda_promo2
FROM fact_precios AS f
LEFT JOIN dim_comercios AS c
    ON f.fecha_publicacion = c.fecha_publicacion
    AND f.id_comercio = c.id_comercio
    AND f.id_bandera = c.id_bandera
LEFT JOIN dim_sucursales AS s
    ON f.fecha_publicacion = s.fecha_publicacion
    AND f.id_comercio = s.id_comercio
    AND f.id_bandera = s.id_bandera
    AND f.id_sucursal = s.id_sucursal
WHERE upper(f.productos_descripcion) LIKE '%COCA COLA%'
ORDER BY f.productos_precio_lista ASC NULLS LAST;


-- H. Sucursales georreferenciadas
-- Base para mapas en Power BI.
SELECT
    s.fecha_publicacion,
    s.id_comercio,
    s.id_bandera,
    c.comercio_bandera_nombre,
    s.id_sucursal,
    s.sucursales_nombre,
    s.sucursales_tipo,
    s.sucursales_calle,
    s.sucursales_numero,
    s.sucursales_localidad,
    s.sucursales_provincia,
    s.sucursales_latitud,
    s.sucursales_longitud
FROM dim_sucursales AS s
LEFT JOIN dim_comercios AS c
    ON s.fecha_publicacion = c.fecha_publicacion
    AND s.id_comercio = c.id_comercio
    AND s.id_bandera = c.id_bandera
WHERE s.sucursales_latitud IS NOT NULL
    AND s.sucursales_longitud IS NOT NULL
ORDER BY s.fecha_publicacion, s.sucursales_provincia, s.sucursales_localidad, comercio_bandera_nombre;
