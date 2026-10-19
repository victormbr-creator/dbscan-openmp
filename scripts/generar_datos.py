"""Generación reproducible con los parámetros del notebook del profesor."""

from pathlib import Path
import argparse
import numpy as np
from sklearn.datasets import make_blobs

ROOT = Path(__file__).resolve().parents[1]


def generar(n):
    if n < 1:
        raise ValueError("n debe ser positivo")
    points, _ = make_blobs(
        n_samples=n, centers=4, cluster_std=0.06, random_state=11, center_box=(0, 1.0)
    )
    points = np.round(np.abs(points[:, ::-1]), 3)
    target = ROOT / "data" / f"{n}_data.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(target, points, delimiter=",", fmt="%.3f")
    loaded = np.loadtxt(target, delimiter=",", ndmin=2)
    assert loaded.shape == (n, 2) and np.isfinite(loaded).all()
    assert np.array_equal(loaded, points)
    return target


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=4000)
    args = p.parse_args()
    target = generar(args.n)
    print(target)
    print(np.loadtxt(target, delimiter=",", ndmin=2)[:5])
