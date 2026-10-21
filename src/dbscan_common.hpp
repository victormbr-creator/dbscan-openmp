#pragma once
#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#ifdef _OPENMP
#include <omp.h>
#endif

struct Point {
    double x, y;
};

inline std::vector<Point> read_csv(const std::string &path) {
    std::ifstream f(path);
    if (!f)
        throw std::runtime_error("No se puede abrir: " + path);

    std::vector<Point> p;
    std::string line;
    size_t row = 0;

    while (std::getline(f, line)) {
        ++row;
        std::istringstream s(line);
        Point a;
        char comma;

        if (!(s >> a.x >> comma >> a.y) || comma != ',' || !std::isfinite(a.x) ||
            !std::isfinite(a.y))
            throw std::runtime_error("CSV inválido, fila " + std::to_string(row));

        s >> std::ws;
        if (!s.eof())
            throw std::runtime_error("Columnas extra");

        p.push_back(a);
    }
    if (p.empty())
        throw std::runtime_error("CSV vacío");
    return p;
}

inline int run(int argc, char **argv, int mode) {
    try {
        if (argc < 5 || argc > 7)
            throw std::runtime_error(
                "Uso: programa entrada.csv salida.csv|- epsilon min_samples [hilos] [k]");

        auto number = [](const char *s) {
            size_t n;
            double v = std::stod(s, &n);
            if (s[n] || !std::isfinite(v))
                throw std::runtime_error("Número inválido");
            return v;
        };

        auto integer = [&](const char *s) {
            double v = number(s);
            if (v < 1 || v > 2147483647 || std::floor(v) != v)
                throw std::runtime_error("Entero positivo requerido");
            return int(v);
        };

        double eps = number(argv[3]);
        int min_samples = integer(argv[4]);

        [[maybe_unused]] int threads = argc > 5 ? integer(argv[5]) : 1,
                             k = argc > 6 ? integer(argv[6]) : 2;

        if (eps <= 0 || !std::isfinite(eps * eps) || eps * eps == 0)
            throw std::runtime_error("epsilon fuera de rango");

        auto p = read_csv(argv[1]);
        const long n = static_cast<long>(p.size());

        const double eps2 = eps * eps;

        int actual = 1;

        auto start = std::chrono::steady_clock::now();

        std::vector<unsigned char> core(n, 0), labels(n, 0);

        auto near = [&](long i, long j) {
            double dx = p[i].x - p[j].x, dy = p[i].y - p[j].y;
            return dx * dx + dy * dy <= eps2;
        };

        auto first = [&](long i) {
            int count = 0;
            for (long j = 0; j < n; ++j)
                if (near(i, j) && ++count >= min_samples) {
                    core[i] = 1;
                    break;
                }
        };

        auto second = [&](long i) {
            if (core[i]) {
                labels[i] = 1;
                return;
            }
            for (long j = 0; j < n; ++j)
                if (core[j] && near(i, j)) {
                    labels[i] = 2;
                    return;
                }
        };
        if (mode == 0) {
            for (long i = 0; i < n; ++i)
                first(i);
            for (long i = 0; i < n; ++i)
                second(i);
        }

#ifdef _OPENMP
        else {
            omp_set_dynamic(0);

#pragma omp parallel num_threads(threads)
            {
#pragma omp single
                actual = omp_get_num_threads();

                if (mode == 1) {
#pragma omp for schedule(static)
                    for (long i = 0; i < n; ++i)
                        first(i);

#pragma omp for schedule(static)
                    for (long i = 0; i < n; ++i)
                        second(i);
                } else {
#pragma omp for schedule(dynamic, 1)
                    for (int b = 0; b < k; ++b)
                        for (long i = n * b / k; i < n * (b + 1) / k; ++i)
                            first(i);

#pragma omp for schedule(dynamic, 1)
                    for (int b = 0; b < k; ++b)
                        for (long i = n * b / k; i < n * (b + 1) / k; ++i)
                            second(i);
                }
            }
        }
#endif

        double seconds =
            std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();

        size_t counts[3] = {0, 0, 0};
        for (auto c : labels)
            ++counts[c];

        if (std::string(argv[2]) != "-") {
            std::ofstream out(argv[2]);
            if (!out)
                throw std::runtime_error("No se puede escribir salida");

            out << std::setprecision(17);

            for (long i = 0; i < n; ++i)
                out << p[i].x << ',' << p[i].y << ',' << int(labels[i]) << '\n';

            out.close();
            if (!out)
                throw std::runtime_error("Error escribiendo salida");
        }
        std::cout << std::setprecision(12) << "{\"n\":" << n << ",\"seconds\":" << seconds
                  << ",\"threads\":" << actual << ",\"k\":" << (mode == 2 ? k : 0)
                  << ",\"noise\":" << counts[0] << ",\"core\":" << counts[1]
                  << ",\"border\":" << counts[2] << "}\n";

        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
