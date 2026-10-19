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
// comprueba si el compilador tiene habilitado OpenMP.
#ifdef _OPENMP
// importa las funciones de OpenMP, como omp_get_num_threads().
#include <omp.h>
#endif
// define lo que es un punto en 2D, con coordenadas x e y.

struct Point {
    double x, y;
};
// Esta función recibe la ruta de un archivo y devuelve un vector de puntos.

inline std::vector<Point> read_csv(const std::string &path) {
    // ifstream abre un archivo para lectura. Si no puede abrirlo, se genera un error.
    std::ifstream f(path);
    if (!f)
        throw std::runtime_error("No se puede abrir: " + path);
    /* p: almacenará todos los puntos.
    ine: guardará temporalmente cada línea del CSV.
    row: contará las filas.
    */
    std::vector<Point> p;
    std::string line;
    size_t row = 0;
    // getline lee una línea completa.
    while (std::getline(f, line)) {
        // istringstream permite interpretar el contenido de esa línea como datos.
        ++row;
        std::istringstream s(line);
        Point a;
        char comma;
        // Extrae los valores de x e y, separados por una coma. Si no se puede extraer
        // correctamente, o si la coma no está presente, o si los valores no son finitos, se lanza
        // un error.
        if (!(s >> a.x >> comma >> a.y) || comma != ',' || !std::isfinite(a.x) ||
            !std::isfinite(a.y))
            throw std::runtime_error("CSV inválido, fila " + std::to_string(row));
        // Descarta espacios en blanco finales y comprueba que no haya contenido adicional.
        s >> std::ws;
        if (!s.eof())
            throw std::runtime_error("Columnas extra");
        // Agrega el punto leído al vector de puntos.
        p.push_back(a);
    }
    if (p.empty())
        throw std::runtime_error("CSV vacío");
    return p;
}
// Esta función coordina la ejecución de DBSCAN.
/*
argc    Número de argumentos recibidos
argv	Arreglo con los argumentos escritos
mode	Selecciona la versión serial, P1 o P2
*/
inline int run(int argc, char **argv, int mode) {
    try {
        // Comprueba que el número de argumentos sea correcto. Si no lo es, lanza un error con el
        // mensaje de uso.
        if (argc < 5 || argc > 7)
            throw std::runtime_error(
                "Uso: programa entrada.csv salida.csv|- epsilon min_samples [hilos] [k]");
        // Función lambda que convierte una cadena a un número de punto flotante. Si la conversión
        // falla o el número no es finito, lanza un error.
        auto number = [](const char *s) {
            size_t n;
            double v = std::stod(s, &n);
            if (s[n] || !std::isfinite(v))
                throw std::runtime_error("Número inválido");
            return v;
        };
        // Función lambda que convierte una cadena a un entero positivo. Si el número no es un
        // entero positivo válido, lanza un error.
        auto integer = [&](const char *s) {
            double v = number(s);
            if (v < 1 || v > 2147483647 || std::floor(v) != v)
                throw std::runtime_error("Entero positivo requerido");
            return int(v);
        };
        // Convierte los argumentos de epsilon y min_samples a sus respectivos tipos. Si alguno de
        // ellos es inválido, se lanza un error.
        double eps = number(argv[3]);
        int min_samples = integer(argv[4]);
        /*
        eps: radio máximo para considerar que dos puntos son vecinos.
        min_samples: número mínimo de puntos dentro de ese radio para considerar que un punto es
        CORE.
        */
        // threads: número de hilos a utilizar en la versión paralela. k: número de bloques en los
        // que se divide el conjunto de datos para la versión paralela 2.
        [[maybe_unused]] int threads = argc > 5 ? integer(argv[5]) : 1,
                             k = argc > 6 ? integer(argv[6]) : 2;
        // Comprueba que epsilon sea positivo y finito. Si no lo es, lanza un error.
        if (eps <= 0 || !std::isfinite(eps * eps) || eps * eps == 0)
            throw std::runtime_error("epsilon fuera de rango");
        // Lee los puntos desde el archivo CSV y almacénalos en un vector. n: número de puntos
        // leídos.
        auto p = read_csv(argv[1]);
        const long n = static_cast<long>(p.size());
        // nos ahorramos calcular el cuadrado cada iteración
        const double eps2 = eps * eps;
        // número real de hilos utilizados, inicialmente 1.
        int actual = 1;
        // registra el momento en que comienza la parte medida de la ejecución.
        auto start = std::chrono::steady_clock::now();
        // core: vector que indica si un punto es CORE (1) o no (0). labels: vector que almacena la
        // clasificación de cada punto (0 = NOISE, 1 = CORE, 2 = BORDER). first actualiza core,
        // second actualiza labels.
        std::vector<unsigned char> core(n, 0), labels(n, 0);
        // near(i)
        // comprueba si dos puntos están suficientemente cerca, utilizando la distancia euclidiana y
        // comparándola con el parámetro eps.
        auto near = [&](long i, long j) {
            double dx = p[i].x - p[j].x, dy = p[i].y - p[j].y;
            return dx * dx + dy * dy <= eps2;
        };
        /* first(i)

        auto: permite que C++ deduzca el tipo de la función lambda.
        first: nombre que utilizamos para llamarla.
        [&]: permite acceder por referencia a variables del contexto, como core, p, n y min_samples.
        (long i): recibe el índice del punto que queremos analizar.

        Recibe el índice de un punto i.
        Recorre todos los puntos j del conjunto de datos.
        Utiliza near(i,j) para comprobar si están a una distancia menor o igual a eps.
        Cuenta los vecinos encontrados.
        Si alcanza min_samples, marca core[i] = 1.
        */
        auto first = [&](long i) {
            int count = 0;
            for (long j = 0; j < n; ++j)
                if (near(i, j) && ++count >= min_samples) {
                    core[i] = 1;
                    break;
                }
        };
        /* second(i)
        Revisa si el punto i ya fue identificado como CORE.
        Si es CORE, asigna labels[i] = 1.
        Si no es CORE, busca si tiene algún vecino que sí sea CORE.
        Si encuentra uno, lo clasifica como BORDER (labels[i] = 2).
        Si no encuentra ninguno, permanece como NOISE (labels[i] = 0), porque el vector se
        inicializó con ceros.
        */
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
            // Desactiva el ajuste automático del número de hilos. Así OpenMP utiliza la cantidad
            // solicitada
            omp_set_dynamic(0);

// Crea una región paralela con el número de hilos indicado. (equipo de hilos)
#pragma omp parallel num_threads(threads)
            {
// Solo un hilo ejecuta la siguiente instrucción.
// Los demás hilos continúan después.
#pragma omp single
                actual = omp_get_num_threads();

                if (mode == 1) {

// PARALELO 1: REPARTO ESTÁTICO

// Divide las iteraciones entre los hilos
// desde el principio.
//
// Ejemplo: 100 puntos y 4 hilos.
// Cada hilo recibe aproximadamente 25 puntos.
//
// Cada hilo identifica los puntos core
// que le corresponden.
#pragma omp for schedule(static)
                    for (long i = 0; i < n; ++i)
                        first(i);

// Barrera implícita:
// Todos los hilos deben terminar de identificar
// los puntos core antes de pasar a esta fase.

// Clasifica cada punto como:
// 1 = core
// 2 = border
// 0 = noise
#pragma omp for schedule(static)
                    for (long i = 0; i < n; ++i)
                        second(i);

                } else {

                    // PARALELO 2: DIVISIÓN EN K BLOQUES

                    // Dividimos los N puntos en K bloques.
                    // Cada bloque tiene un conjunto de puntos
                    // sobre los que debe trabajar.
                    //
                    // schedule(dynamic,1):
                    // Cada hilo toma un bloque disponible.
                    // Cuando termina, toma otro.
                    //
                    // Aunque cada bloque tiene puntos asignados,
                    // la búsqueda de vecinos consulta TODOS
                    // los puntos del conjunto. --> no hay problmea de

#pragma omp for schedule(dynamic, 1)
                    for (int b = 0; b < k; ++b)
                        for (long i = n * b / k; i < n * (b + 1) / k; ++i)
                            first(i);

// BARRERA IMPLÍCITA:
// Todos los hilos terminan la identificación
// de puntos core antes de continuar.
//
// Esto es importante porque second(i)
// necesita consultar el vector core completo.

// Segunda fase:
// Clasificamos los puntos de cada bloque.
// Los bloques se reparten dinámicamente.
#pragma omp for schedule(dynamic, 1)
                    for (int b = 0; b < k; ++b)
                        for (long i = n * b / k; i < n * (b + 1) / k; ++i)
                            second(i);
                }
            }
        }
#endif
        /*
        Una vez que terminamos de identificar los puntos CORE, BORDER y NOISE, necesitamos guardar
        los resultados, medir cuánto tardó el algoritmo y mostrar un resumen de la ejecución.
        */
        // Esta instrucción calcula el tiempo transcurrido desde que iniciamos la medición.
        double seconds =
            std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        // Cuenta cuántos puntos hay de cada tipo (NOISE, CORE, BORDER) y almacena los resultados en
        // el arreglo counts.
        size_t counts[3] = {0, 0, 0};
        for (auto c : labels)
            ++counts[c];
        // Este bloque crea el archivo CSV de resultados.
        if (std::string(argv[2]) != "-") {
            // Abre el archivo de salida para escritura. Si no puede abrirlo, lanza un error.
            std::ofstream out(argv[2]);
            if (!out)
                throw std::runtime_error("No se puede escribir salida");
            // Establece la precisión de los números flotantes a 17 dígitos para asegurar que se
            // guarden con suficiente detalle.
            out << std::setprecision(17);
            // Escribe cada punto y su clasificación en el archivo CSV, separando los valores con
            // comas.
            for (long i = 0; i < n; ++i)
                out << p[i].x << ',' << p[i].y << ',' << int(labels[i]) << '\n';
            // Cierra el archivo de salida y verifica si hubo algún error durante la escritura. Si
            // hubo un error, lanza una excepción.
            out.close();
            if (!out)
                throw std::runtime_error("Error escribiendo salida");
        }
        std::cout << std::setprecision(12) << "{\"n\":" << n << ",\"seconds\":" << seconds
                  << ",\"threads\":" << actual << ",\"k\":" << (mode == 2 ? k : 0)
                  << ",\"noise\":" << counts[0] << ",\"core\":" << counts[1]
                  << ",\"border\":" << counts[2] << "}\n";
        // Muestra un resumen de la ejecución en formato JSON, incluyendo el número total de puntos,
        // el tiempo transcurrido, el número de hilos utilizados, el valor de k (si corresponde), y
        // la cantidad de puntos de cada tipo (NOISE, CORE, BORDER).
        return 0;
        // Captura cualquier excepción lanzada durante la ejecución, muestra el mensaje de error en
        // la salida estándar de errores y devuelve un código de error 1.
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
