-- Consultas de calidad de precios para DuckDB.
-- Son consultas exploratorias: no modifican datos crudos.

-- 1. Productos con precios sospechosamente bajos.
SELECT
    fecha_publicacion,
    id_producto,
    productos_descripcion,
    productos_marca,
    productos_cantidad_presentacion,
    productos_unidad_medida_presentacion,
    productos_precio_lista,
    productos_precio_referencia
FROM fact_precios
WHERE productos_precio_lista <= 0
LIMIT 1000;

SELECT
    fecha_publicacion,
    id_producto,
    productos_descripcion,
    productos_marca,
    productos_cantidad_presentacion,
    productos_unidad_medida_presentacion,
    productos_precio_lista,
    productos_precio_referencia
FROM fact_precios
WHERE productos_precio_lista > 0
    AND productos_precio_lista < 10
LIMIT 1000;

-- 2. Productos con precios muy altos.
-- Top acotado por precio maximo observado por producto. El agregado reduce el
-- volumen antes de ordenar.
WITH precios_por_producto AS (
    SELECT
        fecha_publicacion,
        id_producto,
        ANY_VALUE(productos_descripcion) AS productos_descripcion,
        ANY_VALUE(productos_marca) AS productos_marca,
        MAX(productos_precio_lista) AS precio_maximo,
        COUNT(*) AS cantidad_registros
    FROM fact_precios
    WHERE productos_precio_lista IS NOT NULL
    GROUP BY fecha_publicacion, id_producto
)
SELECT *
FROM precios_por_producto
ORDER BY precio_maximo DESC NULLS LAST
LIMIT 100;

-- Percentiles aproximados generales por fecha. approx_quantile evita ordenar la
-- tabla completa como haria un percentil exacto.
SELECT
    fecha_publicacion,
    approx_quantile(productos_precio_lista, 0.95) AS precio_p95_aproximado,
    approx_quantile(productos_precio_lista, 0.99) AS precio_p99_aproximado,
    MAX(productos_precio_lista) AS precio_maximo
FROM fact_precios
WHERE productos_precio_lista IS NOT NULL
GROUP BY fecha_publicacion;

-- 3. Resumen por unidad de presentacion.
SELECT
    productos_unidad_medida_presentacion,
    COUNT(DISTINCT id_producto) AS cantidad_productos,
    AVG(productos_precio_lista) AS precio_promedio,
    MIN(productos_precio_lista) AS precio_minimo,
    MAX(productos_precio_lista) AS precio_maximo
FROM fact_precios
WHERE productos_precio_lista IS NOT NULL
GROUP BY productos_unidad_medida_presentacion;

-- 4. Productos comparables por presentacion.
SELECT
    fecha_publicacion,
    id_producto,
    productos_descripcion,
    productos_marca,
    productos_cantidad_presentacion,
    productos_unidad_medida_presentacion,
    COUNT(*) AS cantidad_registros,
    MIN(productos_precio_lista) AS precio_minimo,
    MAX(productos_precio_lista) AS precio_maximo,
    AVG(productos_precio_lista) AS precio_promedio,
    AVG(productos_precio_referencia) AS precio_referencia_promedio
FROM fact_precios
WHERE productos_precio_lista IS NOT NULL
GROUP BY
    fecha_publicacion,
    id_producto,
    productos_descripcion,
    productos_marca,
    productos_cantidad_presentacion,
    productos_unidad_medida_presentacion;

-- 5. Consulta base para buscador avanzado.
-- Parametros esperados:
--   ? texto buscado, por ejemplo '%LECHE%'
--   ? marca opcional; pasar NULL para no filtrar
--   ? unidad opcional; pasar NULL para no filtrar
--   ? provincia opcional; pasar NULL para no filtrar
--   ? localidad opcional; pasar NULL para no filtrar
--   ? limite de resultados
WITH productos_filtrados AS (
    SELECT
        f.fecha_publicacion,
        f.id_producto,
        f.productos_descripcion,
        f.productos_marca,
        f.productos_cantidad_presentacion,
        f.productos_unidad_medida_presentacion,
        COUNT(*) AS cantidad_registros,
        MIN(f.productos_precio_lista) AS precio_minimo,
        MAX(f.productos_precio_lista) AS precio_maximo,
        AVG(f.productos_precio_lista) AS precio_promedio,
        AVG(f.productos_precio_referencia) AS precio_referencia_promedio
    FROM fact_precios AS f
    LEFT JOIN dim_sucursales AS s
        ON f.fecha_publicacion = s.fecha_publicacion
        AND f.id_comercio = s.id_comercio
        AND f.id_bandera = s.id_bandera
        AND f.id_sucursal = s.id_sucursal
    WHERE f.productos_precio_lista IS NOT NULL
        AND f.productos_descripcion ILIKE ?
        AND (? IS NULL OR f.productos_marca = ?)
        AND (? IS NULL OR f.productos_unidad_medida_presentacion = ?)
        AND (? IS NULL OR s.sucursales_provincia = ?)
        AND (? IS NULL OR s.sucursales_localidad = ?)
    GROUP BY
        f.fecha_publicacion,
        f.id_producto,
        f.productos_descripcion,
        f.productos_marca,
        f.productos_cantidad_presentacion,
        f.productos_unidad_medida_presentacion
)
SELECT *
FROM productos_filtrados
ORDER BY precio_minimo ASC NULLS LAST, precio_promedio ASC NULLS LAST
LIMIT ?;

-- 6. Consulta para canasta exploratoria.
-- Aproximada: se basa en texto y debe revisarse manualmente antes de usarla
-- como referencia analitica.
WITH candidatos AS (
    SELECT
        fecha_publicacion,
        CASE
            WHEN productos_descripcion ILIKE '%LECHE%' THEN 'LECHE'
            WHEN productos_descripcion ILIKE '%ARROZ%' THEN 'ARROZ'
            WHEN productos_descripcion ILIKE '%FIDEO%' THEN 'FIDEO'
            WHEN productos_descripcion ILIKE '%YERBA%' THEN 'YERBA'
            WHEN productos_descripcion ILIKE '%ACEITE%' THEN 'ACEITE'
            WHEN productos_descripcion ILIKE '%AZUCAR%' THEN 'AZUCAR'
            WHEN productos_descripcion ILIKE '%HARINA%' THEN 'HARINA'
            WHEN productos_descripcion ILIKE '%HUEVO%' THEN 'HUEVO'
            ELSE NULL
        END AS categoria_canasta,
        id_producto,
        productos_descripcion,
        productos_marca,
        productos_cantidad_presentacion,
        productos_unidad_medida_presentacion,
        productos_precio_lista,
        productos_precio_referencia
    FROM fact_precios
    WHERE productos_precio_lista IS NOT NULL
)
SELECT
    fecha_publicacion,
    categoria_canasta,
    id_producto,
    productos_descripcion,
    productos_marca,
    productos_cantidad_presentacion,
    productos_unidad_medida_presentacion,
    COUNT(*) AS cantidad_registros,
    MIN(productos_precio_lista) AS precio_minimo,
    MAX(productos_precio_lista) AS precio_maximo,
    AVG(productos_precio_lista) AS precio_promedio,
    AVG(productos_precio_referencia) AS precio_referencia_promedio
FROM candidatos
WHERE categoria_canasta IS NOT NULL
GROUP BY
    fecha_publicacion,
    categoria_canasta,
    id_producto,
    productos_descripcion,
    productos_marca,
    productos_cantidad_presentacion,
    productos_unidad_medida_presentacion;
