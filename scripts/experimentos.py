"""Mediciones reanudables; --full sólo estima salvo --run."""

# Estas bibliotecas leen opciones/CSV/JSON, identifican archivos con hashes,
# combinan configuraciones, consultan el equipo, mezclan el orden, calculan
# estadísticas y lanzan/temporizan procesos. No implemento DBSCAN en este script.
import argparse, csv, hashlib, itertools, json, os, platform, random, statistics, subprocess, time
from pathlib import Path
# Reutilizo la raíz del proyecto y el generador; importarlo no ejecuta su bloque main.
from generar_datos import ROOT, generar

# La matriz completa tiene ocho tamaños; la modalidad individual selecciona cuatro.
# K contiene el número de bloques de P2, que es independiente del número de hilos.
N_FULL = [20000, 40000, 80000, 120000, 140000, 160000, 180000, 200000]
K = [2, 4, 8, 16, 32, 64]


# SHA-256 identifica los bytes del archivo: permite saber qué ejecutable o dataset
# usé. Un hash no mide rendimiento ni demuestra por sí solo corrección.
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# Ejecuto una versión de C++ y devuelvo su resumen JSON como diccionario.
def execute(mode, path, t, k, eps, minimum):
    # El argumento "-" pide no escribir el CSV de clasificación durante la medición.
    # La lista evita interpretar un comando de shell. check=True lanza una excepción
    # si el programa falla; text y capture_output permiten leer su salida como texto.
    r = subprocess.run(
        [str(ROOT / "bin" / mode), str(path), "-", str(eps), str(minimum), str(t), str(k)],
        capture_output=True,
        text=True,
        check=True,
    )
    # seconds es el tiempo interno medido por C++, no la duración total del proceso.
    result = json.loads(r.stdout)
    # Compruebo los hilos efectivos reportados por OpenMP, no sólo los solicitados.
    if result["threads"] != t:
        raise RuntimeError("Número efectivo de hilos incorrecto")
    return result


# Organizo la campaña sólo al ejecutar el archivo directamente.
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    # Exijo elegir exactamente una opción: --quick o --full.
    # --quick ejecuta la matriz pequeña; --full sólo estima si falta --run.
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--quick", action="store_true")
    group.add_argument("--full", action="store_true")
    # store_true convierte una bandera presente en True. --individual reduce los
    # tamaños de --full; --sizes permite indicar una lista propia y tiene prioridad.
    # --repetitions controla las mediciones por configuración (diez por defecto).
    # --force crea una carpeta nueva, no borra una corrida anterior.
    p.add_argument("--individual", action="store_true")
    p.add_argument("--sizes", nargs="+", type=int)
    p.add_argument("--repetitions", type=int, default=10)
    p.add_argument("--run", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--epsilon", type=float, default=0.03)
    p.add_argument("--min-samples", type=int, default=10)
    # argparse convierte los argumentos a sus tipos; min-samples se consulta
    # como a.min_samples. Rechazo repeticiones menores que uno.
    a = p.parse_args()
    if a.repetitions < 1:
        p.error("repetitions debe ser positivo")
    # v es la cantidad de procesadores lógicos; uso 1 si el sistema no informa el dato.
    # Pruebo 1, la mitad, v y 2*v hilos. // es división entera, set elimina duplicados
    # y sorted ordena. Con v=10 resulta [1,5,10,20]; 20 introduce sobresuscripción.
    v = os.cpu_count() or 1
    threads = sorted(set([1, max(1, v // 2), v, 2 * v]))
    # Uso primero --sizes; en su ausencia elijo quick, individual o la lista completa.
    sizes = a.sizes or (
        [4000, 20000] if a.quick else ([20000, 80000, 140000, 200000] if a.individual else N_FULL)
    )
    # any detecta si al menos uno de los tamaños solicitados es inválido.
    if any(n < 1 for n in sizes):
        p.error("sizes debe ser positivo")
    # Esta comprensión anidada genera tuplas (N, versión, hilos, k).
    # P0 usa un hilo; P1 recorre los hilos; P2 cruza hilos y bloques.
    # Registro k=0 cuando no aplica. Con cuatro cantidades de hilos obtengo
    # 1+4+4*6=29 configuraciones por tamaño: 116 con los cuatro tamaños individuales
    # y 1160 mediciones al usar diez repeticiones.
    configs = [
        (n, m, t, k)
        for n in sizes
        for m in ["serial", "paralelo1", "paralelo2"]
        for t in ([1] if m == "serial" else threads)
        for k in (K if m == "paralelo2" else [0])
    ]
    out = ROOT / "results" / "benchmarks"
    out.mkdir(parents=True, exist_ok=True)
    # Guardo hashes de los tres ejecutables. También registro variables OpenMP;
    # None indica que no estaban definidas explícitamente en el entorno.
    binaries = {m: digest(ROOT / "bin" / m) for m in ["serial", "paralelo1", "paralelo2"]}
    env = {key: os.environ.get(key) for key in ["OMP_PROC_BIND", "OMP_PLACES", "OMP_WAIT_POLICY"]}
    # Estos metadatos describen la campaña y después determinan su carpeta de reanudación.
    metadata = {
        "platform": platform.platform(),
        "cpu_count": v,
        "threads": threads,
        "sizes": sizes,
        "repetitions": a.repetitions,
        "binaries": binaries,
        "environment": env,
        "epsilon": a.epsilon,
        "min_samples": a.min_samples,
    }
    # Piloto explícito antes de permitir el conjunto completo. N² es una extrapolación conservadora, no una garantía.
    # El piloto genera 20000 puntos y ejecuta P0 una vez, incluso en modo sólo estimación.
    # perf_counter mide duración total; sample["seconds"] mide sólo el cómputo de C++.
    pilot = generar(20000)
    begin = time.perf_counter()
    sample = execute("serial", pilot, 1, 2, a.epsilon, a.min_samples)
    wall = time.perf_counter() - begin
    # Extrapolo el cómputo con (N/20000)^2 y añado el tiempo externo observado
    # (lanzamiento, lectura y salida). max evita sumar una diferencia negativa.
    # Multiplico por repeticiones+1 para incluir el calentamiento y supongo
    # cero ganancia paralela. Es una estimación, no una cota ni una medición final.
    estimate = sum(
        (sample["seconds"] * (n / 20000) ** 2 + max(0, wall - sample["seconds"]))
        * (a.repetitions + 1)
        for n, m, t, k in configs
    )
    # Muestro el número de configuraciones, el piloto y la estimación en minutos.
    # indent=2 hace legible el JSON y flush=True imprime sin esperar al final.
    print(
        json.dumps(
            {
                "configurations": len(configs),
                "measured_pilot": sample,
                "estimated_minutes_no_parallel_gain": estimate / 60,
            },
            indent=2,
        ),
        flush=True,
    )
    # SystemExit(0) termina correctamente después de estimar; no ejecuta la matriz.
    if a.full and not a.run:
        print("Sólo estimación. Para ejecutar, añadir --run después de autorizar la duración.")
        raise SystemExit(0)
    # Verificar todos los programas antes de cualquier medición registrada.
    # Uso el Python del entorno del proyecto. El validador requiere el CSV de
    # 4000 puntos previamente generado y aborta la campaña si hay discrepancias.
    subprocess.run(
        [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/validar_resultados.py")], check=True
    )
    # Genero un dataset por tamaño; las tres versiones reciben exactamente ese archivo.
    paths = {n: generar(n) for n in sizes}
    metadata["datasets"] = {n: digest(path) for n, path in paths.items()}
    # Ordeno las claves del JSON antes de obtener un identificador de 16 caracteres.
    # Los mismos metadatos reutilizan la carpeta; los hashes cubren binarios y datos,
    # pero esta firma no incluye el código de este script Python.
    signature = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()[:16]
    # Añado una marca temporal en nanosegundos para iniciar otra corrida.
    if a.force:
        signature += "_" + str(time.time_ns())
    folder = out / signature
    folder.mkdir(exist_ok=True)
    (folder / "metadata.json").write_text(json.dumps(metadata, indent=2))
    raw = folder / "raw.csv"
    # raw.csv guarda una fila por intento: configuración, repetición, tiempo y estado.
    fields = ["n", "mode", "threads", "k", "repeat", "seconds", "status", "error"]
    # Si ya hay resultados, los leo; DictReader devuelve cada fila como diccionario
    # de cadenas. Si no existe el archivo, comienzo con una lista vacía.
    rows = list(csv.DictReader(raw.open())) if raw.exists() else []
    # Identifico mediciones exitosas por (N, versión, hilos, k, repetición).
    # Las fallidas no entran aquí y pueden volver a intentarse al reanudar.
    done = {
        (int(r["n"]), r["mode"], int(r["threads"]), int(r["k"]), int(r["repeat"]))
        for r in rows
        if r["status"] == "ok"
    }
    # product cruza cada repetición con cada configuración. Mezclo el orden con
    # semilla 11 para intercalar pruebas de forma reproducible; no garantiza
    # eliminar efectos de temperatura o carga. Los programas se lanzan uno a uno.
    jobs = list(itertools.product(range(a.repetitions), configs))
    random.Random(11).shuffle(jobs)
    # Recuerdo qué configuraciones calenté en ESTA invocación; al reanudar
    # volveré a calentar las configuraciones que aún tengan mediciones pendientes.
    warmed = set()
    # El modo a agrega filas sin borrar las anteriores; newline deja al módulo CSV
    # el manejo de saltos de línea. Escribo encabezado cuando no hay filas previas.
    with raw.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not rows:
            writer.writeheader()
        # Desempaqueto el trabajo y omito con continue las repeticiones ya exitosas.
        for rep, (n, m, t, k) in jobs:
            if (n, m, t, k, rep) in done:
                continue
            # Preparo la fila antes de ejecutar para registrar también cualquier error.
            r = dict(n=n, mode=m, threads=t, k=k, repeat=rep, seconds="", status="ok", error="")
            try:
                # Descarto el tiempo de una primera ejecución de calentamiento por configuración.
                # max(1,k) convierte el k=0 de registro en un argumento positivo aceptado por C++;
                # P0/P1 lo ignoran. En P2 se conserva el k real.
                if (n, m, t, k) not in warmed:
                    execute(m, paths[n], t, max(1, k), a.epsilon, a.min_samples)
                    warmed.add((n, m, t, k))
                # Esta ejecución sí aporta un tiempo a las estadísticas; guardo sólo seconds.
                r["seconds"] = execute(m, paths[n], t, max(1, k), a.epsilon, a.min_samples)[
                    "seconds"
                ]
            # Si el proceso falla, guardo el mensaje y continúo con los demás trabajos.
            # Una fila fallida no aporta un tiempo válido al resumen.
            except Exception as e:
                r.update(status="failed", error=str(e))
            writer.writerow(r)
            # Vacío el búfer de Python después de cada fila para reducir pérdida de progreso;
            # esto no es una garantía de persistencia frente a un fallo del disco o del sistema.
            f.flush()
            rows.append(r)
    # Agrupo los tiempos exitosos por configuración y por número de repetición.
    # setdefault crea el diccionario interno si falta; una repetición ocupa una clave.
    values = {}
    for r in rows:
        if r["status"] == "ok":
            values.setdefault((int(r["n"]), r["mode"], int(r["threads"]), int(r["k"])), {})[
                int(r["repeat"])
            ] = float(r["seconds"])
    # Sólo resumo configuraciones con todas las repeticiones solicitadas.
    complete = {key: list(val.values()) for key, val in values.items() if len(val) == a.repetitions}
    # Regenero summary.csv a partir de las filas válidas; raw.csv conserva los intentos.
    with (folder / "summary.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "n",
                "mode",
                "threads",
                "k",
                "repetitions",
                "mean_seconds",
                "std_seconds",
                "speedup",
                "efficiency",
            ]
        )
        # Para cada configuración busco el serial del mismo N como referencia.
        # Speedup = media serial / media de esta configuración; eficiencia = speedup/hilos.
        # Si falta el serial completo, dejo esas métricas vacías (None).
        for key, vals in sorted(complete.items()):
            n, m, t, k = key
            base = complete.get((n, "serial", 1, 0))
            avg = statistics.mean(vals)
            speed = statistics.mean(base) / avg if base else None
            w.writerow(
                [
                    n,
                    m,
                    t,
                    k,
                    len(vals),
                    avg,
                    # stdev es desviación estándar muestral; requiere al menos dos valores.
                    # Con una sola repetición escribo 0, sin inferir ausencia real de variabilidad.
                    statistics.stdev(vals) if len(vals) > 1 else 0,
                    speed,
                    speed / t if speed else None,
                ]
            )
    print("Resultados:", folder)
    # Informo configuraciones incompletas y salgo con código 1 si queda alguna.
    # El código 0 de una ejecución completa permite automatizar este flujo.
    missing = len(configs) - len(complete)
    print("Configuraciones incompletas:", missing)
    if missing:
        raise SystemExit(1)
