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
THREADS="4"
PARTITIONS="4"
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

### Muestro las tres gráficas, los tiempos y los speedups

Comparo exactamente estas configuraciones sobre el mismo CSV y con el mismo epsilon y min_samples:

| Versión | Hilos | Particiones |
| --- | ---: | ---: |
| P0 serial | 1 | No aplica |
| P1 paralelo1 | 4 | No aplica |
| P2 paralelo2 | 4 | 4 |

Después de preparar las variables del paso 2, ejecuto:

```sh
.venv/bin/python scripts/comparar_profesor.py "$INPUT" \
  --epsilon "$EPS" --min-samples "$MIN_SAMPLES" \
  --repetitions 10 --output-dir "$OUT/comparacion"

open "$OUT/comparacion/serial_puntos.png" \
     "$OUT/comparacion/paralelo1_puntos.png" \
     "$OUT/comparacion/paralelo2_puntos.png"
```

Este script tiene fijadas las tres configuraciones de la tabla; no toma hilos o particiones de otras variables de la terminal. Descarta un calentamiento por configuración, comprueba igualdad punto a punto contra P0 e intercala diez repeticiones por versión: **30 mediciones nuevas, más tres calentamientos**. No recupera los tiempos de los CSV de clasificación anteriores ni genera otros datos.

Al terminar imprime una tabla con tiempo medio, desviación estándar, speedup y eficiencia. Las tres imágenes también incluyen el nombre de la versión, los hilos, k cuando corresponde, el tiempo medio y el speedup. Es normal que los puntos se vean iguales: las clases deben coincidir; la comparación de rendimiento está en los títulos y la tabla.

- `raw.csv`: tiempo de cada repetición, en segundos.
- `summary.csv`: media, desviación estándar, speedup y eficiencia por versión.
- `metadata.json`: archivo utilizado, parámetros, conteos y hashes.
- `resultado.md`: tabla y las tres imágenes en un solo documento.
- Tres PNG: una gráfica de clasificación por versión. Los CSV intermedios se eliminan automáticamente.

Calculo **speedup = media serial / media de la versión** y **eficiencia = speedup / hilos**. Son tiempos internos de cómputo; no incluyen lectura, escritura ni generación de las imágenes. No comparo estos tiempos con los de otro archivo o con parámetros distintos.

Para consultar después los valores guardados, sin volver a ejecutar:

```sh
cat "$OUT/comparacion/summary.csv"
```

Si vuelvo a usar la misma carpeta, el script pide elegir otra o añadir `--overwrite`; esa opción reemplaza los resultados de la comparación en esa carpeta. Si falla, reviso el error y no presento una salida parcial o antigua como una medición nueva.

### Ejemplo medido con el archivo de 100000 puntos

Las siguientes imágenes son la comparación realizada el 20 de octubre de 2026 con `data/datos_profesor.csv`, epsilon=0.03 y min_samples=10. Son una referencia de mi prueba actual; si recibo otro archivo, ejecuto el comando anterior y presento las imágenes y tiempos de la nueva carpeta.

| Versión | Hilos | k | Media (ms) | DE (ms) | Speedup | Eficiencia |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| P0: serial | 1 | - | 80.227 | 0.501 | 1.000× | 100.00% |
| P1: 4 hilos | 4 | - | 23.120 | 0.308 | 3.470× | 86.75% |
| P2: 4 hilos, 4 particiones | 4 | 4 | 22.575 | 0.173 | 3.554× | 88.84% |

DE es la desviación estándar muestral de las diez repeticiones. Estos valores no sustituyen la campaña histórica del informe PDF. La evidencia de esta comparación está en [resultado.md](../output/comparacion_profesor/resultado.md), [raw.csv](../output/comparacion_profesor/raw.csv) y [summary.csv](../output/comparacion_profesor/summary.csv).

**P0 serial:**

![P0 serial: clasificación, tiempo medio y speedup](../output/comparacion_profesor/serial_puntos.png)

**P1 con 4 hilos:**

![P1 con 4 hilos: clasificación, tiempo medio y speedup](../output/comparacion_profesor/paralelo1_puntos.png)

**P2 con 4 hilos y 4 particiones:**

![P2 con 4 hilos y 4 particiones: clasificación, tiempo medio y speedup](../output/comparacion_profesor/paralelo2_puntos.png)


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

Para ejecutar sólo una versión y obtener su imagen con mis variables del paso 2, elijo uno de estos bloques:

```sh
# Sólo P1, con 5 hilos: epsilon y min_samples siguen en las variables acordadas.
bin/paralelo1 "$INPUT" "$OUT/paralelo1_t5.csv" "$EPS" "$MIN_SAMPLES" 5
.venv/bin/python scripts/visualizar_puntos.py "$OUT/paralelo1_t5.csv"
open "$OUT/paralelo1_t5_puntos.png"
```

```sh
# Sólo P2, con 10 hilos y 64 bloques.
bin/paralelo2 "$INPUT" "$OUT/paralelo2_t10_k64.csv" "$EPS" "$MIN_SAMPLES" 10 64
.venv/bin/python scripts/visualizar_puntos.py "$OUT/paralelo2_t10_k64.csv"
open "$OUT/paralelo2_t10_k64_puntos.png"
```

En P1 el último número indica hilos. En P2 los dos últimos indican hilos y bloques, respectivamente. No genero datos sintéticos en este procedimiento: la entrada sigue siendo el CSV del profesor. Puedo consultar ejemplos con imágenes de mis datasets sintéticos y comandos completos en el [apartado 8 del instructivo de clase](demostracion_clase.md#8-ejecuto-una-configuración-particular-y-veo-su-imagen).

Los tiempos individuales sirven para mostrar ejecuciones reales, pero no constituyen una evaluación estadística de rendimiento. Para afirmar una aceleración estable necesito calentamiento y varias repeticiones por configuración, como en mi evaluación original.

## Qué scripts utilizo en este reto

Para el archivo del profesor utilizo `bin/serial`, `bin/paralelo1` y `bin/paralelo2`. Para obtener las tres gráficas con tiempos y speedups utilizo `comparar_profesor.py`, que ejecuta esas versiones con las configuraciones 1 hilo, 4 hilos y 4 hilos/4 particiones, respectivamente.

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
