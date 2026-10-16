# Reproducción limpia comprobada

Fecha: 15 de octubre de 2026. Repositorio remoto privado: https://github.com/victormbr-creator/dbscan-openmp.

Commit clonado y probado: `b6d894600f97fc5e866fb451b361a09857d27913`.

Directorio independiente: `/private/tmp/dbscan-repro-20261015`. Antes de ejecutar, no existían `data/` ni `bin/` en el clon. Se creó un entorno `.venv` nuevo; no se copió el entorno, los datasets ni los ejecutables del proyecto original. El clon sí contiene los resultados históricos versionados, que no son entradas de la validación.

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

- Python 3.14.5; NumPy 2.5.4, Matplotlib 3.11.2 y scikit-learn 1.9.1 instalados desde el índice de paquetes. Dependencias transitivas registradas en `requirements-repro.txt`.
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

La prueba se hizo en el mismo Mac, usando LLVM/libomp y Python del sistema. Comprueba independencia de archivos locales previos, no portabilidad a otro sistema operativo ni instalación desde cero de dependencias del sistema. No se volvió a ejecutar la matriz de rendimiento completa: las 1160 mediciones originales permanecen intactas.

Los primeros intentos de red fueron bloqueados por el sandbox; al autorizar acceso de red se completaron clonación y descarga. Las advertencias sobre la caché de pip fueron de permisos y no impidieron la instalación. No se modificaron permisos del sistema ni se instaló otro compilador.

Las correcciones posteriores son documentales y añaden el generador PDF; los algoritmos y las dependencias de cálculo permanecen iguales al commit probado. La generación PDF utiliza ReportLab como dependencia opcional, separada de la validación C++/OpenMP.
