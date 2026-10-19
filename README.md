# DBSCAN paralelo con OpenMP

Clasificación propia en C++17: `0` ruido, `1` core de primer orden, `2` core de segundo orden (borde). No se asignan clústeres. El propio punto cuenta en min_samples.

## Reproducir

Requiere Git, Python 3.14 (versión de la reproducción comprobada) y LLVM/libomp con OpenMP. El Makefile usa LLVM de Homebrew en Apple Silicon. La reproducción se comprobó en el mismo Mac; no se afirma portabilidad a otros sistemas.

Para una copia nueva del repositorio privado, con acceso autenticado:

```sh
git clone https://github.com/victormbr-creator/dbscan-openmp.git
cd dbscan-openmp
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Desde la raíz del proyecto:

```sh
.venv/bin/python scripts/generar_datos.py --n 4000
make all
mkdir -p results/serial results/paralelo1 results/paralelo2
bin/serial data/4000_data.csv results/serial/4000_results.csv 0.03 10
bin/paralelo1 data/4000_data.csv results/paralelo1/4000_results.csv 0.03 10 5
bin/paralelo2 data/4000_data.csv results/paralelo2/4000_results.csv 0.03 10 5 16
.venv/bin/python scripts/validar_resultados.py
.venv/bin/python scripts/experimentos.py --quick
.venv/bin/python scripts/experimentos.py --full --individual
```

El último comando estima; **no ejecuta la matriz completa**. Después de autorizarla, añadir `--run`. El perfil individual selecciona N={20000,80000,140000,200000}, mitad de las configuraciones, con todos los hilos y particiones y diez repeticiones. Esta selección es una propuesta bajo la reducción permitida por el profesor. Sin `--individual`, se usan los ocho tamaños. `--sizes` permite elegir otros; `--repetitions` cambia las repeticiones para exploración, pero la entrega exige diez.

Los programas aceptan `entrada salida epsilon min_samples [hilos] [k]`. Usar `-` como salida evita escribir CSV durante los experimentos. La salida estándar es un objeto JSON con tiempo en segundos, conteos y número real de hilos. La salida CSV no tiene encabezado: x,y,clase. Los directorios de salida deben existir; el comando `mkdir -p` anterior los crea incluso en un clon nuevo. Los CSV de clasificación de `results/serial/`, `results/paralelo1/` y `results/paralelo2/` son regenerables y están excluidos de Git. Las mediciones y auditorías de `results/benchmarks/` se conservan versionadas.

```sh
.venv/bin/python scripts/graficas.py results/benchmarks/ID/summary.csv
```

Cada ID contiene metadatos, hashes de ejecutables y datasets, mediciones individuales, promedios y desviaciones estándar. Se reanudan mediciones válidas; `--force` crea otra ejecución. Fallas quedan registradas y las configuraciones incompletas no producen promedios. El material del curso está excluido del repositorio propio; no fue modificado.

Consulta `docs/metodologia.md`, `docs/resultados.md` y `docs/uso_ia.md`. La configuración del Makefile usa LLVM de Homebrew; puede sustituirse con `make CXX=/ruta/clang++`.

## Evaluación individual completada

116 configuraciones y 1160 mediciones válidas, sin fallas. Resultados finales en `results/benchmarks/e5129e76b440779f`; informe en [docs/resultados.md](docs/resultados.md). Auditoría punto por punto para todas las configuraciones:

```sh
.venv/bin/python scripts/auditar_experimentos.py results/benchmarks/e5129e76b440779f
```

## Entrega documental

[Informe PDF](output/pdf/informe_dbscan_openmp.pdf), [reproducción limpia](docs/reproduccion_limpia.md) y [justificación de P2 frente a la diapositiva 11](docs/alcance_p2.md).

Para regenerar el PDF, instalar las dependencias documentales opcionales (no hacen falta para compilar o validar):

```sh
.venv/bin/python -m pip install -r requirements-docs.txt
.venv/bin/python scripts/generar_informe.py
```

El PDF usa las mediciones conservadas y no vuelve a ejecutar los experimentos.

Los hashes de fuentes guardados con los experimentos describen el estado de aquella campaña. Incluyen la prueba inicial `src/test_openmp.cpp`, retirada posteriormente de la entrega y recuperable en el historial de Git; no se alteran esos registros históricos.
