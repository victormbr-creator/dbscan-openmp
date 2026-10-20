"""Audita mediciones y equivalencia punto a punto de la matriz terminada."""

# Audito una campaña guardada: reviso sus mediciones y vuelvo a ejecutar
# las configuraciones para comparar los CSV completos contra mi versión serial.
from pathlib import Path
import csv, hashlib, json, math, statistics, subprocess, tempfile
import numpy as np

# Busco binarios y datos desde la raíz del proyecto, no desde la carpeta de la terminal.
ROOT = Path(__file__).resolve().parents[1]


# Calculo una huella SHA-256 de los bytes para comprobar identidad de archivos.
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


# folder es la carpeta de una campaña con metadata.json, raw.csv y summary.csv.
# Ejecuto sin python -O, porque esa opción deshabilita los assert de comprobación.
def audit(folder):
    # JSON recupera los parámetros; DictReader carga cada fila CSV como un diccionario
    # de textos, por lo que después convierto explícitamente los campos numéricos.
    meta = json.loads((folder / "metadata.json").read_text())
    rows = list(csv.DictReader((folder / "raw.csv").open()))
    summary = list(csv.DictReader((folder / "summary.csv").open()))
    # Reconstruyo el conjunto de tuplas (N, versión, hilos, k) que debería existir.
    # P0 usa un hilo; P1/P2 usan los de metadata; sólo P2 utiliza los seis k.
    expected = {
        (n, m, t, k)
        for n in meta["sizes"]
        for m in ["serial", "paralelo1", "paralelo2"]
        for t in ([1] if m == "serial" else meta["threads"])
        for k in ([2, 4, 8, 16, 32, 64] if m == "paralelo2" else [0])
    }
    # Agrupo los tiempos por configuración y repetición. Esta auditoría estricta
    # rechaza filas fallidas y repeticiones duplicadas, aunque el ejecutor pueda
    # conservar intentos fallidos al reanudar una campaña.
    grouped = {}
    for r in rows:
        assert r["status"] == "ok", r
        key = (int(r["n"]), r["mode"], int(r["threads"]), int(r["k"]))
        rep = int(r["repeat"])
        val = float(r["seconds"])
        # Rechazo NaN, infinito y tiempos no positivos.
        assert math.isfinite(val) and val > 0
        # setdefault crea el grupo si falta; exijo que cada repetición aparezca una sola vez.
        assert rep not in grouped.setdefault(key, {})
        grouped[key][rep] = val
    # Comparo las configuraciones presentes con las esperadas y el número de filas
    # del resumen. Estas comprobaciones no sustituyen la validación punto a punto.
    assert set(grouped) == expected
    assert len(summary) == len(expected)
    # Exijo los índices de repetición 0..repetitions-1 y recalculo media, speedup
    # y eficiencia. math.isclose admite error relativo 1e-12 al comparar decimales;
    # esta tolerancia es para métricas, no para las clases ni el radio epsilon.
    for r in summary:
        key = (int(r["n"]), r["mode"], int(r["threads"]), int(r["k"]))
        assert set(grouped[key]) == set(range(meta["repetitions"]))
        avg = statistics.mean(grouped[key].values())
        base = statistics.mean(grouped[(key[0], "serial", 1, 0)].values())
        assert math.isclose(avg, float(r["mean_seconds"]), rel_tol=1e-12)
        assert math.isclose(base / avg, float(r["speedup"]), rel_tol=1e-12)
        assert math.isclose(base / avg / key[2], float(r["efficiency"]), rel_tol=1e-12)
    # Exijo los mismos bytes de binarios y datasets registrados. Una recompilación
    # que cambie el binario puede fallar aquí aunque clasifique igual; no altero
    # los hashes históricos para hacer pasar la comprobación.
    for mode, h in meta["binaries"].items():
        assert sha(ROOT / "bin" / mode) == h
    for n, h in meta["datasets"].items():
        assert sha(ROOT / "data" / f"{n}_data.csv") == h
    # Acumulo una evidencia de equivalencia por configuración, además de revisar tiempos.
    checks = []
    # Reutilizo un CSV temporal de salida; with elimina la carpeta al terminar.
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "result.csv"
        for n in meta["sizes"]:
            baseline = None
            # Filtro por tamaño y ordeno con P0 primero. En la clave de ordenación,
            # False (serial) precede a True; así ya tengo referencia al ejecutar P1/P2.
            for key in sorted(
                (key for key in expected if key[0] == n), key=lambda key: (key[1] != "serial", key)
            ):
                # Descarto con _ el N ya disponible en el bucle exterior.
                _, mode, t, k = key
                # Reejecuto una vez cada configuración, esta vez escribiendo x,y,clase.
                # check=True interrumpe si el programa falla. max(1,k) adapta el k=0 de registro
                # a la interfaz C++; las versiones que no usan particiones ignoran ese argumento.
                p = subprocess.run(
                    [
                        str(ROOT / "bin" / mode),
                        str(ROOT / "data" / f"{n}_data.csv"),
                        str(output),
                        str(meta["epsilon"]),
                        str(meta["min_samples"]),
                        str(t),
                        str(max(1, k)),
                    ],
                    check=True,
                    text=True,
                    capture_output=True,
                )
                # Reviso N e hilos efectivos y calculo el hash del CSV recién generado.
                info = json.loads(p.stdout)
                result_hash = sha(output)
                assert info["threads"] == t and info["n"] == n
                # El CSV serial fija la referencia: compruebo N filas, tres columnas,
                # coordenadas originales sin cambios y etiquetas dentro de {0,1,2}.
                if mode == "serial":
                    baseline = result_hash
                    data = np.loadtxt(output, delimiter=",")
                    points = np.loadtxt(ROOT / "data" / f"{n}_data.csv", delimiter=",")
                    assert data.shape == (n, 3)
                    np.testing.assert_array_equal(points, data[:, :2])
                    assert set(data[:, 2]) <= {0, 1, 2}
                # Exijo identidad del CSV completo contra P0, incluido el orden de las filas.
                # Esto demuestra equivalencia entre versiones; scikit-learn se contrasta aparte
                # en validar_resultados.py y no se ejecuta sobre cada dataset desde aquí.
                assert result_hash == baseline, (key, "CSV distinto de P0")
                # Registro configuración, hash de salida y conteos de core, borde y ruido.
                checks.append(
                    dict(
                        n=n,
                        mode=mode,
                        threads=t,
                        k=k,
                        sha256=result_hash,
                        core=info["core"],
                        border=info["border"],
                        noise=info["noise"],
                    )
                )
            # El texto 29 corresponde al equipo con cuatro cantidades de hilos (1+4+24).
            # Las comprobaciones anteriores se basan en expected, no en este mensaje fijo.
            print(f"N={n}: 29 configuraciones idénticas a P0", flush=True)
    # Escribo o reemplazo validation.csv sólo después de superar las comprobaciones.
    # fieldnames toma las claves de la primera evidencia como columnas.
    with (folder / "validation.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=checks[0].keys())
        w.writeheader()
        w.writerows(checks)
    print(
        f"Auditoría correcta: {len(rows)} mediciones, {len(summary)} configuraciones, hashes y cálculos comprobados."
    )


# Recibo la carpeta de campaña como argumento posicional y la convierto a Path.
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("folder", type=Path)
    audit(p.parse_args().folder)
