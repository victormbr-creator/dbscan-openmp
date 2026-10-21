import argparse
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def visualizar(entrada, salida, titulo=None):
    if salida.suffix.lower() != ".png" or entrada.resolve() == salida.resolve():
        raise ValueError("La salida debe ser un PNG distinto del CSV de entrada.")

    datos = np.loadtxt(entrada, delimiter=",", ndmin=2)
    if datos.shape[0] == 0 or datos.shape[1] != 3:
        raise ValueError("Necesito un CSV de resultados sin encabezado: x,y,clase.")
    if not np.isfinite(datos).all():
        raise ValueError("El archivo contiene NaN o infinito.")
    if not np.isin(datos[:, 2], [0, 1, 2]).all():
        raise ValueError("Las clases deben ser 0=ruido, 1=core o 2=borde.")

    clases = datos[:, 2].astype(int)
    fig, ax = plt.subplots(figsize=(9, 7))

    estilos = [
        (1, "Core", "#2672B8", "o", 12),
        (2, "Borde", "#D77B00", "^", 35),
        (0, "Ruido", "#BE2633", "x", 40),
    ]
    for clase, nombre, color, marcador, tamano in estilos:
        seleccion = clases == clase
        cantidad = int(seleccion.sum())
        ax.scatter(
            datos[seleccion, 0],
            datos[seleccion, 1],
            c=color,
            marker=marcador,
            s=tamano,
            alpha=0.8,
            label=f"{nombre} ({clase}): {cantidad:,}",
        )

    ax.set_aspect("equal", adjustable="box")
    ax.set(xlabel="x", ylabel="y", title=f"Clasificación DBSCAN · N = {len(datos):,}")
    if titulo is not None:
        ax.set_title(titulo, fontsize=11, pad=12)
    ax.grid(alpha=0.15)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    fig.tight_layout()

    salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(salida.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Dibujo las clases de un CSV de salida x,y,clase, sin volver a ejecutar DBSCAN."
    )
    parser.add_argument("entrada", type=Path, help="CSV de salida de P0, P1 o P2: x,y,clase")
    parser.add_argument("--output", type=Path, help="Ruta del PNG; por defecto, junto al CSV")
    args = parser.parse_args()
    salida = args.output or args.entrada.with_name(args.entrada.stem + "_puntos.png")
    try:
        visualizar(args.entrada, salida)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
