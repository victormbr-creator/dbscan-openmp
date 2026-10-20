# Uso scikit-learn como referencia externa; subprocess ejecuta mis programas C++.
# JSON interpreta su resumen y tempfile evita dejar los CSV de prueba en el proyecto.
from pathlib import Path
import argparse, json, subprocess, tempfile
import numpy as np
from sklearn.cluster import DBSCAN

# Localizo la raíz desde este archivo, independientemente de la carpeta de la terminal.
ROOT = Path(__file__).resolve().parents[1]


# Recibo coordenadas, epsilon, min_samples y las versiones que quiero comprobar.
# Comparo clases punto por punto; estos ensayos verifican corrección, no rendimiento.
def validate(points, eps, minimum, modes):
    # fit calcula DBSCAN con un árbol espacial de scikit-learn. Uso kd_tree como
    # referencia fijada; mis programas C++ siguen usando búsquedas globales.
    model = DBSCAN(eps=eps, min_samples=minimum, algorithm="kd_tree").fit(points)
    # labels_ contiene identificadores de clúster y -1 para ruido, no mis clases 0/1/2.
    # Con where asigno 0 al ruido y provisionalmente 2 a los demás; después marco
    # con 1 los índices core. Así comparo ruido/core/borde, no números de clúster.
    expected = np.where(model.labels_ == -1, 0, 2)
    expected[model.core_sample_indices_] = 1
    # with crea una carpeta temporal y la elimina al salir, incluso si ocurre un error.
    with tempfile.TemporaryDirectory() as tmp:
        inp = Path(tmp) / "in.csv"
        out = Path(tmp) / "out.csv"
        # Con 17 dígitos significativos preservo la precisión de los double de las pruebas.
        np.savetxt(inp, points, delimiter=",", fmt="%.17g")
        # Pruebo serial con un hilo, P1 con 1 y 5, y P2 con esos dos números
        # de hilos y seis valores de k: 1 + 2 + 12 = 15 ejecuciones por caso.
        # El k=2 de serial/P1 sólo completa la interfaz; esas versiones no lo usan.
        for mode in modes:
            for k in ([2, 4, 8, 16, 32, 64] if mode == "paralelo2" else [2]):
                for t in ([1] if mode == "serial" else [1, 5]):
                    # Paso argumentos como lista, sin shell: ejecutable, entrada, salida, epsilon,
                    # min_samples, hilos y k. check=True detiene la validación si C++ falla;
                    # capture_output captura stdout/stderr y text=True los entrega como texto.
                    run = subprocess.run(
                        [
                            str(ROOT / "bin" / mode),
                            str(inp),
                            str(out),
                            str(eps),
                            str(minimum),
                            str(t),
                            str(k),
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    # Leo el JSON emitido por C++ y verifico que utilizó los hilos solicitados.
                    # assert lanza AssertionError si falla; ejecuto estas comprobaciones sin python -O.
                    info = json.loads(run.stdout)
                    assert info["threads"] == t, info
                    # La salida tiene x,y,clase. [:, :2] selecciona las coordenadas y [:, 2] la clase.
                    # Exijo igualdad exacta con los puntos originales y con las clases de referencia.
                    result = np.loadtxt(out, delimiter=",", ndmin=2)
                    np.testing.assert_array_equal(result[:, :2], points)
                    np.testing.assert_array_equal(result[:, 2], expected)
    # Cuento ocurrencias de 0, 1 y 2; minlength=3 incluye categorías con cero puntos.
    # tolist convierte el arreglo NumPy en una lista [ruido, core, borde].
    return np.bincount(expected, minlength=3).tolist()


# --serial-only permite comprobar sólo P0; sin esa bandera pruebo las tres versiones.
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial-only", action="store_true")
    args = parser.parse_args()
    modes = ["serial"] if args.serial_only else ["serial", "paralelo1", "paralelo2"]
    # Cada entrada guarda (puntos, epsilon, min_samples). El caso profesor requiere
    # haber generado antes data/4000_data.csv. Los otros son pequeños casos controlados.
    cases = {
        "profesor": (np.loadtxt(ROOT / "data/4000_data.csv", delimiter=","), 0.03, 10),
        # Compruebo que puntos con coordenadas iguales cuentan como observaciones distintas.
        "duplicados": (np.array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [2.0, 2.0]]), 0.1, 3),
        # Incluyo distancias exactamente iguales a epsilon para comprobar el límite inclusivo.
        "epsilon_borde": (
            np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [8.0, 0.0]]),
            1.0,
            4,
        ),
        # Sin vecinos suficientes, todos deben ser ruido.
        "aislados": (np.array([[0.0, 0.0], [2.0, 0.0], [4.0, 0.0]]), 0.1, 2),
        # Veinte puntos coincidentes permiten comprobar un conjunto formado sólo por cores.
        "densos": (np.zeros((20, 2)), 0.1, 3),
        # Con min_samples=1 el propio punto basta para ser core.
        "un_punto": (np.zeros((1, 2)), 0.1, 1),
        # Si el umbral supera el total de puntos, ninguno puede ser core.
        "min_mayor_n": (np.zeros((3, 2)), 0.1, 4),
        # Intercalo puntos cercanos y lejanos para que haya vecinos en bloques distintos.
        # También pruebo k mayor que N, que deja algunos bloques vacíos.
        "limites_bloques": (
            np.array([[0.0, 0.0], [8.0, 0.0], [0.5, 0.0], [9.0, 0.0], [0.0, 0.0], [1.0, 0.0]]),
            0.5,
            3,
        ),
    }
    # items recorre nombre y parámetros; *params desempaqueta los tres argumentos.
    # flush=True muestra cada resultado de inmediato. Ocho casos por 15 = 120 ejecuciones.
    for name, params in cases.items():
        print(name, validate(*params, modes), flush=True)
    print("VALIDACIÓN CORRECTA: clases 0=ruido, 1=core, 2=segundo orden")
