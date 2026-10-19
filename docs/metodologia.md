# Metodología

## Generación de datos y reproducibilidad

Genero los conjuntos de datos con `scripts/generar_datos.py`, utilizando `make_blobs` de scikit-learn y los parámetros del notebook del profesor: `centers=4`, `cluster_std=0.06`, `random_state=11` y `center_box=(0,1)`. Después invierto el orden de las columnas, aplico valor absoluto y redondeo las coordenadas a tres decimales. Mantengo una semilla fija para repetir la generación con las mismas versiones de las dependencias.

Guardo cada conjunto en `data/<N>_data.csv`, sin encabezado y con dos columnas numéricas correspondientes a x e y. Determino la ruta de salida a partir de la ubicación del script, por lo que no depende del directorio de ejecución. Tras guardar el archivo, lo vuelvo a leer y compruebo que contiene exactamente N filas y dos columnas, que todos los valores son finitos y que las coordenadas coinciden con las generadas.

Para cada tamaño N utilizo el mismo archivo en P0, P1 y P2. Registro las versiones de software y los hashes de los datasets para identificar los datos de la evaluación.

## Algoritmo

Para cada punto cuento vecinos con dx²+dy² <= epsilon², incluido el propio punto. Cuando alcanzo `min_samples`, marco el punto como core y detengo la búsqueda. Así determino si alcanza el umbral, aunque no obtengo necesariamente el número total de vecinos. En la segunda fase busco un core vecino para cada punto no-core: si existe, lo clasifico como segundo orden o borde; de lo contrario, lo mantengo como ruido. No permito que los bordes propaguen la condición de core.

Aplico las mismas optimizaciones en las tres versiones. Utilizo memoria O(N), sin matriz de distancias ni caché exclusiva de una versión, y conservo una complejidad temporal O(N²) en el peor caso.

En P0 ejecuto ambos recorridos secuencialmente y compilo sin OpenMP. En P1 utilizo un equipo OpenMP con dos bucles `omp for schedule(static)` sobre puntos. Elegí el reparto estático para reducir coordinación, aunque puede presentar desequilibrio cuando los puntos requieren búsquedas de distinta duración.

En P2 reparto k bloques de índices [floor(N*b/k),floor(N*(b+1)/k)) mediante `schedule(dynamic,1)`. Los hilos reciben nuevos bloques conforme terminan los anteriores. Cada búsqueda consulta el conjunto global, por lo que conserva vecinos de otros bloques. Si k es menor que la cantidad de hilos, habrá hilos sin bloques que procesar. Los bloques pequeños ofrecen más oportunidades de balance a costa de coordinación adicional.

Integro los resultados mediante posiciones disjuntas de los vectores compartidos. No implemento una fusión posterior de clasificaciones locales: las búsquedas globales evitan perder vecinos y la barrera completa el estado compartido antes de la segunda fase. Justifico esta decisión frente a la diapositiva 11 en [alcance_p2.md](alcance_p2.md).

## Sincronización y condiciones de carrera

Una condición de carrera aparece cuando hay accesos simultáneos no sincronizados a la misma posición de memoria y al menos uno escribe. En mi implementación asigno un único escritor a cada índice. Utilizo bytes independientes, no `vector<bool>`, y no redimensiono los vectores durante el procesamiento paralelo.

Conservo la barrera implícita al final del primer `omp for` para garantizar que todos los cores estén definidos antes de la segunda fase. En esa fase sólo leo el vector core y escribo la etiqueta correspondiente a cada punto. Guardo la salida al finalizar la región paralela.

## Validación y precisión

Comparo las tres clases con DBSCAN de scikit-learn. Utilizo `core_sample_indices_` para identificar cores y las etiquetas -1 para identificar ruido; los no-core restantes son borde. Fijo `algorithm='kd_tree'` como referencia. En la primera prueba con `brute` observé cinco discrepancias en el dataset de 4000 puntos; con `kd_tree` obtuve coincidencia. Los métodos pueden diferir por redondeo flotante cerca de epsilon. Documenté esa diferencia y no añadí tolerancias arbitrarias ni supuse identidad entre todos los backends.

Compilo con `-ffp-contract=off` para desactivar la contracción de operaciones flotantes y no utilizo fast-math. Esta opción no convierte los cálculos en aritmética decimal exacta.

Verifiqué ocho casos: datos del profesor, duplicados, distancia epsilon exacta representable, aislados, densos, un punto, `min_samples>N` y vecinos entre bloques. Para cada caso ejecuté P0, P1 con 1 y 5 hilos y P2 con 1 y 5 hilos y k={2,4,8,16,32,64}: 120 ejecuciones. Comparé coordenadas y clases punto por punto y comprobé el número efectivo de hilos.

## Entorno de medición

Utilicé un Apple M5 con 10 procesadores lógicos y 10 físicos, 25769803776 bytes de memoria (24 GiB), arquitectura arm64 y macOS 26.5.2, build 25F84. Compilé con Homebrew clang 23.1.3. En el entorno Python utilicé NumPy 2.5.4, scikit-learn 1.9.1 y Matplotlib 3.11.2. Las opciones comunes fueron `-std=c++17 -O3 -ffp-contract=off`; para P1 y P2 añadí `-fopenmp`.

Evalué T={1,5,10,20}. Para equipos con V impar, el script calcula floor(V/2), con mínimo 1 y sin duplicados. En mi equipo, 20 hilos implican sobresuscripción. Considero que la carga del sistema y la temperatura pueden afectar el rendimiento y no supongo aceleración lineal.

## Diseño experimental y tiempos

En modalidad individual evalué N={20000,80000,140000,200000}. Para cada tamaño ejecuté una configuración P0, cuatro P1 y 24 P2, combinando los cuatro números de hilos con k={2,4,8,16,32,64}. Obtuve 29 configuraciones por tamaño, 116 en total y 1160 mediciones al repetir cada una diez veces.

Con `steady_clock` mido la asignación e inicialización de etiquetas, ambas fases, la entrada al equipo OpenMP y las sincronizaciones. Excluyo lectura, conteo final de categorías, escritura y salida JSON. Descarto un calentamiento por configuración e intercalo las diez repeticiones en orden pseudoaleatorio con semilla 11. Cada medición utiliza un proceso nuevo e incluye el costo de entrada al equipo OpenMP.

Calculo speedup=media(P0)/media(Px) y eficiencia=speedup/hilos. Conservo tiempos crudos, desviaciones estándar, parámetros, hashes y variables de entorno OpenMP. Antes de ejecutar la matriz estimo su duración con un piloto de 20000 puntos y escalamiento N² sin asumir ganancia paralela. Trato esa estimación como orientativa: la densidad y la parada temprana cambian el trabajo real, y la generación y validación agregan tiempo aparte.

Después de la campaña audité todas las configuraciones contra P0 en cada dataset. Registro los detalles y hashes de salida en `validation.csv`. Excluyo esas ejecuciones de auditoría de los tiempos experimentales y presento gráficas por tamaño o número de hilos, conservando todas las configuraciones.
