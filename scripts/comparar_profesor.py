import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np

from visualizar_puntos import visualizar

ROOT = Path(__file__).resolve().parents[1]
CONFIGURACIONES = [
    ("serial", "P0: serial", 1, 0),
    ("paralelo1", "P1: 4 hilos", 4, 0),
    ("paralelo2", "P2: 4 hilos, 4 particiones", 4, 4),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ejecutar(mode, entrada, salida, epsilon, minimo, hilos, bloques):
    command = [
        str(ROOT / "bin" / mode),
        str(entrada),
        str(salida),
        str(epsilon),
        str(minimo),
        str(hilos),
        str(max(1, bloques)),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    info = json.loads(result.stdout)
    if info["threads"] != hilos or info["k"] != bloques:
        raise ValueError("La configuración efectiva difiere de la solicitada.")
    if not math.isfinite(info["seconds"]) or info["seconds"] <= 0:
        raise ValueError("El programa no devolvió un tiempo positivo y finito.")
    return info


def comparar(args):
    entrada = args.entrada.resolve()
    puntos = np.loadtxt(entrada, delimiter=",", ndmin=2)
    if puntos.shape[0] == 0 or puntos.shape[1] != 2 or not np.isfinite(puntos).all():
        raise ValueError("Necesito un CSV de entrada con dos coordenadas finitas por fila.")

    output = args.output_dir.resolve()
    names = ["raw.csv", "summary.csv", "metadata.json", "resultado.md"]
    names += [f"{mode}_puntos.png" for mode, _, _, _ in CONFIGURACIONES]
    if entrada in [output / name for name in names]:
        raise ValueError("La entrada no puede coincidir con un archivo de salida.")
    if any((output / name).exists() for name in names) and not args.overwrite:
        raise ValueError("Ya hay resultados en esa carpeta. Elige otra o usa --overwrite.")

    input_hash = sha(entrada)
    binary_hashes = {mode: sha(ROOT / "bin" / mode) for mode, _, _, _ in CONFIGURACIONES}
    tiempos = {mode: [] for mode, _, _, _ in CONFIGURACIONES}
    counts = None
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        archivos = {}
        referencia = None
        for mode, name, hilos, bloques in CONFIGURACIONES:
            csv_path = Path(tmp) / f"{mode}.csv"
            info = ejecutar(mode, entrada, csv_path, args.epsilon, args.min_samples, hilos, bloques)
            result = np.loadtxt(csv_path, delimiter=",", ndmin=2)
            if info["n"] != len(puntos) or result.shape != (len(puntos), 3):
                raise ValueError("La salida no contiene todos los puntos de entrada.")
            np.testing.assert_array_equal(result[:, :2], puntos)
            if not np.isin(result[:, 2], [0, 1, 2]).all():
                raise ValueError("Encontré etiquetas fuera de 0, 1 y 2.")
            observed = np.bincount(result[:, 2].astype(int), minlength=3).tolist()
            if observed != [info["noise"], info["core"], info["border"]]:
                raise ValueError("Los conteos JSON no coinciden con el CSV.")
            if referencia is None:
                referencia = csv_path.read_bytes()
                counts = observed
            elif csv_path.read_bytes() != referencia:
                raise ValueError(f"{name} produce una clasificación distinta de P0.")
            archivos[mode] = csv_path
            print(f"{name}: calentamiento descartado y clasificación comprobada.", flush=True)

        jobs = [(rep, config) for rep in range(args.repetitions) for config in CONFIGURACIONES]
        random.Random(11).shuffle(jobs)
        with (output / "raw.csv").open("w", newline="") as file:
            writer = csv.writer(file, lineterminator="\n")
            writer.writerow(["n", "mode", "threads", "k", "repeat", "seconds"])
            for index, (rep, (mode, name, hilos, bloques)) in enumerate(jobs, start=1):
                info = ejecutar(mode, entrada, "-", args.epsilon, args.min_samples, hilos, bloques)
                if (
                    info["n"] != len(puntos)
                    or [info["noise"], info["core"], info["border"]] != counts
                ):
                    raise ValueError("Una medición no conserva N o los conteos de clasificación.")
                tiempos[mode].append(info["seconds"])
                writer.writerow([len(puntos), mode, hilos, bloques, rep, info["seconds"]])
                file.flush()
                print(f"Medición {index}/{len(jobs)}: {name}", flush=True)

        if sha(entrada) != input_hash or any(
            sha(ROOT / "bin" / mode) != digest for mode, digest in binary_hashes.items()
        ):
            raise ValueError("La entrada o los ejecutables cambiaron durante la comparación.")

        summary = []
        base = statistics.mean(tiempos["serial"])
        for mode, name, hilos, bloques in CONFIGURACIONES:
            promedio = statistics.mean(tiempos[mode])
            speedup = base / promedio
            row = dict(
                n=len(puntos),
                mode=mode,
                threads=hilos,
                k=bloques,
                repetitions=args.repetitions,
                mean_seconds=promedio,
                std_seconds=statistics.stdev(tiempos[mode]) if args.repetitions > 1 else 0,
                speedup=speedup,
                efficiency=speedup / hilos,
            )
            summary.append(row)
            titulo = (
                f"{name} · N = {len(puntos):,}\n"
                f"Media: {promedio * 1000:.3f} ms · Speedup: {speedup:.3f}×"
            )
            visualizar(archivos[mode], output / f"{mode}_puntos.png", titulo=titulo)

    with (output / "summary.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=summary[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary)

    metadata = dict(
        created_at=datetime.now().astimezone().isoformat(),
        input=str(entrada),
        input_sha256=input_hash,
        n=len(puntos),
        epsilon=args.epsilon,
        min_samples=args.min_samples,
        repetitions=args.repetitions,
        seed=11,
        warmups_per_configuration=1,
        binaries=binary_hashes,
        noise=counts[0],
        core=counts[1],
        border=counts[2],
        classification_equal=True,
        measured_region="Cómputo C++; excluye lectura, escritura y gráficas",
    )
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")

    table = [
        "| Versión | Hilos | k | Media (ms) | DE (ms) | Speedup | Eficiencia |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row, (_, name, _, _) in zip(summary, CONFIGURACIONES):
        table.append(
            f"| {name} | {row['threads']} | {row['k'] or '-'} | "
            f"{row['mean_seconds'] * 1000:.3f} | {row['std_seconds'] * 1000:.3f} | "
            f"{row['speedup']:.3f}× | {row['efficiency'] * 100:.2f}% |"
        )
    description = (
        f"Comparé {len(puntos):,} puntos con epsilon={args.epsilon} y min_samples={args.min_samples}. "
        f"Descarté un calentamiento por versión y medí {args.repetitions} repeticiones por configuración. "
        "P1 y P2 produjeron clasificaciones idénticas a P0. "
        "Comparo tiempos internos de cómputo; la lectura, escritura y las gráficas quedan fuera."
    )
    report = "# Comparación para la demostración\n\n" + description + "\n\n"
    report += "\n".join(table) + "\n\n"
    report += "Speedup = media serial / media de la versión. Eficiencia = speedup / hilos.\n\n"
    report += (
        "DE es la desviación estándar muestral. Los colores representan core, borde y ruido.\n\n"
    )
    for mode, name, _, _ in CONFIGURACIONES:
        report += f"## {name}\n\n![{name}]({mode}_puntos.png)\n\n"
    (output / "resultado.md").write_text(report.rstrip() + "\n")
    print("\n" + "\n".join(table))
    print(f"\nResultados: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Comparo P0, P1 con 4 hilos y P2 con 4 hilos y 4 bloques."
    )
    parser.add_argument("entrada", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epsilon", type=float, default=0.03)
    parser.add_argument("--min-samples", type=int, default=10)
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if (
        not math.isfinite(args.epsilon)
        or args.epsilon <= 0
        or args.min_samples < 1
        or args.repetitions < 1
    ):
        parser.error(
            "epsilon debe ser positivo y finito; min-samples y repetitions, enteros positivos."
        )
    try:
        comparar(args)
    except (OSError, ValueError, AssertionError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error}\n")
