from pathlib import Path
import argparse, json, subprocess, tempfile
import numpy as np
from sklearn.cluster import DBSCAN

ROOT = Path(__file__).resolve().parents[1]


def validate(points, eps, minimum, modes):
    model = DBSCAN(eps=eps, min_samples=minimum, algorithm="kd_tree").fit(points)
    expected = np.where(model.labels_ == -1, 0, 2)
    expected[model.core_sample_indices_] = 1
    with tempfile.TemporaryDirectory() as tmp:
        inp = Path(tmp) / "in.csv"
        out = Path(tmp) / "out.csv"
        np.savetxt(inp, points, delimiter=",", fmt="%.17g")
        for mode in modes:
            for k in ([2, 4, 8, 16, 32, 64] if mode == "paralelo2" else [2]):
                for t in ([1] if mode == "serial" else [1, 5]):
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
                    info = json.loads(run.stdout)
                    assert info["threads"] == t, info
                    result = np.loadtxt(out, delimiter=",", ndmin=2)
                    np.testing.assert_array_equal(result[:, :2], points)
                    np.testing.assert_array_equal(result[:, 2], expected)
    return np.bincount(expected, minlength=3).tolist()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial-only", action="store_true")
    args = parser.parse_args()
    modes = ["serial"] if args.serial_only else ["serial", "paralelo1", "paralelo2"]
    cases = {
        "profesor": (np.loadtxt(ROOT / "data/4000_data.csv", delimiter=","), 0.03, 10),
        "duplicados": (np.array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [2.0, 2.0]]), 0.1, 3),
        "epsilon_borde": (
            np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [8.0, 0.0]]),
            1.0,
            4,
        ),
        "aislados": (np.array([[0.0, 0.0], [2.0, 0.0], [4.0, 0.0]]), 0.1, 2),
        "densos": (np.zeros((20, 2)), 0.1, 3),
        "un_punto": (np.zeros((1, 2)), 0.1, 1),
        "min_mayor_n": (np.zeros((3, 2)), 0.1, 4),
        "limites_bloques": (
            np.array([[0.0, 0.0], [8.0, 0.0], [0.5, 0.0], [9.0, 0.0], [0.0, 0.0], [1.0, 0.0]]),
            0.5,
            3,
        ),
    }
    for name, params in cases.items():
        print(name, validate(*params, modes), flush=True)
    print("VALIDACIÓN CORRECTA: clases 0=ruido, 1=core, 2=segundo orden")
