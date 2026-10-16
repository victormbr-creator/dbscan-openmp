
#include <iostream>
#include <omp.h>

int main() {

    // Crear una región paralela con cuatro hilos.
    #pragma omp parallel num_threads(4)
    {
        int id = omp_get_thread_num();

        // Evitar que los mensajes se mezclen.
        #pragma omp critical
        {
            std::cout << "Hola desde hilo "
                      << id << std::endl;
        }
    }

    return 0;
}

