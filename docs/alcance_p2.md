# Alcance e interpretación de P2

## Implementación que se entrega

P2 divide los índices en k bloques disjuntos: [floor(N*b/k), floor(N*(b+1)/k)). Cada bloque consulta el conjunto completo para decidir sus resultados, y escribe sólo las posiciones que le corresponden en los vectores compartidos. Los bloques se asignan dinámicamente a los hilos.

Después de la primera fase, una barrera implícita garantiza que el vector global core está completo. La segunda fase consulta ese vector global para clasificar bordes y ruido. Un punto puede tener vecinos en cualquier bloque. La unión de las contribuciones se realiza mediante posiciones disjuntas del vector compartido; no hay etiquetas locales contradictorias que reconciliar.

**No existe una fase independiente de fusión de resultados locales. La barrera sincroniza; no es un algoritmo de fusión de clústeres.** Tampoco se asignan identificadores de clúster.

## Correspondencia con la diapositiva 11

Según el contenido de la diapositiva 11 proporcionado por el estudiante, se solicitan tres implementaciones: serial, P1 sobre el conjunto completo y P2 con división en k partes procesadas en paralelo. Se pregunta cómo unir los resultados para mantener consistencia, sin imponer un algoritmo concreto de reconciliación ni exigir búsquedas exclusivamente locales.

La implementación responde a esos requisitos mediante una partición lógica de las filas en k bloques, planificación paralela dinámica y composición directa de los resultados en posiciones disjuntas del vector global. Las búsquedas globales conservan los vecinos entre bloques y la barrera asegura que todos los cores estén disponibles antes de clasificar bordes. La equivalencia contra P0 se comprobó en las 116 configuraciones experimentales.

Por ello, esta solución es técnicamente consistente con el enunciado proporcionado. No necesita copiar los bloques en matrices físicas ni generar clasificaciones locales incompletas para después corregirlas. La integración consiste en reunir contribuciones por índices exclusivos; la barrera sólo sincroniza las fases. Esta justificación no equivale a una aprobación expresa del profesor.

P1 y P2 comparten las reglas de clasificación y las búsquedas globales. Su diferencia está en la distribución: P1 reparte puntos estáticamente; P2 reparte k bloques dinámicamente. Si se añadiera el requisito de búsquedas exclusivamente locales y una fusión posterior, haría falta una variante distinta, descrita a continuación.

## Alternativa si se exige unión explícita

Para cada punto i y bloque b se podría calcular una contribución parcial c(i,b), contando sus vecinos dentro del bloque. La suma sobre b decide si i es core. Una vez conocidos todos los cores, cada bloque aporta si contiene algún core vecino de i; una reducción OR decide si i es borde. El orden debe conservar una barrera entre la decisión global de cores y la búsqueda de bordes.

Esta alternativa combina contribuciones de vecindarios, no clústeres. Cambia el trabajo realizado y puede perder parte de la ventaja de parada temprana. Necesita implementación, validación y nuevas mediciones comparables. No está implementada ni forma parte de los speedups publicados. No se sustituyó P2 sin confirmar la exigencia original.
