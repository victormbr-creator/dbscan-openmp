"""Generación reproducible con los parámetros del notebook del profesor."""

# Con Path manejo rutas; argparse lee opciones de la terminal.
# NumPy transforma y guarda los puntos; make_blobs genera grupos de puntos sintéticos.
from pathlib import Path
import argparse
import numpy as np
from sklearn.datasets import make_blobs

# __file__ es este archivo; resolve() obtiene su ruta absoluta.
# parents[0] es scripts/ y parents[1] es la raíz del proyecto. Así no dependo
# de la carpeta desde la que ejecuto el comando.
ROOT = Path(__file__).resolve().parents[1]


# Genero n puntos, guardo el CSV y devuelvo su ruta para reutilizarla en otros scripts.
def generar(n):
    # Rechazo tamaños vacíos o negativos antes de llamar al generador.
    if n < 1:
        raise ValueError("n debe ser positivo")
    # make_blobs devuelve coordenadas y etiquetas de grupo; con _ descarto las etiquetas.
    # Uso cuatro centros, dispersión 0.06 y semilla 11 para repetir la generación
    # con el mismo n y entorno. center_box limita los centros, no todos los puntos.
    points, _ = make_blobs(
        n_samples=n, centers=4, cluster_std=0.06, random_state=11, center_box=(0, 1.0)
    )
    # [:, ::-1] conserva todas las filas e invierte las dos columnas.
    # abs toma el valor absoluto y round redondea a tres decimales, como en el notebook.
    points = np.round(np.abs(points[:, ::-1]), 3)
    # El operador / une partes de una ruta; la f-string inserta el valor de n en el nombre.
    target = ROOT / "data" / f"{n}_data.csv"
    # Creo data/ y sus padres si hacen falta; no falla si la carpeta ya existe.
    target.parent.mkdir(parents=True, exist_ok=True)
    # Escribo x,y sin encabezado y con tres decimales; si el CSV existe, lo reemplazo.
    np.savetxt(target, points, delimiter=",", fmt="%.3f")
    # Recargo lo escrito: ndmin=2 mantiene una matriz incluso si hay un solo punto.
    # Compruebo n filas, dos columnas, ausencia de NaN/infinito e igualdad de valores.
    loaded = np.loadtxt(target, delimiter=",", ndmin=2)
    assert loaded.shape == (n, 2) and np.isfinite(loaded).all()
    assert np.array_equal(loaded, points)
    return target


# Este bloque sólo se ejecuta al lanzar el archivo, no al importarlo desde experimentos.py.
# --n recibe un entero y vale 4000 si no lo indico. Muestro la ruta y las primeras cinco filas.
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=4000)
    args = p.parse_args()
    target = generar(args.n)
    print(target)
    print(np.loadtxt(target, delimiter=",", ndmin=2)[:5])
