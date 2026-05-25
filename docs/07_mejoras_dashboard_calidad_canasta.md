# Mejoras del dashboard: calidad y canasta exploratoria

## Nuevas secciones

### Calidad de precios

Resume precios nulos, precios cero, precios positivos menores a 10 y valores
minimos, maximos y promedio. El objetivo es mostrar posibles problemas antes de
interpretar dispersiones o rankings.

La seccion tambien muestra registros marcados como sospechosos cuando existe
`mart_precios_sospechosos`.

### Buscador avanzado

Permite buscar productos comparables desde `mart_productos_comparables`, con
filtros por texto, marca, unidad de medida, precio maximo, cantidad minima de
registros y limite de resultados.

El problema que resuelve es evitar comparaciones amplias por nombre. Antes de
comparar precios conviene revisar presentacion, unidad y cantidad de registros.

### Canasta basica exploratoria

Muestra candidatos para categorias frecuentes:

- LECHE
- ARROZ
- FIDEO
- YERBA
- ACEITE
- AZUCAR
- HARINA
- HUEVO

Los candidatos se generan por busquedas de texto y se ordenan por precio minimo
dentro de cada categoria.

## Por que agregar reglas de calidad

Los datos pueden contener precios en cero, importes muy bajos, valores muy altos,
productos mal descriptos o promociones incompletas. Si el dashboard oculta estos
problemas, una persona puede interpretar como oportunidad de ahorro lo que en
realidad es un error de carga o una comparacion entre presentaciones distintas.

Las reglas actuales no eliminan datos crudos. Solo crean marts analiticos para
marcar casos que requieren revision.

## Como usar el buscador avanzado

1. Buscar un texto especifico, por ejemplo `LECHE`.
2. Filtrar por marca si se quiere comparar dentro de una misma marca.
3. Filtrar por unidad de medida para no mezclar litros, kilos, gramos o unidades.
4. Subir la cantidad minima de registros cuando se quiera una comparacion mas
   estable.
5. Revisar presentacion y precio de referencia antes de sacar conclusiones.

## Limites de la canasta exploratoria

La canasta no es oficial. No usa definiciones normativas ni garantiza equivalencia
perfecta entre productos. Una busqueda por `ACEITE`, por ejemplo, puede mezclar
tipos, tamanos o calidades distintas.

Debe leerse como una ayuda para encontrar candidatos y no como un indice de costo
de vida.

## Proximos pasos

- Incorporar varios dias de datos para detectar outliers por producto y fecha.
- Agregar reglas por categoria y unidad de medida.
- Mejorar normalizacion de marcas y presentaciones.
- Definir manualmente productos canonicos para una canasta propia.
- Evaluar comparaciones por precio de referencia cuando el dato sea consistente.
