import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from generar_datos import ROOT, generar
from visualizar_puntos import visualizar

SIZES = [4000, 20000, 80000, 140000, 200000]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    hashes = {}
    for campaign in ["500407211dbe89c8", "e5129e76b440779f"]:
        meta = json.loads((ROOT / "results/benchmarks" / campaign / "metadata.json").read_text())
        hashes.update(meta["datasets"])

    destination = ROOT / "output/figuras/clasificacion"
    destination.mkdir(parents=True, exist_ok=True)
    figures = []

    with tempfile.TemporaryDirectory() as tmp:
        for n in SIZES:
            data = ROOT / "data" / f"{n}_data.csv"
            if not data.exists():
                generar(n)
            if sha(data) != hashes[str(n)]:
                raise ValueError(f"El dataset {data.name} no coincide con la campaña original.")

            outputs = {}
            for mode in ["serial", "paralelo2"]:
                output = Path(tmp) / f"{n}_{mode}.csv"

                command = [str(ROOT / "bin" / mode), str(data), str(output), "0.03", "10"]
                if mode == "paralelo2":
                    command += ["10", "64"]
                run = subprocess.run(command, check=True, capture_output=True, text=True)
                info = json.loads(run.stdout)
                if info["n"] != n or info["threads"] != (1 if mode == "serial" else 10):
                    raise ValueError("La ejecución no coincide con la configuración solicitada.")
                outputs[mode] = output

            if outputs["serial"].read_bytes() != outputs["paralelo2"].read_bytes():
                raise ValueError(f"Las clasificaciones P0 y P2 difieren para N={n}.")
            name = f"{n}_puntos.png"
            visualizar(outputs["paralelo2"], destination / name)

            figures.append(
                {
                    "n": n,
                    "core": info["core"],
                    "border": info["border"],
                    "noise": info["noise"],
                    "image": name,
                    "image_sha256": sha(destination / name),
                    "dataset_sha256": hashes[str(n)],
                    "classification_sha256": sha(outputs["paralelo2"]),
                    "matches_serial": True,
                }
            )
            print(f"N={n}: imagen generada y clasificación idéntica a P0.", flush=True)

    manifest = {
        "epsilon": 0.03,
        "min_samples": 10,
        "mode": "paralelo2",
        "threads": 10,
        "k": 64,
        "binaries": {mode: sha(ROOT / "bin" / mode) for mode in ["serial", "paralelo2"]},
        "figures": figures,
    }
    (destination / "resumen.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
