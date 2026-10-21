# DBSCAN paralelo con OpenMP

En este proyecto implementé en C++17 la clasificación de puntos bidimensionales en ruido (`0`), core de primer orden (`1`) y segundo orden o borde (`2`). Incluyo el propio punto en `min_samples` y no asigno identificadores de clúster. Desarrollé P0, P1 y P2 con asistencia de IA, como describo en [uso_ia.md](docs/uso_ia.md).

## Entorno y reproducción

Para ejecutar el proyecto utilizo Git, Python 3.14 y LLVM/libomp con OpenMP. Comprobé la reproducción con Python 3.14.5 y LLVM de Homebrew en mi Mac con Apple Silicon. No he comprobado portabilidad a otros sistemas. El Makefile permite indicar otro compilador mediante `make CXX=/ruta/clang++`.

Para obtener una copia nueva de mi repositorio privado, con acceso autenticado, utilizo:

```sh
git clone https://github.com/victormbr-creator/dbscan-openmp.git
cd dbscan-openmp
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Desde la raíz del proyecto, genero los datos, compilo y ejecuto las tres versiones:

```sh
.venv/bin/python scripts/generar_datos.py --n 4000
make all
mkdir -p results/serial results/paralelo1 results/paralelo2
bin/serial data/4000_data.csv results/serial/4000_results.csv 0.03 10
bin/paralelo1 data/4000_data.csv results/paralelo1/4000_results.csv 0.03 10 5
bin/paralelo2 data/4000_data.csv results/paralelo2/4000_results.csv 0.03 10 5 16
.venv/bin/python scripts/validar_resultados.py
```

Los programas aceptan `entrada salida epsilon min_samples [hilos] [k]`. Para evitar la escritura de CSV durante las mediciones uso `-` como salida. La salida estándar es un objeto JSON con tiempo en segundos, conteos y número efectivo de hilos. El CSV de clasificación contiene x, y y clase, sin encabezado.

Creo los directorios de salida con `mkdir -p`, porque deben existir antes de ejecutar los programas. Excluyo de Git los CSV regenerables de `results/serial/`, `results/paralelo1/` y `results/paralelo2/`. Conservo versionadas las mediciones y auditorías de `results/benchmarks/`.

## Visualización de puntos

Para visualizar los puntos clasificados uso el CSV de salida de C++, que contiene `x,y,clase`:

```sh
.venv/bin/python scripts/visualizar_puntos.py results/paralelo2/4000_results.csv
open results/paralelo2/4000_results_puntos.png
```

La gráfica muestra core en azul, borde en naranja y ruido con cruces rojas. Los colores representan clases, no identificadores de clúster. El script lee las etiquetas existentes, incluye todos los puntos y no ejecuta DBSCAN ni altera las mediciones. Si hay puntos coincidentes pueden superponerse. Puedo indicar otra ruta de imagen con `--output ruta/imagen.png`.

## Ejecución de experimentos

Para el piloto y la estimación de la matriz individual utilizo:

```sh
.venv/bin/python scripts/experimentos.py --quick
.venv/bin/python scripts/experimentos.py --full --individual
```

El segundo comando estima la duración; no ejecuta la matriz completa. Para ejecutar esa matriz añado `--run` y, si quiero obtener mediciones nuevas sin reutilizar las existentes, añado `--force`:

```sh
.venv/bin/python scripts/experimentos.py --full --individual --run --force
```

En mi evaluación individual seleccioné N={20000,80000,140000,200000}, la mitad de los tamaños originales, y mantuve todos los hilos, las seis cantidades de particiones y diez repeticiones. Sin `--individual`, el script utiliza los ocho tamaños originales. Con `--sizes` puedo seleccionar otros tamaños y con `--repetitions` puedo modificar las repeticiones para exploración; en la evaluación reportada utilicé diez.

Cada campaña queda en una carpeta identificada por sus metadatos. Allí guardo parámetros, hashes de ejecutables y datasets, tiempos individuales, promedios y desviaciones estándar. El script reanuda mediciones válidas compatibles, registra fallas y no publica promedios de configuraciones incompletas.

Para generar gráficas utilizo la carpeta de la campaña elegida, sustituyendo `ID` por su identificador:

```sh
.venv/bin/python scripts/graficas.py results/benchmarks/ID/summary.csv
```

## Comparación con el CSV del profesor

Para medir el mismo archivo con P0, P1 con cuatro hilos y P2 con cuatro hilos y cuatro particiones, utilizo:

```sh
make all
COMPARE_DIR="results/datos_profesor/comparacion_$(date +%Y%m%d_%H%M%S)"
.venv/bin/python scripts/comparar_profesor.py data/datos_profesor.csv \
  --epsilon 0.03 --min-samples 10 --repetitions 10 --output-dir "$COMPARE_DIR"
open "$COMPARE_DIR/serial_puntos.png" "$COMPARE_DIR/paralelo1_puntos.png" "$COMPARE_DIR/paralelo2_puntos.png"
```

El script lee el archivo recibido sin regenerarlo, compara las clasificaciones y guarda tiempos individuales, promedios, speedups y tres imágenes con sus métricas. Conservo una demostración de 100000 puntos en [output/comparacion_profesor/resultado.md](output/comparacion_profesor/resultado.md). Los comandos y las tres gráficas están en [el instructivo](docs/datos_profesor.md).

## Evaluación reportada

En el informe reporto la campaña `results/benchmarks/e5129e76b440779f`, realizada el 15 de octubre de 2026: 116 configuraciones y 1160 mediciones válidas, sin fallas. Mantengo sus resultados en [docs/resultados.md](docs/resultados.md), sin mezclarlos con campañas posteriores.

Para auditar esa campaña utilizo:

```sh
.venv/bin/python scripts/auditar_experimentos.py results/benchmarks/e5129e76b440779f
```

La auditoría exige los ejecutables y datasets cuyos hashes quedaron registrados en esa campaña. Si una recompilación cambia los hashes, necesito conservar los ejecutables correspondientes o realizar una campaña nueva; no modifico los hashes históricos para hacer pasar la auditoría.

## Documentación

Si recibo un archivo nuevo, sigo el [instructivo para datos del profesor](docs/datos_profesor.md): reviso el CSV, ejecuto las tres versiones sobre sus puntos y compruebo las clasificaciones.

Para mi presentación sigo el [instructivo de demostración en clase](docs/demostracion_clase.md): compilo, compruebo las tres versiones, ejecuto una campaña individual nueva y muestro su auditoría y gráficas.

En [metodologia.md](docs/metodologia.md) explico el algoritmo y la medición. En [alcance_p2.md](docs/alcance_p2.md) justifico P2 frente a la diapositiva 11. También incluyo la [reproducción limpia](docs/reproduccion_limpia.md), el [uso de IA](docs/uso_ia.md) y el [informe PDF](output/pdf/informe_dbscan_openmp.pdf).

Para regenerar el PDF instalo las dependencias documentales opcionales, que no necesito para compilar o validar:

```sh
.venv/bin/python -m pip install -r requirements-docs.txt
make all
.venv/bin/python scripts/generar_figuras_informe.py
.venv/bin/python scripts/generar_informe.py
```

El PDF utiliza las mediciones conservadas e incluye una gráfica de clasificación para cada N: 4000, 20000, 80000, 140000 y 200000. `generar_figuras_informe.py` prepara esas cinco imágenes, verifica los datasets originales y compara P2 con P0; elimina sus CSV temporales sin añadir otra campaña experimental. Si ya tengo las imágenes y `output/figuras/clasificacion/resumen.json`, puedo ejecutar sólo `generar_informe.py`. Mantengo el material del profesor intacto y excluido de mi repositorio propio.

Los hashes de fuentes guardados con los experimentos describen el estado de aquella campaña. Incluyen la prueba inicial `src/test_openmp.cpp`, que retiré posteriormente de la entrega y que puedo recuperar del historial de Git. Los cambios de formato posteriores no sustituyen esos registros históricos.

Para elegir una ejecución concreta de P1 o P2, cambiar hilos/particiones y abrir su imagen, utilizo el [apartado de corridas individuales](docs/demostracion_clase.md#8-ejecuto-una-configuración-particular-y-veo-su-imagen).
