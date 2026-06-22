# SUDOKU RELOADED

> *"Desafortunadamente, nadie te puede decir qué es Matrix. Tienes que verlo por ti mismo."*

![Sudoku Reloaded Banner](banner_animated.gif)

Proceso completa de visión computacional que detecta, lee y resuelve sudokus a partir de una fotografía. En este proyecto se combina la detección de objetos, el reconocimiento óptico de caracteres con entrenamiento de redes neuronales, resolución del problema a través de redes convolucionales y backtracking. Todo ello envuelto en una app temática basada en la saga " The Matrix".

---

## Estructura del proyecto

```
sudoku_reloaded/
├── README.md
├── app/
│   └── app_matrix_doble_solucion.py
├── cuadernos/
│   ├── 01_entrenamiento_YOLO.ipynb
│   ├── 02_entrenamiento_numeros.ipynb
│   ├── 03_entrenamiento_solucion_CNN.ipynb
│   └── 04_flujo_sudoku.ipynb
├── img_pruebas/
│   └── (imágenes de sudokus para probar la app)
└── modelos/
    ├── yolo.pt
    ├── modelo_ocr.keras
    └── modelo_sudoku_mejor.keras
```

---

## El pipeline completo

```
📷 Foto
   ↓
🎯 YOLO          → detecta y recorta el tablero en la imagen
   ↓
📐 Perspectiva   → corrige la distorsión geométrica (homografía)
   ↓
🔬 Morfología    → elimina las líneas de la cuadrícula
   ↓
✂️  Segmentación → divide en 81 celdas individuales
   ↓
🔢 CNN OCR       → clasifica cada celda como dígito 0-9
   ↓
🧠 Red neuronal  → resuelve los 81 valores de golpe (inferencia directa)
⚙️  Backtracking → resuelve por fuerza bruta garantizada
   ↓
📊 Comparativa   → métricas de acierto, tiempo y fiabilidad
```

---

## Los tres modelos

| Modelo | Función | Entrada | Salida |
|--------|---------|---------|--------|
| `yolo.pt` | Detecta el recuadro del sudoku en la foto | Imagen completa | Bounding box (x1,y1,x2,y2) |
| `modelo_ocr.keras` | Lee el dígito de cada celda | Celda 28×28 px gris | Clase 0-9 |
| `modelo_sudoku_mejor.keras` | Resuelve el puzzle completo | Vector 81 valores normalizados /9 | (81,9) softmax → argmax+1 |

---

## Proceso de desarrollo

### Fase 1 — Detección del tablero

El primer reto fue localizar el tablero en una fotografía real: ángulos, iluminación variable, bordes de colores (cuadernos con marco azul), perspectiva. Se entrenó un modelo YOLO con imágenes de sudokus en distintas condiciones para obtener el bounding box del tablero.

Tras el recorte, la corrección de perspectiva usa **umbral adaptativo gaussiano** (no umbral global) para detectar el contorno interior de la cuadrícula ignorando bordes de color. La homografía transforma el cuadrilátero detectado en un cuadrado de 450×450 px.

### Fase 2 — OCR con CNN propia

Se descartó EasyOCR (lento, inconsistente con dígitos tipográficos) y se entrenó una CNN específica con dígitos generados a partir de fuentes de imprenta, que es el estilo real de un sudoku impreso o de periódico — muy distinto a los manuscritos de MNIST.

El preprocesado de cada celda sigue este orden:
1. Eliminación de líneas de cuadrícula con morfología MORPH_OPEN (kernels horizontal y vertical separados)
2. Segmentación en 81 celdas con margen de 6 px para evitar residuos de líneas
3. Detección de celda vacía por contraste centro vs esquinas (heurística sin inferencia)
4. Resize a 28×28 px + CLAHE (ecualización adaptativa) + umbral Otsu sin inversión
5. Inferencia CNN: argmax sobre 10 clases, con corrección si argmax devuelve clase 0

### Fase 3 — Solver neuronal

Se entrenó una red Conv2D sobre un CSV de ~1,3 GB con 1 millón de puzzles reales. La arquitectura trata el grid 9×9 como una imagen de 1 canal y aplica 6 capas convolucionales con BatchNormalization, terminando en una capa Conv2D(9, 1×1, softmax) que produce directamente una probabilidad por cada uno de los 9 dígitos para cada celda.

Entrenamiento en Google Colab con GPU T4:
- Batch size: 256 (optimizado para GPU)
- Epochs: 30 con EarlyStopping (patience=4)
- ReduceLROnPlateau: factor 0.5, patience 2
- ModelCheckpoint: guarda solo el mejor val_accuracy
- Mejor val_accuracy obtenida: ~77,4% por celda

### Fase 4 — Backtracking

Algoritmo clásico de búsqueda recursiva con retroceso. Encuentra la primera celda vacía, prueba dígitos del 1 al 9 comprobando las tres restricciones del sudoku (fila, columna, región 3×3), y retrocede si llega a un callejón sin salida. Garantiza solución al 100% si el puzzle es válido.

### Fase 5 — Comparativa

La app muestra ambas soluciones lado a lado con código de colores:
- 🟢 **Verde brillante** → pista original del puzzle
- 🔷 **Azul** → celda que la CNN acertó (coincide con backtracking)
- 🔴 **Rojo** → celda que la CNN falló
- 🟡 **Ámbar** → celda resuelta por backtracking

La tabla de métricas compara celdas correctas, tiempo en ms y garantía de solución.

---

## La app — SUDOKU RELOADED

Interfaz Streamlit temática de Matrix con flujo de 5 fases activadas por botones secuenciales.

### Instalación

```bash
pip install streamlit ultralytics tensorflow opencv-python-headless numpy
```

### Ejecución

```bash
# desde la raíz del proyecto
streamlit run app/app_matrix_doble_solucion.py
```

### Flujo de la app

Al subir una imagen, el sistema presenta una elección:

- **🔴 Píldora roja** → entras en la Matrix y ejecutas el pipeline completo
- **🔵 Píldora azul** → la historia termina aquí (gif de despedida y botón de nueva intrusión)

Si eliges la píldora roja, el flujo avanza fase a fase con un botón por paso:

| Fase | Botón | Proceso |
|------|-------|---------|
| Inicio | 🔴 PÍLDORA ROJA | Arranca el flujo con mensajes de hackeo animados |
| Inicio | 🔵 PÍLDORA AZUL | Gif de despedida y botón de nueva intrusión |
| 1 | LOCALIZACIÓN SUDOKU | YOLO + corrección de perspectiva |
| 2 | RECONOCIMIENTO ÓPTICO · OCR | CNN OCR — lee los 81 dígitos |
| 3 | RED NEURONAL | Solver neuronal — inferencia directa |
| 4 | BACKTRACKING | Resolución garantizada |
| 5 | ANÁLISIS COMPARATIVO | Tableros lado a lado + tabla de métricas |

> ⚠️ Si la OCR leyó mal algún dígito, el backtracking no encontrará solución válida. En ese caso aparece un aviso de error y el botón **↺ REINTENTAR CON OTRA IMAGEN**.

### Rutas de modelos

La app está en `app/` y los modelos en `modelos/` al mismo nivel. Las rutas se resuelven automáticamente:

```python
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))  # .../sudoku_reloaded/app/
MODELOS_DIR = os.path.join(BASE_DIR, "..", "modelos")     # .../sudoku_reloaded/modelos/
```

No es necesario modificar ninguna ruta si se respeta la estructura de carpetas del proyecto.

### Rutas en los cuadernos

Los notebooks se ejecutan desde `cuadernos/` y usan rutas relativas:

```python
RUTA_YOLO       = Path('../modelos/yolo.pt')
RUTA_MODELO_OCR = Path('../modelos/modelo_ocr.keras')
RUTA_SOLVER     = Path('../modelos/modelo_sudoku_mejor.keras')
RUTA_IMAGEN     = Path('../img_pruebas/024.png')
```

---

## Cuadernos

| Cuaderno | Descripción |
|----------|-------------|
| `01_entrenamiento_YOLO.ipynb` | Entrenamiento del detector de tablero con YOLO |
| `02_entrenamiento_numeros.ipynb` | Generación del dataset de dígitos tipográficos y entrenamiento de la CNN OCR |
| `03_entrenamiento_solucion_CNN.ipynb` | Entrenamiento del solver neuronal en Colab con GPU sobre el CSV de 1M de sudokus |
| `04_flujo_sudoku.ipynb` | Flujo completo comentado línea a línea: detección, OCR, solución CNN y backtracking, y comparativa |

---

## Tecnologías

- **Python 3.10**
- **OpenCV** — procesamiento de imagen, morfología, perspectiva
- **Ultralytics YOLO** — detección del tablero
- **TensorFlow / Keras** — CNN OCR y solver neuronal
- **Streamlit** — interfaz web
- **NumPy** — operaciones matriciales
- **Google Colab + GPU T4** — entrenamiento del solver
