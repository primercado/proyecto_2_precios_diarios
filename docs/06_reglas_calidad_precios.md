# Reglas de calidad para precios

## Por que no alcanza con comparar por nombre

Los nombres de productos en SEPA son textos cargados por distintas fuentes. Dos
productos pueden tener nombres parecidos y no ser equivalentes, o el mismo
producto puede aparecer con variantes de descripcion. Por eso comparar solo por
`productos_descripcion` puede producir conclusiones enganosas.

Un ejemplo claro es `COCA COLA 600 ML` frente a `COCA COLA 2.25 L`. Aunque ambas
descripciones mencionen la misma marca y bebida, la presentacion es distinta. El
precio de lista no representa lo mismo y una comparacion directa mostraria una
diferencia esperable como si fuera dispersion de precios.

Para comparar mejor hay que mirar:

- `productos_cantidad_presentacion`
- `productos_unidad_medida_presentacion`
- `productos_precio_referencia`
- `productos_cantidad_referencia`
- `productos_unidad_medida_referencia`

El precio de referencia permite comparar por litro, kilo o unidad cuando el dato
esta disponible y es consistente. Aun asi, debe revisarse porque tambien puede
tener errores o ausencias.

## Problemas frecuentes

- Precios iguales a 0 o cercanos a 0.
- Precios extremadamente altos.
- Productos mal cargados o con descripcion incompleta.
- Diferencias de presentacion dentro de un mismo nombre comercial.
- Productos con nombres parecidos pero no equivalentes.
- Promociones incompletas o leyendas de promocion sin precio asociado.

## Reglas iniciales sugeridas

- Excluir o marcar precios menores o iguales a 0.
- Marcar precios positivos menores a 10 para revision.
- Marcar precios extremadamente altos para revision manual.
- Comparar productos solo dentro de la misma unidad de presentacion.
- Usar `productos_precio_referencia` cuando se compare por litro, kilo o unidad.
- Exigir una cantidad minima de registros antes de mostrar dispersion.
- Mostrar advertencias en el dashboard cuando una comparacion sea exploratoria.

## Alcance

Estas reglas son una primera version prudente. Sirven para mejorar la lectura del
dashboard y evitar comparaciones obvias mal planteadas, pero no reemplazan una
validacion estadistica completa.

Las reglas deben revisarse cuando existan varios dias de datos. Con mas historial
se pueden detectar valores atipicos por producto, comercio, provincia y fecha,
en lugar de depender solo de umbrales generales.
