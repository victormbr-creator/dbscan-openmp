# Metodología y defensa técnica

## Datos y diagnóstico

El proyecto se encontró en Documents/DBSCAN_Proyecto; el directorio inicialmente abierto en Codex era otro repositorio. Existían `.venv`, directorios vacíos, un test OpenMP y el material del profesor. El notebook local usa `np.savetxt("data/4000_data.csv", ...)`: depende del directorio de trabajo del kernel, no de la ubicación del notebook. No hay contador de ejecución y las gráficas guardadas no prueban ejecución local. No es posible reconstruir el cwd histórico del kernel con ese archivo. No se encontró el CSV en el proyecto. Si el kernel trabaja en material_curso, la subcarpeta data no existe y savetxt falla.

El generador independiente resuelve la ruta a partir de `__file__`. Se ejecutó desde /private/tmp y verificó forma (4000,2), valores finitos e igualdad exacta después de guardar y volver a leer. Conserva make_blobs: centers=4, cluster_std=0.06, random_state=11, center_box=(0,1), inversión de columnas, valor absoluto y redondeo a tres decimales.

## Algoritmo

Para cada punto se cuentan vecinos con dx²+dy² <= epsilon², incluido él mismo. Al alcanzar min_samples se marca core y se detiene la búsqueda. Esto conserva la clasificación, aunque no obtiene el número total de vecinos. Una segunda fase busca un core vecino para cada no-core: si existe es segundo orden (borde); si no, ruido. Los bordes no propagan la condición de core. Todas las versiones aplican las mismas optimizaciones, con memoria O(N) y peor caso O(N²). No hay matriz de distancias ni caché exclusiva.

P0 ejecuta ambos recorridos secuencialmente y se compila sin OpenMP. P1 usa un equipo OpenMP con dos bucles `omp for schedule(static)` sobre puntos. Static reduce la coordinación, pero puede sufrir desequilibrio si hay regiones con búsquedas muy diferentes.

P2 reparte k bloques de índices [N*b/k,N*(b+1)/k), programados con `schedule(dynamic,1)`. Es distinta en la unidad de trabajo y su asignación: los hilos reciben bloques al terminar los anteriores. No crea subconjuntos espaciales aislados. Cada búsqueda consulta el conjunto global y no pierde vecinos entre bloques. Si k < hilos, habrá hilos sin bloque. Bloques pequeños mejoran balance pero añaden coordinación. No requiere reconciliación de etiquetas porque las búsquedas son globales.

Una condición de carrera ocurre cuando accesos simultáneos a memoria compartida, al menos uno de escritura, no están sincronizados. Aquí cada índice tiene un único escritor. Se usan bytes independientes, no vector<bool>. La barrera implícita al final del primer omp for garantiza que todos los cores están definidos antes de la fase dos. La segunda fase sólo lee ese vector y escribe su propia etiqueta. La salida se escribe al finalizar el equipo.

## Validación y precisión

Se comparan las tres clases con DBSCAN de scikit-learn, usando core_sample_indices_ y las etiquetas -1. Se fija algorithm='kd_tree'. La primera prueba con 'brute' discrepó en cinco puntos del dataset de 4000; kd_tree coincidió con las distancias directas del código. Los métodos pueden diferir por redondeo flotante cerca de epsilon; no se exige identidad entre todos los backends de sklearn ni se añadió tolerancia. Se desactiva contracción flotante con -ffp-contract=off y no se usa fast-math.

Ocho casos: profesor, duplicados, distancia epsilon exacta (representable), aislados, densos, un punto, min_samples>N y vecinos entre bloques. Cada caso prueba P0, P1 con 1 y 5 hilos y P2 con 1 y 5 hilos y k={2,4,8,16,32,64}; 120 ejecuciones en total. Se comparan coordenadas y clases punto por punto y el número efectivo de hilos.

## Medición

Apple M5, 10 procesadores lógicos y 10 físicos, 25769803776 bytes (24 GiB), arm64; macOS 26.5.2 build 25F84; Homebrew clang 23.1.3. Python de .venv; NumPy 2.5.4, scikit-learn 1.9.1, Matplotlib 3.11.2. Opciones comunes -std=c++17 -O3 -ffp-contract=off; P1/P2 añaden -fopenmp.

T={1,5,10,20}; en equipos impares se usa floor(V/2), mínimo 1, eliminando duplicados. 20 hilos implica sobresuscripción. El equipo heterogéneo, temperatura y otras cargas pueden cambiar los resultados; no se presupone aceleración lineal.

steady_clock mide asignación e inicialización de etiquetas, ambas fases, creación del equipo y sincronizaciones. Excluye lectura, conteo final de categorías, escritura y emisión JSON. Un calentamiento por configuración se descarta. Las diez repeticiones se intercalan con orden pseudoaleatorio de semilla 11. Cada proceso crea su equipo: el costo de OpenMP está incluido.

Speedup=media(P0)/media(Px), eficiencia=speedup/hilos. Se conservan datos crudos, desviación estándar, parámetros, hashes y entorno OpenMP. La estimación usa un piloto real de 20000 y escala por N² sin asumir ganancia paralela; es orientativa, no una garantía, porque la densidad y la parada temprana cambian el trabajo real. La generación y validación agregan tiempo aparte. La matriz individual reduce los tamaños a cuatro, conserva las seis particiones y todos los hilos: 116 configuraciones, 1160 mediciones, más calentamientos.

La matriz individual fue autorizada y ejecutada. La auditoría posterior verificó todas las configuraciones contra P0 en cada dataset; detalles y hashes de salida en validation.csv. Los tiempos de auditoría quedan fuera de la evaluación. Las gráficas separan paneles por N o por hilos, conservando todas las configuraciones.
