"""Informe de entrega desde los CSV experimentales, sin recalcular mediciones."""

# Uso Path para rutas y csv para resultados. ReportLab compone el PDF con
# párrafos, tablas e imágenes. escape protege el texto de celdas frente a
# caracteres que Paragraph podría interpretar como etiquetas.
from pathlib import Path
import argparse, csv, json
from xml.sax.saxutils import escape
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4


# Genero el informe desde una campaña concreta ya guardada; aquí no ejecuto
# DBSCAN ni nuevos experimentos. root indica la carpeta principal del proyecto.
def main(root):
    # Esta ruta fija la campaña original del informe. Las corridas posteriores
    # no se incorporan automáticamente al PDF.
    folder = root / "results/benchmarks/e5129e76b440779f"
    # summary.csv aporta las métricas; validation.csv aporta las comprobaciones
    # y conteos por configuración. Los campos CSV se leen como cadenas.
    rows = list(csv.DictReader((folder / "summary.csv").open()))
    checks = list(csv.DictReader((folder / "validation.csv").open()))
    # Defino el archivo de salida y creo sus carpetas si faltan; build lo reemplaza.
    out = root / "output/pdf/informe_dbscan_openmp.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    # Parto de estilos de ReportLab y personalizo tipografía, colores y espaciado.
    # fontSize controla la letra; leading la distancia entre líneas; spaceAfter
    # el espacio tras el párrafo. Las medidas se expresan en puntos (1/72 de pulgada).
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleCustom",
            fontName="Helvetica-Bold",
            fontSize=27,
            leading=32,
            textColor=colors.HexColor("#12354A"),
            spaceAfter=20,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Sub", fontSize=12, leading=17, textColor=colors.HexColor("#37637A"), spaceAfter=12
        )
    )
    styles["BodyText"].fontSize = 10
    styles["BodyText"].leading = 14
    styles["BodyText"].spaceAfter = 9
    styles["Heading1"].textColor = colors.HexColor("#12354A")
    styles["Heading1"].spaceAfter = 14
    styles["Heading2"].textColor = colors.HexColor("#37637A")
    styles.add(ParagraphStyle(name="SmallCell", fontName="Helvetica", fontSize=8, leading=10))
    # story es una lista ordenada de elementos de maquetación; ReportLab
    # los distribuye en las páginas al llamar a build al final.
    story = []

    # Este auxiliar agrega un párrafo con el estilo indicado o BodyText por defecto.
    # Paragraph interpreta etiquetas simples como <br/> para saltos de línea.
    def p(text, style="BodyText"):
        story.append(Paragraph(text, styles[style]))

    # Reutilizo p para agregar un encabezado principal.
    def heading(text):
        p(text, "Heading1")

    # Inserto un salto de página explícito para separar secciones.
    def page():
        story.append(PageBreak())

    # Convierto cada celda a texto y escapo caracteres especiales. La comprensión
    # anidada recorre filas y celdas; Paragraph permite ajustar el texto al ancho.
    def table(data, widths=None):
        data = [[Paragraph(escape(str(c)), styles["SmallCell"]) for c in row] for row in data]
        # widths fija anchos de columnas; repeatRows=1 repite el encabezado si la tabla
        # ocupa varias páginas. En TableStyle las coordenadas son (columna,fila);
        # -1 significa la última columna o fila.
        t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4EEF3")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#37637A")),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#D7E0E5")),
                ]
            )
        )
        # extend agrega dos elementos: la tabla y un espacio vertical de 12 puntos.
        story.extend([t, Spacer(1, 12)])

    # Incorporo un PNG existente de la campaña con tamaño fijo; no genero
    # las gráficas aquí. Esos archivos los produce graficas.py.
    def figure(name):
        story.append(Image(str(folder / name), width=495, height=330))

    # Portada: agrego título, fecha, alcance y resumen. Gran parte de la narrativa
    # y algunos resultados destacados son texto fijo revisado para esta campaña;
    # no se actualizan solos al cambiar los CSV.
    p("CÓMPUTO PARALELO Y EN LA NUBE", "Sub")
    p("DBSCAN paralelo<br/>para detección de ruido", "TitleCustom")
    p("Descripción técnica y evaluación experimental individual", "Sub")
    p(
        "Proyecto: victormbr-creator/dbscan-openmp<br/>Fecha de revisión: 19 de octubre de 2026<br/>Entrega indicada: 20 de octubre de 2026"
    )
    story.append(Spacer(1, 20))
    table(
        [
            ["Alcance", "Evidencia"],
            [
                "Implementación",
                "C++17: P0 serial, P1 OpenMP estático y P2 OpenMP por bloques dinámicos.",
            ],
            ["Evaluación", "116 configuraciones, 10 repeticiones y 1160 mediciones válidas."],
            [
                "Resultado destacado",
                "Speedup de 6.24 con P2, 200000 puntos, 10 hilos y 64 particiones.",
            ],
            [
                "Corrección",
                "Ocho casos frente a scikit-learn y equivalencia contra P0 de las 116 configuraciones.",
            ],
        ],
        [120, 375],
    )
    p(
        "En mi proyecto clasifico puntos core de primer orden, segundo orden (borde) y ruido, sin asignar identificadores de clúster. En este informe reporto las mediciones de la campaña del 15 de octubre de 2026, sin mezclarlas con ejecuciones posteriores ni presentar estimaciones como mediciones."
    )
    p(
        "Repositorio privado: github.com/victormbr-creator/dbscan-openmp. Los CSV de respaldo están en results/benchmarks/e5129e76b440779f/."
    )
    page()
    # Sección 1: explico clasificación, complejidad y parámetros del generador.
    # Las llamadas p/table agregan contenido; no ejecutan el algoritmo descrito.
    heading("1. Algoritmo y datos")
    p(
        "El vecindario de un punto contiene los puntos a distancia menor o igual que epsilon, incluido el propio punto. Un punto es core si su vecindario contiene al menos min_samples observaciones. Un no-core es de segundo orden si tiene algún core vecino; de lo contrario es ruido."
    )
    p(
        "En la fase 1 recorro los posibles vecinos de cada punto y lo marco como core al alcanzar el umbral. En la fase 2 busco un core vecino para cada no-core. No permito que los bordes propaguen la condición de core. Utilizo las clases 0=ruido, 1=core y 2=segundo orden."
    )
    p(
        "Comparo dx² + dy² &lt;= epsilon², sin calcular raíz cuadrada. Detengo la búsqueda cuando alcanzo min_samples o encuentro el primer core vecino, según la fase. Determino la condición de umbral, no necesariamente el conteo total. Aplico estas optimizaciones en P0, P1 y P2."
    )
    p(
        "Utilizo memoria O(N) y conservo un peor caso temporal O(N²), sin construir una matriz de distancias. La parada temprana reduce el trabajo en los datos densos estudiados; no generalizo esa reducción a otros conjuntos."
    )
    p("Generación reproducible", "Heading2")
    table(
        [
            ["Parámetro", "Valor"],
            ["Generador", "sklearn.datasets.make_blobs"],
            ["centers / cluster_std", "4 / 0.06"],
            ["random_state / center_box", "11 / (0, 1)"],
            ["Transformación", "Inversión de columnas, valor absoluto y redondeo a 3 decimales."],
            ["Clasificación", "epsilon=0.03; min_samples=10"],
            ["Formato", "CSV sin encabezados, dos columnas numéricas x,y."],
        ],
        [155, 340],
    )
    p(
        "Con scripts/generar_datos.py determino la ruta data/ desde la ubicación del script, independientemente del directorio de ejecución. Verifico la forma, los valores finitos y la igualdad exacta al recargar. Mantengo los parámetros y transformaciones del notebook del profesor."
    )
    p(
        "Comparto la lectura y las reglas en src/dbscan_common.hpp. Desde serial.cpp, paralelo1.cpp y paralelo2.cpp selecciono la estrategia. Utilizo scripts separados para generar, validar, medir, auditar y graficar."
    )
    page()
    # Sección 2: documento P0/P1/P2 y mi interpretación de la consistencia entre bloques.
    heading("2. Paralelización y alcance de P2")
    table(
        [
            ["Versión", "Distribución", "Consulta de vecinos"],
            ["P0", "Bucles secuenciales", "Todo el conjunto"],
            ["P1", "omp for schedule(static), sobre puntos", "Todo el conjunto"],
            ["P2", "omp for schedule(dynamic,1), sobre k bloques de índices", "Todo el conjunto"],
        ],
        [48, 252, 195],
    )
    p(
        "En P2 asigno al bloque b los índices desde floor(N*b/k) hasta floor(N*(b+1)/k), excluyendo el extremo final. Cubro todos los puntos sin superposición, sin crear copias de los datos ni particiones espaciales aisladas."
    )
    p(
        "Asigno a cada índice un único escritor y mantengo los puntos de sólo lectura. Conservo la barrera implícita al terminar la fase 1 para completar el vector global core antes de comenzar la fase 2. Utilizo bytes independientes y evito vector&lt;bool&gt;."
    )
    p("Tratamiento de resultados entre particiones", "Heading2")
    p(
        "Con la partición reparto el trabajo sin limitar el vecindario: al procesar un punto del bloque A puedo contar vecinos y consultar cores del bloque B. Integro las contribuciones directamente en posiciones disjuntas de los vectores compartidos. No implemento una fase independiente de fusión de clasificaciones locales ni reconciliación de clústeres."
    )
    p(
        "Interpreto la diapositiva 11 como el requisito de dividir la matriz en k partes, procesarlas en paralelo y mantener consistencia al unir sus resultados, sin imponer una reconciliación concreta. Respondo mediante partición lógica de filas y composición directa por índices exclusivos; con consultas globales conservo los vecinos entre bloques. Presento esta explicación como mi justificación técnica, no como una aprobación expresa del profesor. La barrera sincroniza las fases, no fusiona clasificaciones locales."
    )
    p(
        "Si necesitara una unión explícita, podría contar vecinos por pares de bloques y sumar las contribuciones antes de decidir cores; después combinaría mediante OR la existencia de cores vecinos. No implementé esa variante ni le atribuyo los resultados reportados: cambiaría el trabajo y requeriría validación y nuevas mediciones."
    )
    p(
        "En P1 elegí reparto estático para reducir coordinación. En P2 utilizo reparto dinámico por bloques para ofrecer más oportunidades de balance. Si k es menor que la cantidad de hilos, sólo k hilos pueden procesar bloques simultáneamente. No instrumenté el tiempo por hilo para atribuir causalidad definitiva a las diferencias."
    )
    page()
    # Sección 3: reporto el hardware y diseño de la campaña original. Estos textos
    # son un registro histórico, no una consulta automática al equipo actual.
    heading("3. Entorno y diseño experimental")
    table(
        [
            ["Elemento", "Configuración registrada"],
            ["Equipo", "Apple M5; 10 procesadores físicos y 10 lógicos; 24 GiB RAM."],
            ["Sistema", "macOS 26.5.2, build 25F84, arm64."],
            ["Compilador", "Homebrew clang 23.1.3; OpenMP para P1/P2."],
            ["Opciones comunes", "-std=c++17 -O3 -Wall -Wextra -Wpedantic -ffp-contract=off"],
            ["Paquetes Python", "NumPy 2.5.4; scikit-learn 1.9.1; Matplotlib 3.11.2."],
            ["N individual", "20000, 80000, 140000, 200000."],
            ["Hilos T", "1, 5, 10, 20."],
            ["Particiones k", "2, 4, 8, 16, 32, 64."],
        ],
        [135, 360],
    )
    p(
        "En mi evaluación individual seleccioné cuatro de los ocho tamaños solicitados y mantuve todos los hilos y particiones. Por tamaño ejecuté 1 configuración P0 + 4 P1 + 24 P2 = 29. Obtuve 116 configuraciones y 1160 mediciones con diez repeticiones. Al usar 20 hilos introduje sobresuscripción sobre 10 procesadores lógicos."
    )
    p(
        "Con steady_clock mido la inicialización de etiquetas, ambas fases, entrada al equipo OpenMP y sincronización. Excluyo lectura, conteo final de categorías, escritura CSV y salida JSON. Utilizo el mismo dataset para comparar las tres versiones."
    )
    p(
        "Descarto un calentamiento por configuración e intercalo las diez repeticiones en orden pseudoaleatorio de semilla 11. Conservo tiempos individuales, medias y desviaciones estándar sin eliminar observaciones. Considero que la carga y la temperatura pueden afectar los tiempos."
    )
    p(
        "Speedup = media(P0) / media(paralelo). Eficiencia = speedup / hilos. La eficiencia no equivale al porcentaje de uso de CPU. Variar hilos con N fijo evalúa escalabilidad fuerte; variar N no constituye por sí solo una prueba formal de escalabilidad débil."
    )
    page()
    # Sección 4: construyo la tabla numérica de mejores configuraciones desde summary.csv.
    heading("4. Resultados y variabilidad")
    data = [["N", "Versión", "T / k", "Media ms", "DE ms", "Speedup"]]
    # Obtengo los tamaños sin duplicados y en orden, y recorro las tres versiones.
    for n in sorted({int(r["n"]) for r in rows}):
        for mode in ["serial", "paralelo1", "paralelo2"]:
            # Filtro filas por N y versión. max con key elige el mayor speedup observado,
            # equivalente al menor tiempo medio si la referencia serial es la misma.
            # No selecciono la repetición más rápida: cada fila ya resume las repeticiones.
            r = max(
                (r for r in rows if int(r["n"]) == n and r["mode"] == mode),
                key=lambda r: float(r["speedup"]),
            )
            # Agrego versión, hilos/k, media, desviación y speedup. Multiplico segundos
            # por 1000 para expresar ms; :.4f y :.3f controlan decimales de presentación.
            data.append(
                [
                    n,
                    {"serial": "P0", "paralelo1": "P1", "paralelo2": "P2"}[mode],
                    r["threads"] + " / " + (r["k"] if mode == "paralelo2" else "-"),
                    f"{float(r['mean_seconds'])*1000:.4f}",
                    f"{float(r['std_seconds'])*1000:.4f}",
                    f"{float(r['speedup']):.3f}",
                ]
            )
    table(data, [70, 60, 75, 105, 95, 90])
    p(
        "Tabla 1. Mejores medias observadas por versión y tamaño. Cada fila resume diez repeticiones. DE es desviación estándar muestral, no intervalo de confianza. Selecciono la mejor configuración con un fin descriptivo y conservo todas las configuraciones en summary.csv."
    )
    p(
        "Ambas versiones paralelas superaron 1.5 en los cuatro tamaños evaluados. P2 con 10 hilos y 64 bloques obtuvo la mejor media en todos. Para 200000 puntos, la mejor P2 redujo el tiempo aproximadamente 12.1% frente a la mejor P1. Su eficiencia fue 62.35%; la de P1 con 20 hilos fue 27.41%."
    )
    p(
        "No generalizo la mejor configuración a otros equipos, distribuciones o parámetros. En estos datos, la alta densidad permite parada temprana; el crecimiento aproximadamente lineal observado no cambia la complejidad de peor caso."
    )
    page()
    # Secciones 5 a 7: inserto los tres PNG existentes y sus explicaciones.
    heading("5. Tiempo y escalabilidad")
    figure("tiempo.png")
    p(
        "Figura 1. Tiempo medio de cálculo en milisegundos. Cada panel fija el número de hilos de las versiones paralelas; P0 siempre usa ejecución serial. Muestro todos los k de P2."
    )
    p(
        "El tiempo aumenta con N. En P2, k=2 limita el trabajo concurrente a dos bloques y deja de aprovechar hilos adicionales. Con más bloques se observan menores tiempos. Las curvas corresponden a la clasificación y no incluyen entrada/salida."
    )
    p(
        "Mantengo comparabilidad algorítmica: no utilizo un índice espacial exclusivo de una versión ni matrices precalculadas, y comparto las condiciones de parada."
    )
    page()
    heading("6. Speedup frente a hilos")
    figure("speedup_hilos.png")
    p(
        "Figura 2. Speedup respecto a la media serial del mismo N. La línea discontinua marca el objetivo 1.5. Cada panel corresponde a un tamaño; las curvas de P2 conservan k fijo."
    )
    p(
        "P2 alcanza su mejor media con 10 hilos y k=64. El paso a 20 hilos no mejora esa configuración. P1 alcanza mejores medias con 20 hilos en los tres tamaños mayores, pero no generalizo el efecto: no medí directamente planificación, temperatura ni desequilibrio por hilo."
    )
    page()
    heading("7. Speedup frente a particiones")
    figure("speedup_particiones.png")
    p(
        "Figura 3. Speedup de P2 al variar k; el eje horizontal muestra potencias de dos equiespaciadas. Cada curva fija el número de hilos."
    )
    p(
        "Con un hilo el speedup permanece cerca de uno. Con varios hilos, k=2 mantiene una aceleración cercana a dos. Aumentar k hasta 64 mejora el rendimiento medido con 10 hilos. Esto es compatible con mejor balance de carga, aunque no demuestra por sí solo su causa."
    )
    page()
    # Sección 8: describo evidencia ya obtenida. Generar este PDF no vuelve a
    # ejecutar las validaciones ni sustituye los scripts que las realizan.
    heading("8. Validación, reproducción y uso de IA")
    p(
        "Utilizo DBSCAN de scikit-learn con algorithm=kd_tree como referencia externa, core_sample_indices_ para cores y labels_=-1 para ruido. Clasifico como borde los no-core restantes. Probé datos del profesor, duplicados, distancia epsilon exacta, aislados, densos, un punto, min_samples mayor que N y vecinos entre bloques: 120 ejecuciones."
    )
    p(
        "En la primera comparación con brute observé cinco discrepancias en 4000 puntos; kd_tree coincidió con mi implementación. Documenté la sensibilidad al cálculo flotante cerca del umbral, sin añadir tolerancias arbitrarias ni suponer identidad entre todos los backends."
    )
    p(
        "Mediante la auditoría revisé hashes, diez repeticiones distintas por configuración, tiempos finitos y positivos, medias, speedup y eficiencia. Reejecuté las 116 configuraciones y comparé los CSV completos contra P0. Contrasté los datasets grandes con P0; no afirmo validación externa de cada uno con sklearn."
    )
    # Tomo los conteos de las filas seriales de validation.csv: una por tamaño.
    # Las versiones paralelas fueron contrastadas con esa referencia en la auditoría.
    table(
        [["N", "Core", "Segundo orden", "Ruido"]]
        + [[r["n"], r["core"], r["border"], r["noise"]] for r in checks if r["mode"] == "serial"],
        [120, 125, 125, 125],
    )
    p("Reproducción limpia", "Heading2")
    # Exijo que exista el registro de reproducción antes de emitir el informe;
    # esta condición sólo comprueba su existencia, no verifica su contenido.
    repro = root / "docs/reproduccion_limpia.md"
    if not repro.exists():
        raise RuntimeError("Falta registrar la reproducción limpia antes de emitir el informe")
    p(
        "Con asistencia de Codex comprobé un clon remoto en una carpeta temporal, con un entorno virtual nuevo, dependencias instaladas y ejecutables y datos regenerados. Registro comandos, versión y resultados en docs/reproduccion_limpia.md. Utilicé el mismo Mac y las dependencias de sistema instaladas; no comprobé portabilidad a otro sistema operativo."
    )
    p(
        "Utilicé Codex de OpenAI como apoyo en código, automatización, pruebas y documentación. Reporto resultados de ejecuciones reales y declaro la asistencia de IA. Realizo el proyecto individualmente y soy responsable de revisar las decisiones y comprender el código para mi defensa."
    )
    p(
        "Archivos de respaldo: docs/metodologia.md, docs/resultados.md, docs/uso_ia.md y results/benchmarks/e5129e76b440779f/{raw.csv,summary.csv,metadata.json,validation.csv}. El PDF fue generado por scripts/generar_informe.py a partir de esos resultados."
    )

    # ReportLab llama a este auxiliar al dibujar cada página. canvas permite
    # trazar una línea y texto en coordenadas desde la esquina inferior izquierda;
    # doc.page contiene el número de página actual.
    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor("#D7E0E5"))
        canvas.line(50, 43, 545, 43)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#37637A"))
        canvas.drawString(50, 30, "DBSCAN con OpenMP | Evaluación individual")
        canvas.drawRightString(545, 30, str(doc.page))

    # Configuro tamaño A4, márgenes y metadatos del PDF. build procesa story
    # y aplica footer tanto en la primera página como en las siguientes.
    SimpleDocTemplate(
        str(out),
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=45,
        bottomMargin=58,
        title="DBSCAN paralelo con OpenMP - Informe final",
        author="victormbr-creator",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    print(out)


# --root permite indicar otra raíz; por defecto uso la carpeta padre de scripts/.
# Este bloque se ejecuta al lanzar el archivo, no al importarlo.
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    main(parser.parse_args().root)
