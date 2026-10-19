# Resultados del piloto (registro histórico)

Realicé el piloto registrado en results/benchmarks/500407211dbe89c8: 58 configuraciones completas, diez repeticiones cada una y 580 tiempos individuales, sin fallas. Reporto estas mediciones por separado de la matriz final.

| N | Programa | Hilos | k | Media (ms) | Speedup |
|---:|---|---:|---:|---:|---:|
|4000|P0|1|—|1.6471|1.00|
|4000|P1|10|—|0.5201|3.17|
|4000|P2|5|64|0.4605|3.58|
|20000|P0|1|—|9.2056|1.00|
|20000|P1|10|—|2.0216|4.55|
|20000|P2|10|64|1.6658|5.53|

Para P1/P2 presento las mejores medias observadas de cada N; todas las configuraciones, incluidas las menos favorables, están en summary.csv. Se trata de selección descriptiva, no garantía de repetibilidad. Con N=20000, la desviación estándar de P0 es 0.203 ms, P1 0.145 ms y P2 0.077 ms en esas configuraciones. Ambas superaron 1.5 en este piloto. El balance dinámico por bloques es una explicación plausible de la ventaja de P2, pero no medí el desequilibrio por hilo para atribuirle causalidad definitiva. Tiempos tan pequeños son sensibles al costo de lanzamiento, carga y temperatura.

Las gráficas de tiempo, speedup por hilos y por particiones están junto a summary.csv. Al realizar este piloto todavía no había ejecutado la matriz final. Posteriormente completé 116 configuraciones y 1160 mediciones; el estado vigente está en [resultados.md](resultados.md). La estimación medida con piloto serial de 20000 (8.658 ms) fue 7.78 minutos, sin asumir aceleración paralela y más preparación. Es una aproximación N² y puede variar.

## Registro de fases al cierre del piloto

1. Revisé el notebook y el entorno virtual. Con asistencia de IA preparé `scripts/generar_datos.py` y comprobé su ejecución desde otro directorio. Para 4000 puntos obtuve forma (4000,2), valores finitos e igualdad al recargar. Las primeras filas fueron (0.415,0.446), (0.470,0.007), (0.784,0.500), (0.406,0.451), (0.466,0.452).
2. Desarrollé P0 y las utilidades comunes. Compilé y comparé la salida serial con la referencia: 3829 core, 112 segundo orden y 59 ruido. Resolví una advertencia de variable no usada y documenté cinco discrepancias frente al backend brute.
3. Incorporé P1 con OpenMP. Comprobé la compilación, el número efectivo de hilos y la igualdad de clases.
4. Incorporé P2 y probé los seis valores de k en los ocho casos de validación, incluidos vecinos entre bloques.
5. Apliqué parada temprana, distancias al cuadrado y memoria O(N) en las tres versiones. En el piloto superé el objetivo 1.5, por lo que no introduje un índice espacial más complejo.
6. Automaticé experimentos y gráficas. Ejecuté `--quick` con diez repeticiones y utilicé `--full --individual` para estimar la campaña posterior. Conservé tiempos individuales, promedios, hashes y gráficas.
7. Preparé la documentación y las instrucciones de reproducción. Después del piloto ejecuté y audité la matriz individual, cuyos resultados presento en el informe final.
