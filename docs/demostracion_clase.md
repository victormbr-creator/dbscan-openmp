# Demostración en clase: DBSCAN con OpenMP

En esta demostración compilo mis tres versiones, compruebo su clasificación y ejecuto una campaña experimental nueva con los cuatro tamaños de mi modalidad individual. Después muestro sus resultados y gráficas.

## 1. Preparación antes de clase

Llevo el proyecto y sus dependencias instaladas. Conecto el equipo a la corriente, evito que entre en reposo y cierro tareas pesadas para reducir interferencias durante las mediciones. No necesito conexión a Internet para ejecutar la demostración con el entorno ya preparado.

Abro Terminal y compruebo el entorno:

```sh
cd ~/Documents/DBSCAN_Proyecto
pwd
.venv/bin/python -c 'import numpy, sklearn, matplotlib; print("Dependencias disponibles")'
make -n all
```

Espero ver la ruta del proyecto y `Dependencias disponibles`. `make -n` muestra lo que compilaría, sin compilar. Si no hay cambios pendientes puede indicar que no hay nada por hacer.

Uso `.venv/bin/python` explícitamente en todos los comandos: no necesito activar el entorno con `source`. Instalo o reparo dependencias antes de la presentación si este paso falla.

## 2. Compilo y genero los datos de la demostración

Ya en clase, desde la misma carpeta ejecuto:

```sh
make -B all
.venv/bin/python scripts/generar_datos.py --n 4000
mkdir -p results/serial results/paralelo1 results/paralelo2
```

`-B` obliga a recompilar para mostrar el proceso, aunque ya existan los ejecutables. Obtengo `bin/serial`, `bin/paralelo1` y `bin/paralelo2`. Genero 4000 puntos para una prueba breve y creo los directorios donde escribiré sus clasificaciones.

**Lo que explico:** «Las tres versiones comparten las reglas de clasificación. P0 recorre los puntos secuencialmente; P1 reparte los puntos con OpenMP; P2 reparte k bloques de índices. En P2 mantengo la consulta global de vecinos y una barrera entre las dos fases».

## 3. Muestro que las tres versiones clasifican igual

```sh
bin/serial data/4000_data.csv results/serial/4000_results.csv 0.03 10
bin/paralelo1 data/4000_data.csv results/paralelo1/4000_results.csv 0.03 10 5
bin/paralelo2 data/4000_data.csv results/paralelo2/4000_results.csv 0.03 10 5 16
```

Los argumentos son entrada, salida, epsilon y min_samples; en las versiones paralelas añado hilos y, para P2, particiones. En este ejemplo uso epsilon=0.03, min_samples=10, cinco hilos y 16 bloques en P2.

Cada programa imprime un JSON. Para estos datos espero `n=4000`, `noise=59`, `core=3829` y `border=112` en las tres versiones. Los tiempos pueden variar. El CSV guarda `x,y,clase`, con `0=ruido`, `1=core` y `2=borde`.

Compruebo igualdad del archivo completo:

```sh
cmp results/serial/4000_results.csv results/paralelo1/4000_results.csv && echo "P0 y P1: CSV idénticos"
cmp results/serial/4000_results.csv results/paralelo2/4000_results.csv && echo "P0 y P2: CSV idénticos"
head -n 5 results/paralelo2/4000_results.csv
```

Si `cmp` encuentra diferencias, no imprime el mensaje de éxito y debo revisar el resultado.

**Lo que explico:** «Comparo las coordenadas y la clase de cada punto, no sólo los totales. Estas ejecuciones individuales muestran el funcionamiento; para comparar rendimiento usaré diez repeticiones».

## 4. Ejecuto los experimentos completos de mi modalidad individual

```sh
.venv/bin/python scripts/experimentos.py --full --individual --run --force
```

Este es el comando central de mi demostración. Lo ejecuto una sola vez y espero a que termine.

| Opción | Para qué la uso |
| --- | --- |
| `--full` | Selecciono la campaña completa, en lugar del piloto pequeño. |
| `--individual` | Utilizo N=20000, 80000, 140000 y 200000. |
| `--run` | Ejecuto las mediciones; sin esta opción sólo obtendría una estimación. |
| `--force` | Creo una campaña nueva para medir en clase, sin reutilizar mediciones anteriores. |

Con los diez procesadores lógicos de mi Mac se prueban 1, 5, 10 y 20 hilos, y para P2 se prueban k=2, 4, 8, 16, 32 y 64. El script detecta los procesadores; en otro equipo los hilos y el número de configuraciones pueden cambiar.

| Versión | Configuraciones por tamaño | Cuatro tamaños | Diez repeticiones |
| --- | ---: | ---: | ---: |
| P0 | 1 | 4 | 40 |
| P1 | 4 | 16 | 160 |
| P2 | 4 × 6 = 24 | 96 | 960 |
| Total | 29 | 116 | 1160 |

El script genera los cuatro datasets automáticamente. No tengo que generar manualmente los de 80000, 140000 o 200000 puntos.

Al comenzar, muestra un piloto con 20000 puntos y una estimación de duración. Luego ejecuta la validación contra scikit-learn: ocho casos con 15 configuraciones cada uno, es decir, 120 ejecuciones de comprobación. Debe aparecer:

```text
VALIDACIÓN CORRECTA: clases 0=ruido, 1=core, 2=segundo orden
```

**Ese mensaje termina la validación previa, no los experimentos.** Después genera los datasets y ejecuta las mediciones. Puede pasar un intervalo sin imprimir nuevos mensajes; consulto el avance como explico abajo.

Además de las 1160 mediciones registradas, en una campaña nueva sin fallos ejecuta 116 calentamientos descartados, el piloto y las 120 comprobaciones. No cuento esas ejecuciones como repeticiones medidas.

**Lo que explico mientras corre:** «Por cada tamaño comparo 29 configuraciones y repito cada una diez veces. Intercalo el orden con una semilla fija y descarto un calentamiento por configuración. El tiempo registrado lo mide C++ y corresponde al cómputo; no incluye lectura ni escritura del CSV».

La estimación inicial extrapola el peor caso cuadrático y no supone aceleración paralela. No es una duración garantizada: la parada temprana y el paralelismo pueden hacer que la ejecución real termine mucho antes. Reservo margen para la demostración y no prometo un tiempo fijo.

### Cómo compruebo el avance sin detener la corrida

Abro una segunda pestaña de Terminal y ejecuto:

```sh
cd ~/Documents/DBSCAN_Proyecto
pgrep -fl 'scripts/experimentos.py|bin/(serial|paralelo1|paralelo2)'
wc -l results/benchmarks/*/raw.csv
```

`pgrep` permite ver si el coordinador o alguno de los programas está activo. `wc` muestra las líneas de cada archivo de mediciones, incluidas las campañas antiguas. Repito el segundo comando después de unos segundos y localizo el archivo nuevo cuyo contador crece. La última línea `total` suma todas las campañas: no es el progreso de la nueva.

Una corrida completa sin fallos tendrá **1161 líneas** en su `raw.csv`: un encabezado y 1160 mediciones. El contador de líneas muestra progreso, pero no demuestra que todas hayan sido exitosas; lo compruebo con el resumen y la auditoría.

Si el CSV nuevo todavía no aparece, el script puede seguir validando o generando datos. No lanzo otra campaña mientras la primera siga activa. No presiono Ctrl+C en la pestaña de la corrida si quiero dejarla terminar.

## 5. Compruebo que terminó y selecciono la campaña nueva

Al terminar deben aparecer estas dos líneas, con una ruta real en lugar de `ID`:

```text
Resultados: /Users/victormanuelbenitezrenteria/Documents/DBSCAN_Proyecto/results/benchmarks/ID
Configuraciones incompletas: 0
```

También debe regresar el prompt de Terminal. Inmediatamente después, antes de ejecutar otro comando, puedo consultar:

```sh
echo $?
```

Espero `0`, que indica finalización exitosa. Si aparecen configuraciones incompletas o una excepción, no presento la campaña como terminada correctamente.

Copio la ruta que apareció tras `Resultados:` y la asigno a `RUN_DIR`. **Sustituyo `ID_DE_LA_CORRIDA` por el identificador real; no ejecuto el marcador literalmente.**

```sh
RUN_DIR="results/benchmarks/ID_DE_LA_CORRIDA"
wc -l "$RUN_DIR/raw.csv" "$RUN_DIR/summary.csv"
```

Espero 1161 líneas en `raw.csv` y 117 en `summary.csv`, contando sus encabezados. Uso esa misma variable en los siguientes pasos y en la misma pestaña de Terminal.

## 6. Audito la corrida que acabo de realizar

```sh
.venv/bin/python scripts/auditar_experimentos.py "$RUN_DIR"
```

Esta auditoría comprueba las 1160 mediciones, sus repeticiones, los hashes de los ejecutables y datasets, las medias, el speedup y la eficiencia. También vuelve a ejecutar las 116 configuraciones y compara sus CSV completos contra P0, incluidos los datos de 200000 puntos. Es un paso adicional que toma tiempo; no agrega repeticiones al experimento.

Espero mensajes de igualdad contra P0 para los cuatro tamaños y, al final:

```text
Auditoría correcta: 1160 mediciones, 116 configuraciones, hashes y cálculos comprobados.
```

La auditoría genera `validation.csv` dentro de la campaña nueva. Para conservar la comprobación de hashes, no recompilo ni sustituyo datasets entre medir y auditar.

**Lo que explico:** «Los casos pequeños se comparan con scikit-learn. En la auditoría de la matriz completa comparo las versiones paralelas contra mi serial punto por punto; no afirmo que todos los conjuntos grandes se hayan validado con scikit-learn».

## 7. Genero y muestro las gráficas de esa misma corrida

```sh
.venv/bin/python scripts/graficas.py "$RUN_DIR/summary.csv"
open "$RUN_DIR/tiempo.png" "$RUN_DIR/speedup_hilos.png" "$RUN_DIR/speedup_particiones.png"
```

`open` abre las imágenes en macOS. Muestro el tiempo medio frente al tamaño, el speedup frente a hilos y el speedup de P2 frente a particiones.

Para mostrar en la terminal la mejor configuración de cada versión y tamaño, leo el resumen de esta campaña:

```sh
.venv/bin/python - "$RUN_DIR/summary.csv" <<'PY'
import csv
import sys

with open(sys.argv[1]) as archivo:
    filas = list(csv.DictReader(archivo))

print("N       versión     hilos   k    media_ms   speedup")
for n in sorted({int(f["n"]) for f in filas}):
    for version in ["serial", "paralelo1", "paralelo2"]:
        candidatas = [f for f in filas if int(f["n"]) == n and f["mode"] == version]
        mejor = min(candidatas, key=lambda f: float(f["mean_seconds"]))
        print(f"{n:<7} {version:<11} {int(mejor['threads']):>3} "
              f"{int(mejor['k']):>4} {float(mejor['mean_seconds']) * 1000:>11.4f} "
              f"{float(mejor['speedup']):>9.3f}")
PY
```

Selecciono la menor **media de diez repeticiones**, no la ejecución individual más rápida. `k=0` indica que no aplica en P0/P1. Este bloque sólo lee el CSV; no vuelve a medir.

**Lo que explico:** «Calculo speedup como tiempo medio serial dividido por tiempo medio paralelo, usando el mismo N. Un speedup de 5 significa que el tiempo paralelo es una quinta parte del serial. La eficiencia es speedup/hilos; no es el porcentaje de uso de CPU. Los valores de hoy pueden diferir de los del informe por las condiciones de ejecución».

## Qué archivos se generan

- Los datos en `data/` y las clasificaciones de 4000 puntos se regeneran; están excluidos de Git.
- La campaña nueva se guarda en su propia carpeta de `results/benchmarks/`: `metadata.json`, `raw.csv` y `summary.csv`.
- La auditoría agrega `validation.csv` y el generador de gráficas agrega tres PNG.
- El PDF entregado sigue mostrando la campaña histórica. No ejecuto `generar_informe.py` para mostrar resultados nuevos: ese script está vinculado a la campaña original.

Las mediciones nuevas permanecen locales hasta que decida agregarlas a Git. Para presentar los resultados del día uso la carpeta que imprimió el comando y sus gráficas.

## Si algo falla durante la demostración

| Situación | Qué reviso |
| --- | --- |
| No encuentra `.venv/bin/python` o `scripts/...` | Compruebo con `pwd` que estoy en `~/Documents/DBSCAN_Proyecto`. |
| Falta `data/4000_data.csv` | Ejecuto el generador del paso 2 antes de validar o medir. |
| El compilador o una dependencia no se encuentra | Reviso la preparación del entorno; no presento una salida anterior como una ejecución actual. |
| Sólo muestra una estimación y termina | Compruebo que incluí `--run`. |
| Parece detenido después de `VALIDACIÓN CORRECTA` | Reviso procesos y crecimiento de `raw.csv` en la segunda pestaña. |
| Hay mediciones fallidas o configuraciones incompletas | Leo el error y `raw.csv`; no interpreto un resumen parcial como campaña completa. |
| La auditoría falla por hashes | Compruebo que seleccioné la carpeta nueva y mantuve sus binarios y datasets. |

Si interrumpo una campaña creada con `--force`, repetir el mismo comando crea otra carpeta y empieza una campaña nueva. Quitar `--force` tampoco selecciona automáticamente la carpeta con sufijo temporal interrumpida: busca la carpeta base de los metadatos. Para la demostración dejo terminar la corrida o inicio deliberadamente otra desde cero, después de resolver la causa del fallo.
