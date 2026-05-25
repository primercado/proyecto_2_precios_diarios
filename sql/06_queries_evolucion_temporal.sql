-- Consultas de evolucion temporal para dashboard Streamlit.
-- Motor objetivo: DuckDB.
--
-- Advertencia de comparabilidad:
-- Las comparaciones agrupan productos por ID, descripcion, marca,
-- presentacion y unidad. Aun asi, pueden existir inconsistencias de carga o
-- productos no estrictamente equivalentes entre fechas.


-- 1. Evolucion de un producto por fecha.
-- Cambiar el texto de busqueda por el producto a analizar.
SELECT
    fecha_publicacion,
    id_producto,
    productos_descripcion,
    productos_marca,
    productos_cantidad_presentacion,
    productos_unidad_medida_presentacion,
    cantidad_registros,
    precio_minimo,
    precio_maximo,
    precio_promedio,
    precio_referencia_promedio
FROM mart_evolucion_productos
WHERE productos_descripcion ILIKE '%LECHE%'
ORDER BY fecha_publicacion, cantidad_registros DESC
LIMIT 200;


-- 2. Ranking de productos con mayor aumento porcentual.
-- Usa la variacion contra la fecha anterior disponible para cada producto.
SELECT
    fecha_publicacion,
    fecha_anterior,
    productos_descripcion,
    productos_marca,
    productos_cantidad_presentacion,
    productos_unidad_medida_presentacion,
    precio_promedio_anterior,
    precio_promedio_actual,
    variacion_absoluta,
    variacion_porcentual,
    cantidad_registros_anterior,
    cantidad_registros_actual
FROM mart_variacion_productos
WHERE fecha_publicacion = DATE '2026-05-24'
    AND cantidad_registros_anterior >= 20
    AND cantidad_registros_actual >= 20
    AND variacion_porcentual IS NOT NULL
    AND variacion_absoluta > 0
ORDER BY variacion_porcentual DESC, cantidad_registros_actual DESC
LIMIT 50;


-- 3. Ranking de productos con mayor baja porcentual.
SELECT
    fecha_publicacion,
    fecha_anterior,
    productos_descripcion,
    productos_marca,
    productos_cantidad_presentacion,
    productos_unidad_medida_presentacion,
    precio_promedio_anterior,
    precio_promedio_actual,
    variacion_absoluta,
    variacion_porcentual,
    cantidad_registros_anterior,
    cantidad_registros_actual
FROM mart_variacion_productos
WHERE fecha_publicacion = DATE '2026-05-24'
    AND cantidad_registros_anterior >= 20
    AND cantidad_registros_actual >= 20
    AND variacion_porcentual IS NOT NULL
    AND variacion_absoluta < 0
ORDER BY variacion_porcentual ASC, cantidad_registros_actual DESC
LIMIT 50;


-- 4. Comparacion general entre dos fechas.
-- Resume volumen, productos unicos y precio promedio general.
WITH fechas AS (
    SELECT
        fecha_publicacion,
        cantidad_registros_precios,
        cantidad_productos_unicos,
        precio_promedio_general
    FROM mart_resumen_general
    WHERE fecha_publicacion IN (DATE '2026-05-23', DATE '2026-05-24')
)
SELECT
    inicial.fecha_publicacion AS fecha_inicial,
    final.fecha_publicacion AS fecha_final,
    inicial.cantidad_registros_precios AS registros_iniciales,
    final.cantidad_registros_precios AS registros_finales,
    final.cantidad_registros_precios - inicial.cantidad_registros_precios AS diferencia_registros,
    inicial.cantidad_productos_unicos AS productos_iniciales,
    final.cantidad_productos_unicos AS productos_finales,
    final.cantidad_productos_unicos - inicial.cantidad_productos_unicos AS diferencia_productos,
    inicial.precio_promedio_general AS precio_promedio_inicial,
    final.precio_promedio_general AS precio_promedio_final,
    CASE
        WHEN inicial.precio_promedio_general > 0
            THEN ((final.precio_promedio_general - inicial.precio_promedio_general)
                / inicial.precio_promedio_general) * 100
        ELSE NULL
    END AS variacion_porcentual_precio_promedio
FROM fechas AS inicial
CROSS JOIN fechas AS final
WHERE inicial.fecha_publicacion = DATE '2026-05-23'
    AND final.fecha_publicacion = DATE '2026-05-24';


-- 5. Productos con datos suficientes para comparar.
-- Ajustar el umbral de registros minimos segun el caso de uso.
SELECT
    fecha_publicacion,
    fecha_anterior,
    productos_descripcion,
    productos_marca,
    productos_cantidad_presentacion,
    productos_unidad_medida_presentacion,
    cantidad_registros_anterior,
    cantidad_registros_actual,
    precio_promedio_anterior,
    precio_promedio_actual,
    variacion_porcentual
FROM mart_variacion_productos
WHERE cantidad_registros_anterior >= 20
    AND cantidad_registros_actual >= 20
ORDER BY fecha_publicacion DESC, cantidad_registros_actual DESC
LIMIT 200;


-- 6. Comparacion entre dos fechas para productos equivalentes.
-- Esta consulta exige misma descripcion, marca, presentacion y unidad porque
-- usa mart_variacion_productos, construido con esas claves de comparabilidad.
SELECT
    productos_descripcion,
    productos_marca,
    productos_cantidad_presentacion,
    productos_unidad_medida_presentacion,
    precio_promedio_anterior,
    precio_promedio_actual,
    variacion_absoluta,
    variacion_porcentual
FROM mart_variacion_productos
WHERE fecha_anterior = DATE '2026-05-23'
    AND fecha_publicacion = DATE '2026-05-24'
    AND cantidad_registros_anterior >= 20
    AND cantidad_registros_actual >= 20
ORDER BY ABS(variacion_porcentual) DESC
LIMIT 100;
