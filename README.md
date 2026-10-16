# DBSCAN paralelo con OpenMP

Clasificación propia en C++17: `0` ruido, `1` core de primer orden, `2` core de segundo orden (borde). No se asignan clústeres. El propio punto cuenta en min_samples.

## Reproducir

Desde `~/Documents/DBSCAN_Proyecto`:

```sh
.venv/bin/python scripts/generar_datos.py --n 4000
make all
bin/serial data/4000_data.csv results/serial/4000_results.csv 0.03 10
bin/paralelo1 data/4000_data.csv results/paralelo1/4000_results.csv 0.03 10 5
bin/paralelo2 data/4000_data.csv results/paralelo2/4000_results.csv 0.03 10 5 16
.venv/bin/python scripts/validar_resultados.py
.venv/bin/python scripts/experimentos.py --quick
.venv/bin/python scripts/experimentos.py --full --individual
```

El último comando estima; **no ejecuta la matriz completa**. Después de autorizarla, añadir `--run`. El perfil individual selecciona N={20000,80000,140000,200000}, mitad de las configuraciones, con todos los hilos y particiones y diez repeticiones. Esta selección es una propuesta bajo la reducción permitida por el profesor. Sin `--individual`, se usan los ocho tamaños. `--sizes` permite elegir otros; `--repetitions` cambia las repeticiones para exploración, pero la entrega exige diez.

Los programas aceptan `entrada salida epsilon min_samples [hilos] [k]`. Usar `-` como salida evita escribir CSV durante los experimentos. La salida estándar es un objeto JSON con tiempo en segundos, conteos y número real de hilos. La salida CSV no tiene encabezado: x,y,clase. Los directorios de salida deben existir.

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
