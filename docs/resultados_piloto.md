# Resultados del piloto (registro histórico)

Piloto real: results/benchmarks/500407211dbe89c8. 58 configuraciones completas, diez repeticiones cada una, 580 tiempos individuales, sin fallas. No equivale a la matriz final.

| N | Programa | Hilos | k | Media (ms) | Speedup |
|---:|---|---:|---:|---:|---:|
|4000|P0|1|—|1.6471|1.00|
|4000|P1|10|—|0.5201|3.17|
|4000|P2|5|64|0.4605|3.58|
|20000|P0|1|—|9.2056|1.00|
|20000|P1|10|—|2.0216|4.55|
|20000|P2|10|64|1.6658|5.53|

Para P1/P2 se muestran las mejores medias observadas de cada N; todas las configuraciones, incluidas las menos favorables, están en summary.csv. Se trata de selección descriptiva, no garantía de repetibilidad. Con N=20000, la desviación estándar de P0 es 0.203 ms, P1 0.145 ms y P2 0.077 ms en esas configuraciones. Ambas superaron 1.5 en este piloto. El balance dinámico por bloques es una explicación plausible de la ventaja de P2, pero no se midió el desequilibrio por hilo para atribuirle causalidad definitiva. Tiempos tan pequeños son sensibles al costo de lanzamiento, carga y temperatura.

Las gráficas de tiempo, speedup por hilos y por particiones están junto a summary.csv. Al realizar este piloto todavía no se había ejecutado la matriz final. Posteriormente se completaron 116 configuraciones y 1160 mediciones; el estado vigente está en [resultados.md](resultados.md). La estimación medida con piloto serial de 20000 (8.658 ms) fue 7.78 minutos, sin asumir aceleración paralela y más preparación. Es una aproximación N² y puede variar.

## Registro de fases al cierre del piloto

1. Se inspeccionó el notebook real y el entorno virtual; se creó scripts/generar_datos.py. Ejecutado desde /private/tmp con --n 4000: forma (4000,2), igualdad exacta al recargar y valores finitos. Primeras filas: (0.415,0.446), (0.470,0.007), (0.784,0.500), (0.406,0.451), (0.466,0.452).
2. Se crearon src/serial.cpp, src/dbscan_common.hpp, Makefile y scripts/validar_resultados.py. `make bin/serial`, ejecución de P0 y validación serial: 3829 core, 112 segundo orden, 59 ruido. Se resolvió una advertencia de variable no usada y se documentó la discrepancia de cinco puntos frente al backend brute.
3. Se creó src/paralelo1.cpp; `make all` compiló OpenMP sin advertencias en la verificación final. Se comprobaron hilos efectivos y clases idénticas.
4. Se creó src/paralelo2.cpp; se probaron seis valores de k en los ocho casos, incluidas fronteras entre bloques. `scripts/validar_resultados.py` terminó correctamente.
5. Optimización común: parada al alcanzar min_samples, distancias al cuadrado, O(N) memoria. La implementación validada ya superó 1.5 en el piloto; no se justificó introducir índices espaciales más complejos.
6. Se crearon scripts/experimentos.py y scripts/graficas.py. Se ejecutó `--quick` con diez repeticiones y `--full --individual` sólo para estimación. Datos crudos, promedios, hashes y gráficas guardados.
7. README, metodología, resultados, dependencias y uso de IA preparados. En ese momento quedaba pendiente autorizar la matriz individual. Esa ejecución ya se completó y auditó; actualmente corresponde revisar el informe final y practicar la defensa técnica.
