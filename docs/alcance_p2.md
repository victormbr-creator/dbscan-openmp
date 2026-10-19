# Alcance e interpretación de P2

## Implementación

En P2 divido los índices en k bloques disjuntos: [floor(N*b/k),floor(N*(b+1)/k)). Cada bloque consulta el conjunto completo para decidir sus resultados y escribe únicamente las posiciones que le corresponden en los vectores compartidos. Asigno los bloques dinámicamente a los hilos mediante OpenMP.

Después de la primera fase conservo una barrera implícita para garantizar que el vector global core esté completo. En la segunda fase consulto ese vector para clasificar bordes y ruido. Un punto puede tener vecinos en cualquier bloque. Integro las contribuciones mediante posiciones disjuntas del vector compartido, sin generar etiquetas locales contradictorias.

No implemento una fase independiente de fusión de resultados locales. La barrera sincroniza las fases; no es un algoritmo de fusión de clústeres. Tampoco asigno identificadores de clúster.

## Correspondencia con la diapositiva 11

Interpreto la diapositiva 11 como el requisito de desarrollar tres implementaciones: una serial, P1 sobre el conjunto completo y P2 con división en k partes procesadas en paralelo. La pregunta sobre cómo unir los resultados para mantener consistencia no impone un algoritmo concreto de reconciliación ni exige búsquedas exclusivamente locales.

Respondo a ese planteamiento mediante partición lógica de filas, planificación dinámica y composición directa de los resultados por índices exclusivos. Las consultas globales conservan los vecinos entre bloques y la barrera asegura que todos los cores estén disponibles antes de clasificar bordes. Comprobé equivalencia contra P0 en las 116 configuraciones experimentales.

Por ello considero que mi solución es técnicamente consistente con el enunciado. No necesito copiar los bloques en matrices físicas ni generar clasificaciones locales incompletas para corregirlas después. Presento esta explicación como mi justificación técnica, no como una aprobación expresa del profesor.

En P1 y P2 conservo las mismas reglas de clasificación y consultas globales. Cambio la distribución del trabajo: P1 reparte puntos estáticamente y P2 reparte k bloques dinámicamente. Si se añadiera un requisito de búsquedas exclusivamente locales y fusión posterior, necesitaría una variante distinta.

## Alternativa con unión explícita

Como alternativa podría calcular, para cada punto i y bloque b, una contribución c(i,b) que cuente sus vecinos en ese bloque. Sumaría las contribuciones para decidir si i es core. Con todos los cores conocidos, cada bloque aportaría si contiene algún core vecino de i; combinaría esas respuestas mediante OR para decidir borde o ruido. Mantendría una barrera entre la decisión global de cores y la búsqueda de bordes.

Esta alternativa combina contribuciones de vecindarios, no clústeres. Cambiaría el trabajo realizado y podría reducir la ventaja de la parada temprana. No la implementé ni le atribuyo los speedups reportados; requeriría validación y nuevas mediciones comparables.
