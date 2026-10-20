# Demostración con un CSV proporcionado por el profesor

Mi objetivo es leer el archivo recibido, ejecutar P0, P1 y P2 con los mismos parámetros y comprobar la clasificación de sus puntos. El número de filas no está fijado en C++: el programa lo obtiene al leer el CSV.

Trabajo desde `~/Documents/DBSCAN_Proyecto`

## 1. Recibo el archivo y confirmo los parámetros

Copio el archivo a `data/` con un nombre distinto de los datasets generados, por ejemplo `datos_profesor.csv`. Conservo intacto el archivo original.

El formato que acepta mi lector es:

```text
0.415,0.446
0.470,0.007
0.784,0.500
```

- Dos columnas numéricas: `x,y`, separadas por coma.
- Sin encabezado, columnas de índice, etiquetas ni líneas vacías.
- Decimales con punto; también puedo recibir valores negativos.
- Valores finitos: sin `NaN` ni infinito.
- Al menos un punto; no es obligatorio tener 4000 ni 200000 filas.

Pregunto qué **epsilon** y **min_samples** debo utilizar. Si no los especifica, propongo `0.03` y `10`, explicando que son los de mi evaluación original. Epsilon depende de la escala de las coordenadas: no supongo que 0.03 sea adecuado para cualquier conjunto.

Si el archivo tiene encabezado, separadores diferentes o columnas adicionales, primero aclaro el formato y las columnas que representan las coordenadas. Si necesito adaptarlo, guardo una copia distinta. No elimino puntos, redondeo, normalizo ni aplico valor absoluto automáticamente: esas transformaciones modificarían el problema recibido.

## 2. Preparo las rutas y compilo

```sh
cd ~/Documents/DBSCAN_Proyecto
make all

INPUT="data/datos_profesor.csv"
EPS="0.03"
MIN_SAMPLES="10"
THREADS="5"
PARTITIONS="16"
OUT="results/datos_profesor/$(date +%Y%m%d_%H%M%S)"

mkdir -p "$OUT"
ls -lh "$INPUT"
head -n 5 "$INPUT"
```

Sustituyo el nombre en `INPUT` por el archivo real y ajusto `EPS` y `MIN_SAMPLES` a lo acordado. Las comillas permiten nombres con espacios. Mantengo esta pestaña de Terminal abierta: las variables definidas aquí se usan en los siguientes pasos.

`OUT` separa las salidas de esta demostración mediante una fecha y hora. Nunca utilizo la ruta de entrada como salida.

**Lo que explico:** «Mi programa lee el número de puntos del archivo. Uso exactamente las mismas coordenadas y parámetros en las tres versiones; lo que cambia es la distribución del trabajo».

## 3. Reviso el CSV antes de ejecutar

Este bloque sólo lee el archivo; no lo transforma:

```sh
.venv/bin/python - "$INPUT" <<'PY'
import csv
import math
import sys

cantidad = 0
with open(sys.argv[1], encoding="utf-8", newline="") as archivo:
    for numero, fila in enumerate(csv.reader(archivo), start=1):
        if len(fila) != 2:
            raise SystemExit(f"Fila {numero}: necesito exactamente dos columnas x,y.")
        try:
            x, y = map(float, fila)
        except ValueError:
            raise SystemExit(f"Fila {numero}: hay un encabezado o un valor no numérico.")
        if not (math.isfinite(x) and math.isfinite(y)):
            raise SystemExit(f"Fila {numero}: hay NaN o infinito.")
        cantidad += 1
if cantidad == 0:
    raise SystemExit("El archivo está vacío.")
print(f"Revisión numérica correcta: {cantidad} puntos, dos coordenadas por punto.")
PY
```

`sys.argv[1]` recibe `INPUT`; `csv.reader` separa las columnas y `enumerate` permite informar la fila problemática. Esta revisión numérica ayuda a detectar errores comunes. El lector C++ realiza además su propia validación del formato: por ejemplo, no admite campos entrecomillados ni una marca BOM al inicio, aunque algunas herramientas CSV los toleren.

Si la revisión falla, corrijo el formato en una copia acordada con el profesor antes de continuar. No interpreto un error de lectura como un fallo de DBSCAN.

## 4. Ejecuto las tres versiones sobre el archivo recibido

```sh
bin/serial "$INPUT" "$OUT/serial.csv" "$EPS" "$MIN_SAMPLES"
bin/paralelo1 "$INPUT" "$OUT/paralelo1.csv" "$EPS" "$MIN_SAMPLES" "$THREADS"
bin/paralelo2 "$INPUT" "$OUT/paralelo2.csv" "$EPS" "$MIN_SAMPLES" "$THREADS" "$PARTITIONS"
```

Espero que cada comando termine sin errores e imprima un JSON con:

| Campo | Qué compruebo |
| --- | --- |
| `n` | Coincide con la cantidad de puntos del archivo recibido. |
| `threads` | P0 usa 1; P1/P2 reportan los hilos solicitados. |
| `k` | En P2 coincide con las particiones solicitadas. |
| `core`, `border`, `noise` | Suman N y coinciden entre versiones. |
| `seconds` | Tiempo de cómputo de esa ejecución, en segundos. |

No espero los conteos del conjunto original de 4000 puntos: los datos del profesor pueden producir otros resultados. Que todos sean ruido o todos sean core no demuestra por sí solo un error; depende de las distancias y parámetros.

**Lo que explico:** «Incluyo al propio punto en min_samples. Si alcanza el umbral de vecinos dentro de epsilon, es core. Si no es core pero tiene un core vecino, es borde. De lo contrario es ruido».

En datos nuevos no prometo el mismo tiempo de ejecución que en los datos densos de mi informe. La búsqueda mantiene un peor caso O(N²); la parada temprana puede ayudar menos en conjuntos diferentes.

## 5. Comparo todos los puntos y muestro la salida

```sh
cmp "$OUT/serial.csv" "$OUT/paralelo1.csv" && echo "P0 y P1: CSV idénticos"
cmp "$OUT/serial.csv" "$OUT/paralelo2.csv" && echo "P0 y P2: CSV idénticos"
head -n 10 "$OUT/paralelo2.csv"
```

`cmp` compara los archivos completos. Si hay diferencias, no aparece el mensaje de éxito y reviso la discrepancia. La salida contiene tres columnas, sin encabezado: `x,y,clase`.

| Clase | Interpretación |
| --- | --- |
| 0 | Ruido |
| 1 | Core o primer orden |
| 2 | Borde o segundo orden |

Puedo verificar también las coordenadas y mostrar los conteos con este bloque:

```sh
.venv/bin/python - "$INPUT" "$OUT/serial.csv" <<'PY'
import sys
import numpy as np

puntos = np.loadtxt(sys.argv[1], delimiter=",", ndmin=2)
salida = np.loadtxt(sys.argv[2], delimiter=",", ndmin=2)
if salida.shape != (len(puntos), 3):
    raise SystemExit("La salida no tiene N filas y tres columnas.")
np.testing.assert_array_equal(salida[:, :2], puntos)
if not np.isin(salida[:, 2], [0, 1, 2]).all():
    raise SystemExit("Encontré una clase fuera de 0, 1 y 2.")
conteos = np.bincount(salida[:, 2].astype(int), minlength=3)
print(f"N={len(puntos)}; ruido={conteos[0]}; core={conteos[1]}; borde={conteos[2]}")
print("Coordenadas y orden de los puntos conservados.")
PY
```

**Lo que explico:** «La igualdad de los CSV demuestra que mis versiones serial y paralelas producen las mismas clases para cada punto. No basta comparar sólo los totales, y la coincidencia entre versiones no sustituye una referencia externa».

## 6. Si necesito demostrar corrección frente a una referencia externa

Para un conjunto de tamaño manejable, comparo la salida serial con DBSCAN de scikit-learn usando los mismos parámetros. Como ya comprobé que P1 y P2 coinciden con P0, esta comprobación se extiende a las tres salidas.

```sh
.venv/bin/python - "$INPUT" "$OUT/serial.csv" "$EPS" "$MIN_SAMPLES" <<'PY'
import sys
import numpy as np
from sklearn.cluster import DBSCAN

puntos = np.loadtxt(sys.argv[1], delimiter=",", ndmin=2)
salida = np.loadtxt(sys.argv[2], delimiter=",", ndmin=2)
epsilon = float(sys.argv[3])
minimo = int(sys.argv[4])

modelo = DBSCAN(eps=epsilon, min_samples=minimo, algorithm="kd_tree").fit(puntos)
esperado = np.where(modelo.labels_ == -1, 0, 2)
esperado[modelo.core_sample_indices_] = 1
np.testing.assert_array_equal(salida[:, :2], puntos)
np.testing.assert_array_equal(salida[:, 2], esperado)
print(f"VALIDACIÓN EXTERNA CORRECTA: coinciden las clases de los {len(puntos)} puntos.")
PY
```

`labels_` contiene identificadores de clúster y `-1` para ruido. Los convierto a mis clases: ruido=0, core=1 y resto=borde=2. No comparo identificadores de clúster porque mi implementación clasifica ruido/core/borde y no asigna esos identificadores.

Esta comprobación externa puede requerir mucha memoria y tiempo en conjuntos grandes o con vecindarios muy densos, incluso con `kd_tree`. No la lanzo automáticamente sobre un archivo grande desconocido. Si sólo pruebo un subconjunto, lo presento como validación de ese subconjunto y ejecuto ambas implementaciones sobre él: quitar puntos cambia los vecindarios y no permite validar directamente las etiquetas del conjunto completo.

Si surge una discrepancia, reviso parámetros, filas afectadas y distancias cercanas a epsilon. No modifico el radio ni introduzco una tolerancia sólo para conseguir coincidencia.

## 7. Si el profesor solicita probar otros hilos o particiones

Por ejemplo, vuelvo a ejecutar P2 con diez hilos y 64 particiones:

```sh
bin/paralelo2 "$INPUT" "$OUT/paralelo2_t10_k64.csv" "$EPS" "$MIN_SAMPLES" 10 64
cmp "$OUT/serial.csv" "$OUT/paralelo2_t10_k64.csv" && echo "P2 con 10 hilos y 64 bloques coincide con P0"
```

Cambio únicamente la distribución del trabajo. Mantengo el archivo, epsilon y min_samples. Los bloques son rangos de índices; cada punto sigue consultando vecinos de todo el conjunto. La barrera entre fases garantiza que el vector de cores esté completo antes de clasificar los bordes.

Si cambio epsilon o min_samples a petición del profesor, vuelvo a ejecutar las tres versiones con esos nuevos parámetros y comparo las salidas de esa misma configuración.

Los tiempos individuales sirven para mostrar ejecuciones reales, pero no constituyen una evaluación estadística de rendimiento. Para afirmar una aceleración estable necesito calentamiento y varias repeticiones por configuración, como en mi evaluación original.

## Qué scripts utilizo en este reto

Para el archivo del profesor utilizo directamente `bin/serial`, `bin/paralelo1` y `bin/paralelo2`, más los bloques de comprobación anteriores.

**No ejecuto `generar_datos.py` sobre el nombre del archivo recibido ni utilizo `experimentos.py --sizes N` para medirlo.** El primero genera datos sintéticos y el segundo también genera sus propios CSV por tamaño: indicar el mismo N no hace que use el archivo del profesor. Por eso doy al CSV recibido un nombre propio y conservo el original.

`validar_resultados.py`, al ejecutarlo normalmente, prueba sus casos predefinidos y `data/4000_data.csv`; no selecciona automáticamente este archivo nuevo. Para contrastar los datos recibidos uso el paso 6.

Las salidas quedan dentro de la ruta que puedo consultar con:

```sh
echo "$OUT"
ls -lh "$OUT"
```

Los CSV en `data/` están excluidos de Git. La carpeta nueva de resultados puede aparecer como no versionada; no se sube automáticamente.

## Respuesta breve que puedo dar al profesor

«Coloco su archivo en data, compruebo que contiene dos coordenadas numéricas por fila y utilizo los parámetros que me indique. Ejecuto las tres versiones sobre el mismo archivo y comparo sus CSV completos. Compruebo que se conservan los puntos y que cada uno recibe una clase válida. Para un conjunto manejable, además contrasto esas clases con scikit-learn. No regenero ni sustituyo sus datos por los de mi experimento original».
