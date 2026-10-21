from pathlib import Path
import csv, hashlib, json, math, statistics, subprocess, tempfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def audit(folder):
    meta = json.loads((folder / "metadata.json").read_text())
    rows = list(csv.DictReader((folder / "raw.csv").open()))
    summary = list(csv.DictReader((folder / "summary.csv").open()))

    expected = {
        (n, m, t, k)
        for n in meta["sizes"]
        for m in ["serial", "paralelo1", "paralelo2"]
        for t in ([1] if m == "serial" else meta["threads"])
        for k in ([2, 4, 8, 16, 32, 64] if m == "paralelo2" else [0])
    }

    grouped = {}
    for r in rows:
        assert r["status"] == "ok", r
        key = (int(r["n"]), r["mode"], int(r["threads"]), int(r["k"]))
        rep = int(r["repeat"])
        val = float(r["seconds"])

        assert math.isfinite(val) and val > 0

        assert rep not in grouped.setdefault(key, {})
        grouped[key][rep] = val

    assert set(grouped) == expected
    assert len(summary) == len(expected)

    for r in summary:
        key = (int(r["n"]), r["mode"], int(r["threads"]), int(r["k"]))
        assert set(grouped[key]) == set(range(meta["repetitions"]))
        avg = statistics.mean(grouped[key].values())
        base = statistics.mean(grouped[(key[0], "serial", 1, 0)].values())
        assert math.isclose(avg, float(r["mean_seconds"]), rel_tol=1e-12)
        assert math.isclose(base / avg, float(r["speedup"]), rel_tol=1e-12)
        assert math.isclose(base / avg / key[2], float(r["efficiency"]), rel_tol=1e-12)

    for mode, h in meta["binaries"].items():
        assert sha(ROOT / "bin" / mode) == h
    for n, h in meta["datasets"].items():
        assert sha(ROOT / "data" / f"{n}_data.csv") == h

    checks = []

    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "result.csv"
        for n in meta["sizes"]:
            baseline = None

            for key in sorted(
                (key for key in expected if key[0] == n), key=lambda key: (key[1] != "serial", key)
            ):
                _, mode, t, k = key

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

                info = json.loads(p.stdout)
                result_hash = sha(output)
                assert info["threads"] == t and info["n"] == n

                if mode == "serial":
                    baseline = result_hash
                    data = np.loadtxt(output, delimiter=",")
                    points = np.loadtxt(ROOT / "data" / f"{n}_data.csv", delimiter=",")
                    assert data.shape == (n, 3)
                    np.testing.assert_array_equal(points, data[:, :2])
                    assert set(data[:, 2]) <= {0, 1, 2}

                assert result_hash == baseline, (key, "CSV distinto de P0")

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

            print(f"N={n}: 29 configuraciones idénticas a P0", flush=True)

    with (folder / "validation.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=checks[0].keys())
        w.writeheader()
        w.writerows(checks)
    print(
        f"Auditoría correcta: {len(rows)} mediciones, {len(summary)} configuraciones, hashes y cálculos comprobados."
    )


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("folder", type=Path)
    audit(p.parse_args().folder)
