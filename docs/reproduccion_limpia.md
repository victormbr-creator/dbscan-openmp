# Reproducción limpia comprobada

Fecha: 15 de octubre de 2026. Repositorio remoto privado: https://github.com/victormbr-creator/dbscan-openmp.

Commit clonado y probado: `b6d894600f97fc5e866fb451b361a09857d27913`.

Directorio independiente: `/private/tmp/dbscan-repro-20261015`. Antes de ejecutar comprobé que no existían `data/` ni `bin/` en el clon. Creé un entorno `.venv` nuevo, sin copiar el entorno, los datasets ni los ejecutables del proyecto original. El clon sí contiene los resultados históricos versionados, que no son entradas de la validación.

## Comandos ejecutados

```sh
git clone https://github.com/victormbr-creator/dbscan-openmp.git /private/tmp/dbscan-repro-20261015
cd /private/tmp/dbscan-repro-20261015
python3 -m venv .venv
.venv/bin/python -m pip install --no-cache-dir -r requirements.txt
make all
.venv/bin/python scripts/generar_datos.py --n 4000
.venv/bin/python scripts/validar_resultados.py
.venv/bin/python -m pip check
.venv/bin/python --version
```

## Resultados observados

- Python 3.14.5; NumPy 2.5.4, Matplotlib 3.11.2 y scikit-learn 1.9.1 instalados desde el índice de paquetes. Registré las dependencias transitivas en `requirements-repro.txt`.
- Compilación de P0/P1/P2 con el Makefile: correcta, sin advertencias en la salida observada.
- Generación: exactamente 4000 filas y dos columnas; primeros puntos (0.415,0.446), (0.470,0.007), (0.784,0.500), (0.406,0.451), (0.466,0.452).
- Validación: ocho casos y 120 ejecuciones correctas. En datos del profesor: 3829 core, 112 segundo orden y 59 ruido.
- `pip check`: No broken requirements found.

| Caso | Ruido | Core | Segundo orden |
|---|---:|---:|---:|
| Profesor | 59 | 3829 | 112 |
| Duplicados | 1 | 3 | 0 |
| Distancia epsilon | 1 | 1 | 3 |
| Aislados | 3 | 0 | 0 |
| Densos | 0 | 20 | 0 |
| Un punto | 0 | 1 | 0 |
| min_samples > N | 3 | 0 | 0 |
| Límites de bloques | 2 | 3 | 1 |

## Límites de esta comprobación

Realicé la prueba en el mismo Mac con LLVM/libomp y Python del sistema. Comprobé independencia de archivos locales previos, no portabilidad a otro sistema operativo ni instalación desde cero de dependencias del sistema. No repetí la matriz de rendimiento completa durante esta comprobación; conservé intactas las 1160 mediciones originales.

Realicé esta comprobación con asistencia de Codex, como declaro en [uso_ia.md](uso_ia.md). El registro corresponde al commit indicado, no a una nueva campaña de rendimiento. Los cambios posteriores de documentación y formato no sustituyen esta evidencia histórica.

Para generar el PDF utilizo ReportLab como dependencia opcional, separada de la compilación y validación C++/OpenMP.
