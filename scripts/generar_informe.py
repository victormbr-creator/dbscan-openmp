"""Informe de entrega desde los CSV experimentales, sin recalcular mediciones."""
from pathlib import Path
import argparse,csv,json
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4

def main(root):
    folder=root/'results/benchmarks/e5129e76b440779f'
    rows=list(csv.DictReader((folder/'summary.csv').open()))
    checks=list(csv.DictReader((folder/'validation.csv').open()))
    out=root/'output/pdf/informe_dbscan_openmp.pdf';out.parent.mkdir(parents=True,exist_ok=True)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCustom',fontName='Helvetica-Bold',fontSize=27,leading=32,textColor=colors.HexColor('#12354A'),spaceAfter=20))
    styles.add(ParagraphStyle(name='Sub',fontSize=12,leading=17,textColor=colors.HexColor('#37637A'),spaceAfter=12))
    styles['BodyText'].fontSize=10;styles['BodyText'].leading=14;styles['BodyText'].spaceAfter=9
    styles['Heading1'].textColor=colors.HexColor('#12354A');styles['Heading1'].spaceAfter=14
    styles['Heading2'].textColor=colors.HexColor('#37637A')
    styles.add(ParagraphStyle(name='SmallCell',fontName='Helvetica',fontSize=8,leading=10))
    story=[]
    def p(text,style='BodyText'):story.append(Paragraph(text,styles[style]))
    def heading(text):p(text,'Heading1')
    def page():story.append(PageBreak())
    def table(data,widths=None):
        data=[[Paragraph(escape(str(c)),styles['SmallCell']) for c in row] for row in data]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E4EEF3')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#37637A')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#D7E0E5'))]))
        story.extend([t,Spacer(1,12)])
    def figure(name):story.append(Image(str(folder/name),width=495,height=330))
    p('CÓMPUTO PARALELO Y EN LA NUBE','Sub')
    p('DBSCAN paralelo<br/>para detección de ruido','TitleCustom')
    p('Descripción técnica y evaluación experimental individual','Sub')
    p('Proyecto: victormbr-creator/dbscan-openmp<br/>Fecha de preparación: 15 de octubre de 2026<br/>Entrega indicada: 20 de octubre de 2026')
    story.append(Spacer(1,20))
    table([['Alcance','Evidencia'],['Implementación','C++17: P0 serial, P1 OpenMP estático y P2 OpenMP por bloques dinámicos.'],['Evaluación','116 configuraciones, 10 repeticiones y 1160 mediciones válidas.'],['Resultado destacado','Speedup de 6.24 con P2, 200000 puntos, 10 hilos y 64 particiones.'],['Corrección','Ocho casos frente a scikit-learn y equivalencia contra P0 de las 116 configuraciones.']],[120,375])
    p('Se clasifican puntos core de primer orden, segundo orden (borde) y ruido. No se asignan identificadores de clúster. El presente documento conserva los resultados medidos; no presenta tiempos estimados como mediciones.')
    p('Repositorio privado: github.com/victormbr-creator/dbscan-openmp. Los CSV de respaldo están en results/benchmarks/e5129e76b440779f/.')
    page();heading('1. Algoritmo y datos')
    p('El vecindario de un punto contiene los puntos a distancia menor o igual que epsilon, incluido el propio punto. Un punto es core si su vecindario contiene al menos min_samples observaciones. Un no-core es de segundo orden si tiene algún core vecino; de lo contrario es ruido.')
    p('Fase 1: recorrer los posibles vecinos de cada punto y marcar core al alcanzar el umbral. Fase 2: para cada no-core, buscar un core vecino. Los bordes no propagan la condición de core. Las clases de salida son 0=ruido, 1=core y 2=segundo orden.')
    p('Se compara dx² + dy² &lt;= epsilon², sin raíz cuadrada. La búsqueda se detiene cuando alcanza min_samples o encuentra el primer core vecino, según la fase. Se calcula la condición de umbral, no necesariamente el conteo total. Estas optimizaciones son comunes a P0, P1 y P2.')
    p('La memoria principal es O(N); el peor caso temporal sigue siendo O(N²). No se construye una matriz de distancias. La parada temprana reduce el trabajo en los datos densos estudiados, pero no garantiza esa reducción en otros conjuntos.')
    p('Generación reproducible','Heading2')
    table([['Parámetro','Valor'],['Generador','sklearn.datasets.make_blobs'],['centers / cluster_std','4 / 0.06'],['random_state / center_box','11 / (0, 1)'],['Transformación','Inversión de columnas, valor absoluto y redondeo a 3 decimales.'],['Clasificación','epsilon=0.03; min_samples=10'],['Formato','CSV sin encabezados, dos columnas numéricas x,y.']],[155,340])
    p('scripts/generar_datos.py determina la ruta data/ desde la ubicación del script, independientemente del directorio de ejecución. Verifica forma, valores finitos e igualdad exacta al recargar. Esto resuelve la dependencia de la ruta relativa del notebook.')
    p('Estructura: src/dbscan_common.hpp comparte lectura y reglas; serial.cpp, paralelo1.cpp y paralelo2.cpp seleccionan la estrategia. Los scripts generan, validan, miden, auditan y grafican.')
    page();heading('2. Paralelización y alcance de P2')
    table([['Versión','Distribución','Consulta de vecinos'],['P0','Bucles secuenciales','Todo el conjunto'],['P1','omp for schedule(static), sobre puntos','Todo el conjunto'],['P2','omp for schedule(dynamic,1), sobre k bloques de índices','Todo el conjunto']],[48,252,195])
    p('Para cada bloque b, P2 procesa los índices desde floor(N*b/k) hasta floor(N*(b+1)/k), excluyendo el extremo final. Los intervalos cubren todos los puntos sin superposición. No se crean copias de los datos ni particiones espaciales aisladas.')
    p('Cada hilo escribe sólo los elementos correspondientes a sus puntos objetivo. Los datos se mantienen de sólo lectura. La barrera implícita al terminar la fase 1 completa el vector global core antes de comenzar la fase 2. Se utilizan bytes independientes y se evita vector&lt;bool&gt;.')
    p('Tratamiento de resultados entre particiones','Heading2')
    p('La partición reparte el trabajo, no limita el vecindario. Un punto del bloque A puede contar vecinos y consultar cores del bloque B. Las contribuciones de cada bloque quedan directamente en posiciones disjuntas de los vectores compartidos; la barrera hace disponible el estado global completo. No hay una fase independiente de fusión de clasificaciones locales ni reconciliación de clústeres.')
    p('Según el contenido de la diapositiva 11 proporcionado por el estudiante, P2 debe dividir la matriz en k partes, procesarlas en paralelo y mantener consistencia al unir sus resultados, sin exigir un algoritmo concreto de reconciliación. La partición lógica de filas y composición directa por índices exclusivos responde técnicamente a ese planteamiento; las consultas globales preservan los vecinos entre bloques. Esta justificación no equivale a una aprobación expresa del profesor. La barrera sincroniza las fases y no realiza una fusión de clasificaciones locales.')
    p('Si se exigiera una unión explícita, una alternativa sería contar vecinos locales por pares de bloques y sumar las contribuciones antes de decidir cores; después combinar mediante OR la existencia de cores vecinos en cada bloque. Esa variante cambia el trabajo y requiere nueva validación y medición. No forma parte de los resultados aquí reportados.')
    p('P1 reduce coordinación mediante reparto estático. P2 ofrece más oportunidades de balance cuando hay suficientes bloques; si k es menor que el número de hilos, sólo k hilos pueden procesar bloques simultáneamente en una fase. No se instrumentó el tiempo por hilo para atribuir causalidad definitiva a las diferencias de rendimiento.')
    page();heading('3. Entorno y diseño experimental')
    table([['Elemento','Configuración registrada'],['Equipo','Apple M5; 10 procesadores físicos y 10 lógicos; 24 GiB RAM.'],['Sistema','macOS 26.5.2, build 25F84, arm64.'],['Compilador','Homebrew clang 23.1.3; OpenMP para P1/P2.'],['Opciones comunes','-std=c++17 -O3 -Wall -Wextra -Wpedantic -ffp-contract=off'],['Paquetes Python','NumPy 2.5.4; scikit-learn 1.9.1; Matplotlib 3.11.2.'],['N individual','20000, 80000, 140000, 200000.'],['Hilos T','1, 5, 10, 20.'],['Particiones k','2, 4, 8, 16, 32, 64.']],[135,360])
    p('El perfil individual selecciona cuatro de los ocho tamaños solicitados y conserva todas las configuraciones de hilos y particiones. Por tamaño: 1 configuración P0 + 4 P1 + 24 P2 = 29. Cuatro tamaños dan 116 configuraciones; diez repeticiones dan 1160 mediciones. Los 20 hilos implican sobresuscripción sobre 10 procesadores lógicos.')
    p('steady_clock mide la inicialización de etiquetas, ambas fases, entrada al equipo OpenMP y sincronización. Excluye lectura, conteo final de categorías, escritura CSV y salida JSON. Se utiliza el mismo dataset para comparar las tres versiones.')
    p('Se descarta un calentamiento por configuración y se intercalan las diez repeticiones en orden pseudoaleatorio de semilla 11. Se conservan tiempos individuales, medias y desviaciones estándar, sin eliminar observaciones. La carga y la temperatura pueden afectar los tiempos.')
    p('Speedup = media(P0) / media(paralelo). Eficiencia = speedup / hilos. La eficiencia no equivale al porcentaje de uso de CPU. Variar hilos con N fijo evalúa escalabilidad fuerte; variar N no constituye por sí solo una prueba formal de escalabilidad débil.')
    page();heading('4. Resultados y variabilidad')
    data=[['N','Versión','T / k','Media ms','DE ms','Speedup']]
    for n in sorted({int(r['n']) for r in rows}):
        for mode in ['serial','paralelo1','paralelo2']:
            r=max((r for r in rows if int(r['n'])==n and r['mode']==mode),key=lambda r:float(r['speedup']))
            data.append([n,{'serial':'P0','paralelo1':'P1','paralelo2':'P2'}[mode],r['threads']+' / '+(r['k'] if mode=='paralelo2' else '-'),f"{float(r['mean_seconds'])*1000:.4f}",f"{float(r['std_seconds'])*1000:.4f}",f"{float(r['speedup']):.3f}"])
    table(data,[70,60,75,105,95,90])
    p('Tabla 1. Mejores medias observadas por versión y tamaño. Cada fila resume diez repeticiones. DE es desviación estándar muestral, no intervalo de confianza. La selección de la mejor configuración es descriptiva; todas las configuraciones están disponibles en summary.csv.')
    p('Ambas versiones paralelas superaron 1.5 en los cuatro tamaños evaluados. P2 con 10 hilos y 64 bloques obtuvo la mejor media en todos. Para 200000 puntos, la mejor P2 redujo el tiempo aproximadamente 12.1% frente a la mejor P1. Su eficiencia fue 62.35%; la de P1 con 20 hilos fue 27.41%.')
    p('No se garantiza que la mejor configuración se mantenga en otros equipos, distribuciones o parámetros. En estos datos, la alta densidad permite parada temprana; el crecimiento aproximadamente lineal observado no cambia la complejidad de peor caso.')
    page();heading('5. Tiempo y escalabilidad')
    figure('tiempo.png')
    p('Figura 1. Tiempo medio de cálculo en milisegundos. Cada panel fija el número de hilos de las versiones paralelas; P0 siempre usa ejecución serial. Se muestran todos los k de P2.')
    p('El tiempo aumenta con N. En P2, k=2 limita el trabajo concurrente a dos bloques y deja de aprovechar hilos adicionales. Con más bloques se observan menores tiempos. Las curvas corresponden a la clasificación y no incluyen entrada/salida.')
    p('El estudio conserva comparabilidad algorítmica: no se usa un índice espacial exclusivo de una versión, no hay matrices precalculadas y las condiciones de parada son compartidas.')
    page();heading('6. Speedup frente a hilos')
    figure('speedup_hilos.png')
    p('Figura 2. Speedup respecto a la media serial del mismo N. La línea discontinua marca el objetivo 1.5. Cada panel corresponde a un tamaño; las curvas de P2 conservan k fijo.')
    p('P2 alcanza su mejor media con 10 hilos y k=64. El paso a 20 hilos no mejora esa configuración. P1 alcanza mejores medias con 20 hilos en los tres tamaños mayores, pero el efecto no debe generalizarse: no se midieron directamente planificación, temperatura ni desequilibrio por hilo.')
    page();heading('7. Speedup frente a particiones')
    figure('speedup_particiones.png')
    p('Figura 3. Speedup de P2 al variar k; el eje horizontal muestra potencias de dos equiespaciadas. Cada curva fija el número de hilos.')
    p('Con un hilo el speedup permanece cerca de uno. Con varios hilos, k=2 mantiene una aceleración cercana a dos. Aumentar k hasta 64 mejora el rendimiento medido con 10 hilos. Esto es compatible con mejor balance de carga, aunque no demuestra por sí solo su causa.')
    page();heading('8. Validación, reproducción y uso de IA')
    p('La referencia externa usa DBSCAN de scikit-learn con algorithm=kd_tree, core_sample_indices_ para cores y labels_=-1 para ruido. Los no-core restantes son borde. Se probaron datos del profesor, duplicados, distancia epsilon exacta, aislados, densos, un punto, min_samples mayor que N y vecinos entre bloques: 120 ejecuciones en total.')
    p('La primera comparación con el backend brute mostró cinco discrepancias en 4000 puntos; kd_tree coincidió con la implementación. Se documenta sensibilidad al cálculo flotante cerca del umbral, sin tolerancias arbitrarias ni garantía de identidad entre todos los backends.')
    p('La auditoría de la matriz revisó hashes, diez repeticiones distintas por configuración, tiempos finitos y positivos, medias, speedup y eficiencia. Reejecutó las 116 configuraciones y comparó los CSV completos contra P0. Los datasets grandes se contrastaron con P0; no se afirma validación externa de cada uno con sklearn.')
    table([['N','Core','Segundo orden','Ruido']]+[[r['n'],r['core'],r['border'],r['noise']] for r in checks if r['mode']=='serial'],[120,125,125,125])
    p('Reproducción limpia','Heading2')
    repro=root/'docs/reproduccion_limpia.md'
    if not repro.exists():raise RuntimeError('Falta registrar la reproducción limpia antes de emitir el informe')
    p('Se clonó el repositorio remoto en una carpeta temporal, se creó un entorno virtual nuevo, se instalaron dependencias, se compilaron los ejecutables y se generaron los datos sin reutilizar binarios ni datasets locales. El detalle de comandos, versión y resultados está en docs/reproduccion_limpia.md. La prueba usa el mismo Mac y las dependencias de sistema instaladas; no demuestra portabilidad a otro sistema operativo.')
    p('Se utilizó Codex de OpenAI para asistir en código, automatización, pruebas y documentación. Los resultados proceden de ejecuciones reales. La modalidad individual fue confirmada por el estudiante; la revisión y comprensión para la defensa siguen siendo su responsabilidad.')
    p('Archivos de respaldo: docs/metodologia.md, docs/resultados.md, docs/uso_ia.md y results/benchmarks/e5129e76b440779f/{raw.csv,summary.csv,metadata.json,validation.csv}. El PDF fue generado por scripts/generar_informe.py a partir de esos resultados.')
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#D7E0E5'));canvas.line(50,43,545,43)
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#37637A'))
        canvas.drawString(50,30,'DBSCAN con OpenMP | Evaluación individual');canvas.drawRightString(545,30,str(doc.page))
    SimpleDocTemplate(str(out),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=45,bottomMargin=58,title='DBSCAN paralelo con OpenMP - Informe final',author='victormbr-creator').build(story,onFirstPage=footer,onLaterPages=footer)
    print(out)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);main(parser.parse_args().root)
