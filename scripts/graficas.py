"""Gráficas por panel para conservar todas las configuraciones legibles."""

# Leo el resumen con csv, organizo rutas con Path y dibujo con Matplotlib.
# math se usa para distribuir paneles y representar las potencias de dos.
import argparse
import csv
import math
from pathlib import Path
import matplotlib

# Agg genera imágenes sin abrir ventanas; debo elegirlo antes de importar pyplot.
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# Recibo la ruta de summary.csv. No ejecuto DBSCAN ni recalculo las mediciones.
def plot(summary):
    # DictReader usa el encabezado para obtener diccionarios; los valores llegan como texto.
    with summary.open() as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("El resumen no contiene configuraciones completas")
    # Convierto N, hilos y k a enteros, y tiempos/speedup a flotantes para graficar.
    for r in rows:
        for key in ["n", "threads", "k"]:
            r[key] = int(r[key])
        for key in ["mean_seconds", "speedup"]:
            r[key] = float(r[key])
    # Las comprensiones con llaves eliminan duplicados; sorted fija el orden de los paneles.
    # La lista de hilos considera sólo las versiones paralelas.
    sizes = sorted({r["n"] for r in rows})
    threads = sorted({r["threads"] for r in rows if r["mode"] != "serial"})

    # Creo dos columnas y las filas necesarias: ceil redondea hacia arriba.
    # squeeze=False mantiene axes como matriz aun con una sola fila.
    def panels(values):
        fig, axes = plt.subplots(
            math.ceil(len(values) / 2),
            2,
            figsize=(12, 4 * math.ceil(len(values) / 2)),
            squeeze=False,
        )
        # axes.flat permite recorrer los ejes en una dimensión; oculto los que sobren.
        for ax in axes.flat[len(values) :]:
            ax.set_visible(False)
        return fig, list(axes.flat)

    # Ajusto espacios dejando sitio arriba al título, guardo el PNG a 160 dpi
    # en la carpeta del resumen y cierro la figura para liberar recursos.
    def finish(fig, name):
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        fig.savefig(summary.parent / (name + ".png"), dpi=160)
        plt.close(fig)

    # Primera gráfica: un panel por cantidad de hilos; cada curva fija versión y k.
    fig, axes = panels(threads)
    fig.suptitle("Tiempo medio de cálculo por configuración")
    # zip empareja cada panel con su número de hilos. Incluyo P0 en todos los paneles
    # como referencia serial; P0 sigue usando un solo hilo.
    for ax, t in zip(axes, threads):
        groups = {}
        for r in rows:
            if r["mode"] != "serial" and r["threads"] != t:
                continue
            # Traduzco nombres del ejecutable a las etiquetas del informe; distingo cada k de P2.
            label = {"serial": "P0", "paralelo1": "P1", "paralelo2": "P2"}[r["mode"]]
            if r["mode"] == "paralelo2":
                label += f", k={r['k']}"
            # setdefault crea una lista por curva y agrega la fila correspondiente.
            groups.setdefault(label, []).append(r)
        # Ordeno cada curva por N antes de unir sus puntos. lambda r: r["n"] es
        # una función corta que extrae N como clave de orden. Divido N entre 1000
        # para mostrar miles de puntos y multiplico segundos por 1000 para obtener ms.
        for label, group in groups.items():
            group.sort(key=lambda r: r["n"])
            ax.plot(
                [r["n"] / 1000 for r in group],
                [r["mean_seconds"] * 1000 for r in group],
                marker=".",
                label=label,
            )
        ax.set(title=f"{t} hilos (P0 usa 1)", xlabel="Puntos (miles)", ylabel="Tiempo medio (ms)")
        # Añado una cuadrícula tenue y una leyenda de dos columnas para facilitar la lectura.
        ax.grid(alpha=0.2)
        ax.legend(fontsize=7, ncol=2)
    finish(fig, "tiempo")
    # Genero otras dos figuras: speedup frente a hilos y speedup frente a k.
    # Ahora cada panel fija N; uso el speedup ya calculado en summary.csv.
    for x, name in [("threads", "speedup_hilos"), ("k", "speedup_particiones")]:
        fig, axes = panels(sizes)
        fig.suptitle("Speedup = tiempo medio P0 / tiempo medio paralelo")
        for ax, n in zip(axes, sizes):
            groups = {}
            for r in rows:
                # Excluyo P0 de las curvas de speedup y filtro el tamaño del panel.
                # Al variar k sólo tiene sentido dibujar P2.
                if r["n"] != n or r["mode"] == "serial":
                    continue
                if x == "k" and r["mode"] != "paralelo2":
                    continue
                # Al variar hilos, cada curva fija la versión y el k de P2.
                # Al variar k, cada curva fija la cantidad de hilos.
                label = (
                    ("P1" if r["mode"] == "paralelo1" else f"P2, k={r['k']}")
                    if x == "threads"
                    else f"P2, {r['threads']} hilos"
                )
                groups.setdefault(label, []).append(r)
            # Ordeno por la variable horizontal. Para k uso log2: 2,4,8,... quedan
            # equiespaciados, pero las marcas mostrarán los valores originales de k.
            for label, group in groups.items():
                group.sort(key=lambda r: r[x])
                ax.plot(
                    [math.log2(r[x]) if x == "k" else r[x] for r in group],
                    [r["speedup"] for r in group],
                    marker=".",
                    label=label,
                )
            # Dibujo la meta 1.5 como referencia horizontal; no representa una medición.
            ax.axhline(1.5, color="gray", linestyle="--", label="Meta 1.5×")
            ax.set(
                title=f"N = {n:,}",
                xlabel="Número de hilos" if x == "threads" else "Particiones k",
                ylabel="Speedup (×)",
            )
            # Obtengo las posiciones distintas del eje horizontal; transformo la posición
            # con log2 si corresponde y conservo la etiqueta numérica original.
            ticks = sorted({r[x] for group in groups.values() for r in group})
            ax.set_xticks(
                [math.log2(v) if x == "k" else v for v in ticks], labels=[str(v) for v in ticks]
            )
            ax.grid(alpha=0.2)
            ax.legend(fontsize=7, ncol=2)
        finish(fig, name)
    print(summary.parent)


# Recibo un argumento posicional: la ruta del summary.csv que quiero graficar.
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    plot(parser.parse_args().summary)
