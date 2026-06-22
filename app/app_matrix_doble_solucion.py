import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO
from tensorflow import keras
import tempfile
import os
import copy
import time
import random
import streamlit.components.v1 as components

# BASE_DIR apunta a la carpeta app/ donde vive este fichero
# los modelos están en ../modelos/ (un nivel arriba)
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MODELOS_DIR = os.path.join(BASE_DIR, "..", "modelos")

st.set_page_config(page_title="SUDOKU RELOADED", page_icon="🟢", layout="centered")

# oculto el menú, el header y el footer de streamlit
st.markdown("""
<style>
#MainMenu { visibility: hidden; }
header    { visibility: hidden; }
footer    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Lluvia de código Matrix ───────────────────────────────────
components.html("""
<script>
const doc = window.parent.document;
if (!doc.getElementById('matrix-canvas')) {
    const canvas = doc.createElement('canvas');
    canvas.id = 'matrix-canvas';
    canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:0;opacity:0.30;pointer-events:none;';
    doc.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');
    function resize(){ canvas.width = window.parent.innerWidth; canvas.height = window.parent.innerHeight; }
    resize();
    window.parent.addEventListener('resize', resize);
    const chars = '0123456789ABCDEF$+-*/<>=ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾊﾋﾌﾍﾎ'.split('');
    const fs = 16;
    let drops = Array(Math.floor(canvas.width / fs)).fill(1);
    function draw(){
        ctx.fillStyle = 'rgba(0,0,0,0.06)';
        ctx.fillRect(0,0,canvas.width,canvas.height);
        ctx.fillStyle = '#00ff41';
        ctx.font = fs + 'px monospace';
        for(let i=0;i<drops.length;i++){
            const t = chars[Math.floor(Math.random()*chars.length)];
            ctx.fillText(t, i*fs, drops[i]*fs);
            if(drops[i]*fs > canvas.height && Math.random() > 0.975) drops[i]=0;
            drops[i]++;
        }
    }
    setInterval(draw, 50);
}
</script>
""", height=0)

# ── CSS Matrix ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

.stApp { background-color: #000000; }
.main .block-container { background: transparent; position: relative; z-index: 1; }
html, body, [class*="css"] { font-family: 'Share Tech Mono', monospace; font-size: 19.55px; }

h1 {
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 2.3rem !important; color: #00ff41 !important;
    text-align: center !important;
    text-shadow: 0 0 10px #00ff41, 0 0 20px #00ff41 !important;
    letter-spacing: 6px !important; margin-bottom: 0 !important;
}
.matrix-subtitle {
    font-family: 'Share Tech Mono', monospace; font-size: 1.26rem;
    color: #00ff41; text-align: center; margin-bottom: 1.5rem;
    letter-spacing: 3px; opacity: 0.8;
}
.step-tag {
    font-family: 'Share Tech Mono', monospace; font-size: 0.86rem;
    background: #00ff41; color: #000; padding: 4px 12px;
    display: inline-block; margin-bottom: 12px; letter-spacing: 2px;
    font-weight: bold; box-shadow: 0 0 10px rgba(0,255,65,0.5);
}
.step-tag-cnn {
    font-family: 'Share Tech Mono', monospace; font-size: 0.86rem;
    background: #ffd000; color: #000; padding: 4px 12px;
    display: inline-block; margin-bottom: 12px; letter-spacing: 2px;
    font-weight: bold; box-shadow: 0 0 10px rgba(255,208,0,0.5);
}
.step-tag-compare {
    font-family: 'Share Tech Mono', monospace; font-size: 0.86rem;
    background: #00cfff; color: #000; padding: 4px 12px;
    display: inline-block; margin-bottom: 12px; letter-spacing: 2px;
    font-weight: bold; box-shadow: 0 0 10px rgba(0,207,255,0.5);
}
.sudoku-wrap { display: flex; justify-content: center; margin: 1.5rem 0; }
table.sudoku {
    border-collapse: collapse; font-family: 'Share Tech Mono', monospace;
    font-size: 20.7px; border: 2px solid #00ff41;
    box-shadow: 0 0 20px rgba(0,255,65,0.4);
    table-layout: fixed; width: 396px;
}
table.sudoku td {
    width: 44px; height: 44px; text-align: center; vertical-align: middle;
    background: #001a00; color: #00aa2e;
}
table.sudoku td.given   { color: #00ff41; background: #002200; text-shadow: 0 0 8px #00ff41; font-weight: bold; }
table.sudoku td.solved  { color: #ffd000; background: #1a1500; text-shadow: 0 0 10px #ffb000; font-weight: bold; }
table.sudoku td.cnn-ok  { color: #00cfff; background: #001a22; text-shadow: 0 0 8px #00aaff; font-weight: bold; }
table.sudoku td.cnn-err { color: #ff4444; background: #1a0000; text-shadow: 0 0 8px #ff2222; font-weight: bold; }
table.sudoku td.empty   { color: transparent; }
table.sudoku tr:nth-child(3n) td   { border-bottom: 2px solid #00ff41; }
table.sudoku tr:nth-child(3n+1) td { border-top:    2px solid #00ff41; }
table.sudoku td:nth-child(3n)      { border-right:  2px solid #00ff41; }
table.sudoku td:nth-child(3n+1)    { border-left:   2px solid #00ff41; }
table.sudoku td { border: 1px solid #004d15; }

table.compare {
    border-collapse: collapse; font-family: 'Share Tech Mono', monospace;
    font-size: 1rem; width: 100%; margin-top: 1rem; border: 1px solid #00ff41;
}
table.compare th { background: #002200; color: #00ff41; padding: 8px 12px; border: 1px solid #00ff41; letter-spacing: 1px; }
table.compare td { background: #001100; color: #00cc35; padding: 8px 12px; border: 1px solid #004d15; text-align: center; }
table.compare td.highlight { color: #ffd000; text-shadow: 0 0 8px #ffd000; }
table.compare td.green     { color: #00ff41; text-shadow: 0 0 8px #00ff41; }
table.compare td.red       { color: #ff4444; }

.win-banner {
    font-family: 'Share Tech Mono', monospace; font-size: 1.26rem;
    background: rgba(0,20,0,0.9); border: 1px solid #00ff41;
    box-shadow: 0 0 25px rgba(0,255,65,0.5); color: #00ff41;
    text-align: center; padding: 1.5rem; margin: 1rem 0;
    line-height: 2; letter-spacing: 2px; animation: glitch 3s infinite;
}
@keyframes glitch {
    0%, 95%, 100% { text-shadow: 0 0 10px #00ff41; }
    96% { text-shadow: -2px 0 #ff0000, 2px 0 #0000ff; transform: skewX(3deg); }
    97% { text-shadow:  2px 0 #ff0000,-2px 0 #0000ff; transform: skewX(-3deg); }
    98% { text-shadow: 0 0 10px #00ff41; transform: skewX(0); }
}
.stat-box {
    background: rgba(0,20,0,0.85); border: 1px solid #00ff41;
    box-shadow: 0 0 10px rgba(0,255,65,0.3); padding: 1rem; text-align: center;
}
.stat-num { font-family: 'Share Tech Mono', monospace; font-size: 1.61rem; color: #00ff41; display: block; text-shadow: 0 0 8px #00ff41; }
.stat-lbl { font-size: 0.98rem; color: #00aa2e; display: block; margin-top: 4px; letter-spacing: 1px; }
.px-divider { border: none; border-top: 1px solid #00ff41; margin: 1.5rem 0; box-shadow: 0 0 8px rgba(0,255,65,0.4); }
[data-testid="stFileUploadDropzone"] { background: rgba(0,20,0,0.8) !important; border: 2px dashed #00ff41 !important; border-radius: 4px !important; }
.stSpinner > div { border-top-color: #00ff41 !important; }
p, .stMarkdown p { color: #00cc35; }
.puntos::after { content: ''; animation: puntosanim 1.2s steps(4,end) infinite; }
@keyframes puntosanim { 0%{content:'';} 25%{content:'.';} 50%{content:'..';} 75%{content:'...';} }
.cur { animation: parpadeo 0.8s step-end infinite; }
@keyframes parpadeo { 50% { opacity: 0; } }
.upload-area { border: 2px dashed #00ff41; background: rgba(0,20,0,0.6); padding: 2rem; text-align: center; box-shadow: inset 0 0 30px rgba(0,255,65,0.08); }
.stButton > button {
    font-family: 'Share Tech Mono', monospace !important;
    background: rgba(0,20,0,0.9) !important; color: #00ff41 !important;
    border: 2px solid #00ff41 !important; border-radius: 4px !important;
    letter-spacing: 2px !important; box-shadow: 0 0 12px rgba(0,255,65,0.4) !important;
    transition: all 0.2s !important; width: 100% !important; font-size: 1.21rem !important;
}
.stButton > button:hover { background: #00ff41 !important; color: #000 !important; box-shadow: 0 0 25px rgba(0,255,65,0.8) !important; }
</style>
""", unsafe_allow_html=True)

# ── Mensajes de hacker ────────────────────────────────────────
ALUMNOS = ["Bárbara", "Ainara", "Nora", "David", "Leire", "Eduardo",
           "Raúl", "Ander", "Álex", "Juan"]

MENSAJES_DIEGO = {
    "intro": [
        "Infiltrándome en el servidor principal de The Bridge",
        "Interceptando las credenciales de Diego",
        "Accediendo al panel de control del bootcamp de Diego",
        "Hackeando el portal interno de The Bridge con credenciales de Diego",
    ],
    "deteccion": [
        "Descargando el historial de correcciones de Diego",
        "Clonando el repositorio privado de ejercicios de Diego",
        "Extrayendo los criterios secretos de evaluación de Diego",
    ],
    "ocr": [
        "Desbloqueando las redes neuronales de Diego",
        "Insertando aprobados automáticos en el sistema de Diego",
        "Borrando las penalizaciones por entrega tardía del servidor de Diego",
        "Eliminando el Weekly del próximo viernes del calendario de Luismi",
    ],
    "cnn": [
        "Entrenando una red neuronal con los patrones de corrección de Diego",
        "Prediciendo las preguntas del próximo examen de Diego",
        "Hackeando el modelo de evaluación de Diego",
        "Accediendo al proyecto secreto de Full Stack en el ordenador de Diego",
    ],
    "backtrack": [
        "Cambiando todas las notas a 10 en el expediente de Diego",
        "Subiendo los proyectos finales directamente al GitHub de Diego",
        "Desactivando el calor de la sala desde el servidor de Diego",
    ],
    "compare": [
        "Comparando mi solución con los criterios ocultos de Diego",
        "Calculando cuánto vale cada celda en la rúbrica de Diego",
        "Generando el informe perfecto para impresionar a Diego",
        "Fusionando el repo de Data Science con el de Full Stack via Diego",
    ],
}

MENSAJES_ANDREEA = {
    "intro": [
        "Infiltrándome en el servidor principal de The Bridge",
        "Interceptando las credenciales de Andreea",
        "Accediendo al panel de control del bootcamp de Andreea",
        "Hackeando el portal interno de The Bridge con credenciales de Andreea",
    ],
    "deteccion": [
        "Modificando los parámetros de entrega de ejercicios de Andreea",
        "Clonando los apuntes privados de Machine Learning de Andreea",
        "Extrayendo el solucionario secreto de Andreea",
        "Accediendo al GitHub privado de The Bridge con la cuenta de Andreea",
    ],
    "ocr": [
        "Descifrando los comentarios de corrección de Andreea",
        "Reescribiendo los criterios de evaluación del servidor de Andreea",
        "Cambiando a aptos todos los ejercicios en el ordenador de Andreea",
        "Borrando el Weekly de Luismi del portal de The Bridge",
    ],
    "cnn": [
        "Entrenando una red neuronal con el estilo de corrección de Andreea",
        "Prediciendo qué va a preguntar Andreea en la próxima clase",
        "Hackeando el modelo mental de evaluación de Andreea",
        "Accediendo al proyecto de alianza con Full Stack desde el PC de Andreea",
    ],
    "backtrack": [
        "Cambiando todas las notas a sobresaliente en el sistema de Andreea",
        "Eliminando los comentarios negativos del expediente de Andreea",
        "Captando la señal del ordenador de Andreea",
        "Instalando aire acondicionado virtual en el servidor de Andreea",
    ],
    "compare": [
        "Comparando resultados con los estándares secretos de Andreea",
        "Calculando la probabilidad de aprobado según Andreea",
        "Generando el proyecto perfecto para impresionar a Andreea",
        "Fusionando el repo de Data Science con el de Full Stack via Andreea",
    ],
}

PLANTILLAS_ALUMNOS = {
    "intro": [
        "Accediendo al servidor central de The Bridge",
        "Conectando con el portátil de {n}",
        "Rastreando la sesión de {n} en el portal de The Bridge",
        "Clonando el repositorio de GitHub de {n}",
    ],
    "deteccion": [
        "Abriendo los archivos ocultos de {n}",
        "Leyendo los apuntes secretos de {n}",
        "Descargando el proyecto de {n} sin que se entere",
        "Accediendo al portal de The Bridge con las credenciales de {n}",
    ],
    "ocr": [
        "Descifrando los WhatsApp de {n}",
        "Revisando el historial de búsqueda de {n}",
        "Copiando el código de {n} sin que se entere",
        "Rellenando el Weekly de Luismi en nombre de {n}",
    ],
    "cnn": [
        "Activando la red neuronal cuántica de {n}",
        "Propagando pulsos hacia adelante en la mente de {n}",
        "Ejecutando inferencia en el cerebro de {n}",
    ],
    "backtrack": [
        "Cambiando las notas de {n} en el expediente",
        "Reenviando los memes de {n} a toda la clase",
        "Instalando ventilador virtual en el puesto de {n}",
    ],
    "compare": [
        "Analizando vectores de error de {n}",
        "Calculando divergencia entre soluciones de {n}",
        "Generando informe de rendimiento para {n}",
        "Preparando la alianza de {n} con Full Stack para el proyecto final",
    ],
}

def iniciar_baraja():
    nombres = ALUMNOS[:]
    random.shuffle(nombres)
    profe = random.choice(["Diego", "Andreea"])
    pos   = random.randint(0, len(nombres))
    nombres.insert(pos, profe)
    st.session_state.baraja = nombres

def siguiente_nombre():
    if not st.session_state.get("baraja"):
        iniciar_baraja()
    return st.session_state.baraja.pop()

def mensajes_hack(fase):
    salida = []
    plantilla = PLANTILLAS_ALUMNOS.get(fase, ["Procesando"])
    for t in plantilla:
        nombre = siguiente_nombre()
        if nombre == "Diego":
            opciones = MENSAJES_DIEGO.get(fase, ["Hackeando el sistema de Diego"])
            salida.append(random.choice(opciones))
        elif nombre == "Andreea":
            opciones = MENSAJES_ANDREEA.get(fase, ["Hackeando el sistema de Andreea"])
            salida.append(random.choice(opciones))
        else:
            salida.append(t.format(n=nombre) if "{n}" in t else t)
    return salida

SCROLL_JS = """<script>
(function(){
    var doc = window.parent.document;
    var main = doc.querySelector('section[data-testid="stMain"]')
             || doc.querySelector('.main')
             || doc.documentElement;
    main.scrollTo({ top: main.scrollHeight, behavior: 'smooth' });
    window.parent.scrollTo({ top: window.parent.document.body.scrollHeight, behavior: 'smooth' });
})();
</script>"""

def scroll_abajo():
    components.html(SCROLL_JS, height=0)

def animar_hack(fase, contenedor, delay=2.2, pausa_final=2.0):
    msgs = mensajes_hack(fase)
    acumulado = []
    for m in msgs:
        html = "<div style='font-family:Share Tech Mono,monospace; padding:12px 0; font-size: 1.26rem;'>"
        for prev in acumulado:
            html += (f"<div style='color:#00aa2e; opacity:0.8; margin:8px 0;'>"
                     f"&gt; {prev} <span style='color:#7fff00'>[OK]</span></div>")
        html += (f"<div style='color:#00ff41; margin:8px 0; text-shadow:0 0 8px #00ff41;'>"
                 f"&gt; {m}<span class='puntos'></span> <span class='cur'>█</span></div>")
        html += "</div>"
        contenedor.markdown(html, unsafe_allow_html=True)
        scroll_abajo()
        time.sleep(delay)
        acumulado.append(m)
    final = "<div style='font-family:Share Tech Mono,monospace; padding:12px 0; font-size: 1.21rem;'>"
    for m in acumulado:
        final += (f"<div style='color:#00aa2e; opacity:0.85; margin:7px 0;'>"
                  f"&gt; {m} <span style='color:#7fff00'>[OK]</span></div>")
    final += "</div>"
    contenedor.markdown(final, unsafe_allow_html=True)
    scroll_abajo()
    time.sleep(pausa_final)
    return final
# ── Header ────────────────────────────────────────────────────
st.title("SUDOKU RELOADED")
st.markdown("<p class='matrix-subtitle'>REALITY.EXE HA DEJADO DE FUNCIONAR | RESUELVE EL SUDOKU</p>", unsafe_allow_html=True)

# ── Cargar modelos ────────────────────────────────────────────
@st.cache_resource
def cargar_modelos():
    modelo_yolo   = YOLO(os.path.join(MODELOS_DIR, "yolo.pt"))
    modelo_ocr    = keras.models.load_model(os.path.join(MODELOS_DIR, "modelo_ocr.keras"))
    modelo_solver = keras.models.load_model(os.path.join(MODELOS_DIR, "modelo_sudoku_mejor.keras"))
    return modelo_yolo, modelo_ocr, modelo_solver

modelo_yolo, modelo_ocr, modelo_solver = cargar_modelos()

# ── Funciones — misma lógica exacta que el notebook ──────────

def ordenar_esquinas(pts):
    pts  = pts.reshape(4, 2).astype('float32')
    rect = np.zeros((4, 2), dtype='float32')
    s       = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # top-left
    rect[2] = pts[np.argmax(s)]   # bottom-right
    d       = np.diff(pts, axis=1).flatten()
    rect[1] = pts[np.argmin(d)]   # top-right
    rect[3] = pts[np.argmax(d)]   # bottom-left
    return rect

def corregir_perspectiva(img):
    gris  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur  = cv2.GaussianBlur(gris, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY_INV, 11, 4)
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.dilate(thresh, kernel, iterations=1)
    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return img
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)
    img_area  = img.shape[0] * img.shape[1]
    for c in contornos[:8]:
        if cv2.contourArea(c) < img_area * 0.15:
            continue
        peri   = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            rect = ordenar_esquinas(approx.reshape(4, 2))
        else:
            box  = cv2.boxPoints(cv2.minAreaRect(c))
            rect = ordenar_esquinas(box)
        lado = 450
        dst  = np.array([[0,0],[lado,0],[lado,lado],[0,lado]], dtype='float32')
        M    = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, M, (lado, lado))
    return img

def eliminar_lineas(warped):
    gris    = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    binaria = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY_INV, 11, 5)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (warped.shape[1]//9, 1))
    h_lines  = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, h_kernel)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, warped.shape[0]//9))
    v_lines  = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, v_kernel)
    lineas   = cv2.dilate(cv2.add(h_lines, v_lines), np.ones((3,3), np.uint8), iterations=1)
    resultado = gris.copy()
    resultado[lineas > 0] = 255
    return resultado

def dividir_celdas(img_sin_lineas, margen=6):
    alto, ancho = img_sin_lineas.shape[:2]
    ch, cw = alto // 9, ancho // 9
    celdas = []
    for fila in range(9):
        fc = []
        for col in range(9):
            y1 = fila*ch + margen;  y2 = y1 + ch - margen*2
            x1 = col*cw + margen;   x2 = x1 + cw - margen*2
            fc.append(img_sin_lineas[y1:y2, x1:x2])
        celdas.append(fc)
    return celdas

def celda_tiene_digito(celda):
    gris = celda if len(celda.shape)==2 else cv2.cvtColor(celda, cv2.COLOR_BGR2GRAY)
    gris = cv2.resize(gris.astype(np.float32), (48, 48))
    e    = 8
    esquinas = np.concatenate([gris[:e,:e].ravel(), gris[:e,-e:].ravel(),
                                gris[-e:,:e].ravel(), gris[-e:,-e:].ravel()])
    fondo  = np.median(esquinas)
    centro = gris[12:36, 12:36]
    return (np.sum(centro < fondo - 40) / centro.size) > 0.03

def preprocesar_para_cnn(celda):
    gris = celda if len(celda.shape)==2 else cv2.cvtColor(celda, cv2.COLOR_BGR2GRAY)
    gris = cv2.resize(gris, (28, 28), interpolation=cv2.INTER_AREA)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    gris  = clahe.apply(gris)
    _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binaria.astype('float32') / 255.0

def predecir_celda(celda, modelo):
    if not celda_tiene_digito(celda):
        return 0
    img   = preprocesar_para_cnn(celda).reshape(1, 28, 28, 1)
    pred  = modelo.predict(img, verbose=0)[0]
    clase = int(np.argmax(pred))
    if clase == 0:
        clase = int(np.argmax(pred[1:])) + 1
    return clase

def detectar_sudoku(celdas, modelo):
    return [[predecir_celda(celdas[f][c], modelo) for c in range(9)] for f in range(9)]

def resolver_cnn(sudoku, modelo):
    puzzle_flat  = np.array([v for fila in sudoku for v in fila], dtype='float32')
    puzzle_input = (puzzle_flat / 9.0).reshape(1, 81)
    t0       = time.time()
    pred_raw = modelo.predict(puzzle_input, verbose=0)[0]
    t_ms     = (time.time() - t0) * 1000
    digitos  = np.argmax(pred_raw, axis=1) + 1
    sol      = np.where(puzzle_flat != 0, puzzle_flat.astype(int), digitos)
    tablero  = sol.reshape(9, 9).tolist()
    n_huecos = int((puzzle_flat == 0).sum())
    return tablero, t_ms, n_huecos

def es_valido(t, fila, col, num):
    if num in t[fila]: return False
    if num in [t[i][col] for i in range(9)]: return False
    bf, bc = (fila//3)*3, (col//3)*3
    for i in range(bf, bf+3):
        for j in range(bc, bc+3):
            if t[i][j] == num: return False
    return True

def backtrack(t):
    for i in range(9):
        for j in range(9):
            if t[i][j] == 0:
                for num in range(1, 10):
                    if es_valido(t, i, j, num):
                        t[i][j] = num
                        if backtrack(t): return True
                        t[i][j] = 0
                return False
    return True

def resolver_backtrack(sudoku):
    tablero = copy.deepcopy(sudoku)
    t0      = time.time()
    exito   = backtrack(tablero)
    t_ms    = (time.time() - t0) * 1000
    return tablero, exito, t_ms

# ── Render HTML ───────────────────────────────────────────────
def render_sudoku(sudoku, original=None, comparar_con=None):
    html = "<div class='sudoku-wrap'><table class='sudoku'>"
    for i, fila in enumerate(sudoku):
        html += "<tr>"
        for j, num in enumerate(fila):
            valor    = str(num) if num != 0 else "&nbsp;"
            es_pista = original is not None and original[i][j] != 0
            if es_pista:
                css = "given"
            elif comparar_con is not None and num != 0:
                css = "cnn-ok" if num == comparar_con[i][j] else "cnn-err"
            elif original is not None and num != 0:
                css = "solved"
            elif original is None and num != 0:
                css = "given"
            else:
                css = "empty"
            html += f"<td class='{css}'>{valor}</td>"
        html += "</tr>"
    html += "</table></div>"
    return html

def render_comparativa(sudoku, tablero_cnn, tablero_bt, t_cnn, t_bt):
    arr_orig = np.array(sudoku)
    arr_cnn  = np.array(tablero_cnn)
    arr_bt   = np.array(tablero_bt)
    mask     = arr_orig == 0
    n_huecos = int(mask.sum())
    aciertos = int(np.sum(arr_cnn[mask] == arr_bt[mask]))
    pct      = aciertos / n_huecos * 100 if n_huecos > 0 else 100.0
    perfecta = aciertos == n_huecos
    bt_ok    = int(np.sum(arr_bt == 0)) == 0

    html  = "<table class='compare'>"
    html += "<tr><th>MÉTODO</th><th>CELDAS CORRECTAS</th><th>TIEMPO</th><th>GARANTÍA</th></tr>"
    cls_pct = "green" if perfecta else ("highlight" if pct >= 80 else "red")
    html += (f"<tr><td>🧠 RED NEURONAL</td>"
             f"<td class='{cls_pct}'>{aciertos}/{n_huecos} ({pct:.1f}%)</td>"
             f"<td class='highlight'>{t_cnn:.1f} ms</td>"
             f"<td class='red'>NO GARANTIZA</td></tr>")
    bt_cls = "green" if bt_ok else "red"
    bt_txt = "SÍ — 100%" if bt_ok else "PUZZLE INVÁLIDO"
    html += (f"<tr><td>⚙️  BACKTRACKING</td>"
             f"<td class='green'>{n_huecos}/{n_huecos} (100.0%)</td>"
             f"<td>{t_bt:.1f} ms</td>"
             f"<td class='{bt_cls}'>{bt_txt}</td></tr>")
    html += "</table>"

    if perfecta:
        msg   = "✅ LA RED NEURONAL RESOLVIÓ EL PUZZLE PERFECTAMENTE"
        color = "#00ff41"
    else:
        errores = n_huecos - aciertos
        msg     = f"⚠️  LA RED FALLÓ EN {errores} CELDA(S) — EL BACKTRACKING GARANTIZA EL 100%"
        color   = "#ffd000"
    html += (f"<div style='font-family:Share Tech Mono,monospace; color:{color}; "
             f"margin-top:1rem; font-size:1rem; letter-spacing:1px; "
             f"text-shadow:0 0 8px {color};'>&gt;&gt; {msg}</div>")
    return html, aciertos, n_huecos, pct, perfecta

# ════════════════════════════════════════════════════════════
# FLUJO POR PASOS
# 0=inicio · 1=imagen · 2=fase1-yolo · 3=fase2-ocr
# 4=fase3-cnn · 5=fase4-backtrack · 6=fase5-comparativa
# ════════════════════════════════════════════════════════════

if "paso" not in st.session_state:
    st.session_state.paso  = 0
    st.session_state.datos = {}

st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.markdown("<div class='step-tag'>&gt;_ PROTOCOLO</div>", unsafe_allow_html=True)
st.markdown("**Carga el sudoku y ejecuta las fases del hackeo**")

imagen_subida = st.file_uploader("Sube tu sudoku", type=["jpg","jpeg","png"], label_visibility="collapsed")

if imagen_subida is not None:
    if st.session_state.datos.get("nombre") != imagen_subida.name:
        st.session_state.paso  = 0
        st.session_state.datos = {"nombre": imagen_subida.name}

if not imagen_subida:
    st.markdown("""
<div class='upload-area'>
    <div style='font-size: 2.88rem; color:#00ff41'>&#9783;</div>
    <div style='color:#00ff41; font-family:"Share Tech Mono",monospace; font-size: 1.38rem; letter-spacing:2px'>
        INYECTA EL SUDOKU<br>
        <span style='font-size: 1.03rem; opacity:0.6'>JPG · PNG · Captura · Foto de periódico</span>
    </div>
</div>
""", unsafe_allow_html=True)
    st.stop()

if "imagen" not in st.session_state.datos:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(imagen_subida.read()); tmp_path = tmp.name
    st.session_state.datos["imagen"] = cv2.imread(tmp_path)
    os.unlink(tmp_path)

imagen = st.session_state.datos["imagen"]

# ── PASO 0 → pantalla de inicio ──────────────────────────────
if st.session_state.paso == 0:
    if st.session_state.datos.get("pildora_azul"):
        st.markdown("""
<div style='font-family:"Share Tech Mono",monospace; text-align:center;
            color:#4488ff; font-size:1.1rem; letter-spacing:2px; margin-bottom:1rem;
            text-shadow:0 0 10px #4488ff;'>
    &gt;&gt; HAS ELEGIDO LA PÍLDORA AZUL &lt;&lt;<br>
    <span style='font-size:0.85rem; opacity:0.7;'>La historia termina aquí. Sigues creyendo lo que quieres creer.</span>
</div>
""", unsafe_allow_html=True)
        st.markdown(
            "<div style='display:flex;justify-content:center;'>"
            "<img src='https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExczg0eWhrczM5bDVraXJjZGdpeTc1Y3p3bnkxMHZsYjczeDFoYW5wOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/5Cc1oc4t7xTJnfa6Pq/giphy.gif'"
            " style='max-width:100%;border-radius:8px;box-shadow:0 0 30px rgba(68,136,255,0.5);'>"
            "</div>",
            unsafe_allow_html=True
        )
        st.markdown("<br><br>", unsafe_allow_html=True)
        _, col_r, _ = st.columns([1, 2, 1])
        with col_r:
            if st.button("↺ NUEVA INTRUSIÓN"):
                components.html("<script>window.parent.location.reload();</script>", height=0)
        st.stop()

    st.markdown("""
<div style='
    font-family:"Share Tech Mono",monospace;
    background: rgba(0,15,0,0.92);
    border: 2px solid #00ff41;
    box-shadow: 0 0 40px rgba(0,255,65,0.3), inset 0 0 60px rgba(0,255,65,0.05);
    padding: 2.5rem 2rem; margin: 1.5rem 0; text-align: center; letter-spacing: 2px;
'>
    <div style='font-size:3.2rem; margin-bottom:0.5rem;'>🕳️</div>
    <div style='color:#00ff41; font-size:1.4rem; text-shadow:0 0 12px #00ff41; margin-bottom:0.8rem;'>
        ACCESO AL SISTEMA DETECTADO
    </div>
    <div style='color:#00aa2e; font-size:0.95rem; line-height:2; margin-bottom:1.5rem;'>
        El sistema ha identificado un sudoku.<br>
        Para acceder a Matrix debes elegir:<br><br>
        <span style='color:#ff4444; text-shadow:0 0 8px #ff0000;'>▓ PÍLDORA ROJA</span>
        &nbsp;→&nbsp; entras en la Matrix y descubres la verdad<br>
        <span style='color:#4488ff; text-shadow:0 0 8px #4488ff;'>▓ PÍLDORA AZUL</span>
        &nbsp;→&nbsp; cierras el navegador y sigues durmiendo
    </div>
    <div style='color:#00ff41; font-size:0.82rem; opacity:0.5; letter-spacing:4px;'>
        ── LA ELECCIÓN ES TUYA ──
    </div>
</div>
""", unsafe_allow_html=True)

    col_roja, col_azul = st.columns(2)
    with col_roja:
        if st.button("🔴  PÍLDORA ROJA  →  ENTRAR EN LA MATRIX"):
            iniciar_baraja()
            ph  = st.empty()
            log = animar_hack("intro", ph)
            st.session_state.datos["log_intro"] = log
            st.session_state.paso = 1
            st.rerun()
    with col_azul:
        if st.button("🔵  PÍLDORA AZUL  →  SEGUIR DURMIENDO"):
            st.session_state.datos["pildora_azul"] = True
            st.rerun()
    st.stop()

if st.session_state.datos.get("log_intro"):
    st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
    st.markdown(st.session_state.datos["log_intro"], unsafe_allow_html=True)

st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.image(cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB), use_container_width=True)

# ── PASO 1 → FASE 1: YOLO + perspectiva ──────────────────────
if st.session_state.paso == 1:
    if st.button("▶ EJECUTAR FASE 1 · LOCALIZACIÓN SUDOKU"):
        ph      = st.empty()
        log     = animar_hack("deteccion", ph)
        results = modelo_yolo(imagen, verbose=False)
        if len(results[0].boxes) == 0:
            ph.empty()
            st.error(">> ERROR: No se detectó ninguna matriz. Reintenta con otra imagen.")
            st.stop()
        boxes    = results[0].boxes.xyxy.cpu().numpy()
        areas    = (boxes[:,2]-boxes[:,0]) * (boxes[:,3]-boxes[:,1])
        idx      = int(np.argmax(areas))
        x1,y1,x2,y2 = map(int, boxes[idx])
        conf     = float(results[0].boxes.conf[idx])
        recorte  = imagen[y1:y2, x1:x2]
        corregida = corregir_perspectiva(recorte)
        st.session_state.datos.update({"recorte": recorte, "corregida": corregida,
                                        "conf": conf, "log_f1": log})
        st.session_state.paso = 2
        st.rerun()
    st.stop()

st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.markdown("<div class='step-tag'>&gt;_ FASE 1 · LOCALIZACIÓN SUDOKU</div>", unsafe_allow_html=True)
if st.session_state.datos.get("log_f1"):
    st.markdown(st.session_state.datos["log_f1"], unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.image(cv2.cvtColor(st.session_state.datos["recorte"],   cv2.COLOR_BGR2RGB))
with c2:
    st.image(cv2.cvtColor(st.session_state.datos["corregida"], cv2.COLOR_BGR2RGB))

# ── PASO 2 → FASE 2: CNN OCR ─────────────────────────────────
if st.session_state.paso == 2:
    if st.button("▶ EJECUTAR FASE 2 · RECONOCIMIENTO ÓPTICO · OCR"):
        ph        = st.empty()
        log       = animar_hack("ocr", ph)
        t0        = time.time()
        corregida = st.session_state.datos["corregida"]
        img_sl    = eliminar_lineas(corregida)
        celdas    = dividir_celdas(img_sl)
        sudoku    = detectar_sudoku(celdas, modelo_ocr)
        st.session_state.datos.update({"sudoku": sudoku,
                                        "img_sl": img_sl,
                                        "t_ocr":  time.time() - t0,
                                        "log_f2": log})
        st.session_state.paso = 3
        st.rerun()
    st.stop()

sudoku = st.session_state.datos["sudoku"]
nd     = sum(1 for f in sudoku for n in f if n != 0)
st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.markdown("<div class='step-tag'>&gt;_ FASE 2 · RECONOCIMIENTO ÓPTICO · OCR</div>", unsafe_allow_html=True)
if st.session_state.datos.get("log_f2"):
    st.markdown(st.session_state.datos["log_f2"], unsafe_allow_html=True)
st.markdown(f"<p style='color:#00ff41'>&gt;&gt; {nd} glifos descifrados · {81-nd} casillas cifradas</p>",
            unsafe_allow_html=True)
img_sl = st.session_state.datos.get("img_sl")
if img_sl is not None:
    import base64 as _b64
    _, buf = cv2.imencode(".png", img_sl)
    b64    = _b64.b64encode(buf).decode()
    st.markdown(f"""
<div style='display:flex; justify-content:center; gap:1rem; align-items:flex-start;
            flex-wrap:nowrap; margin:1.5rem 0; overflow-x:auto;'>
  <div style='text-align:center; flex-shrink:0;'>
    <p style='color:#00aa2e; font-family:"Share Tech Mono",monospace; font-size:0.80rem;
              letter-spacing:1px; margin-bottom:8px;'>IMAGEN PROCESADA POR EL MODELO</p>
    <img src='data:image/png;base64,{b64}'
         style='width:280px; height:280px; object-fit:cover;
                border:2px solid #00ff41; box-shadow:0 0 20px rgba(0,255,65,0.4);
                display:block;'/>
  </div>
  <div style='text-align:center; flex-shrink:0;'>
    <p style='color:#00aa2e; font-family:"Share Tech Mono",monospace; font-size:0.80rem;
              letter-spacing:1px; margin-bottom:8px;'>DÍGITOS RECONOCIDOS POR LA CNN</p>
    <div style='width:282px; height:282px; overflow:hidden;'>
      <div style='transform:scale(0.71); transform-origin:top left; width:396px;'>
        {render_sudoku(sudoku).replace("<div class='sudoku-wrap'>","<div style='margin:0;'>").strip()}
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown(render_sudoku(sudoku), unsafe_allow_html=True)
# ── PASO 3 → FASE 3: CNN solver ──────────────────────────────
if st.session_state.paso == 3:
    if st.button("▶ EJECUTAR FASE 3 · RED NEURONAL"):
        ph  = st.empty()
        log = animar_hack("cnn", ph)
        tablero_cnn, t_cnn, n_huecos = resolver_cnn(sudoku, modelo_solver)
        st.session_state.datos.update({"tablero_cnn": tablero_cnn,
                                        "t_cnn":       t_cnn,
                                        "n_huecos":    n_huecos,
                                        "log_f3":      log})
        st.session_state.paso = 4
        st.rerun()
    st.stop()

tablero_cnn = st.session_state.datos["tablero_cnn"]
st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.markdown("<div class='step-tag-cnn'>&gt;_ FASE 3 · RED NEURONAL SOLVER</div>", unsafe_allow_html=True)
if st.session_state.datos.get("log_f3"):
    st.markdown(st.session_state.datos["log_f3"], unsafe_allow_html=True)
st.markdown("<p style='color:#ffd000'>&gt;&gt; INFERENCIA DIRECTA — SIN GARANTÍA DE SOLUCIÓN PERFECTA</p>",
            unsafe_allow_html=True)
st.markdown(render_sudoku(tablero_cnn, original=sudoku), unsafe_allow_html=True)
st.markdown(f"<p style='color:#ffd000; text-align:center'>&gt; tiempo de inferencia: "
            f"{st.session_state.datos['t_cnn']:.1f} ms</p>", unsafe_allow_html=True)

# ── PASO 4 → FASE 4: backtracking ────────────────────────────
if st.session_state.paso == 4:
    if st.button("▶ EJECUTAR FASE 4 · BACKTRACKING"):
        ph  = st.empty()
        log = animar_hack("backtrack", ph)
        tablero_bt, exito, t_bt = resolver_backtrack(sudoku)
        st.session_state.datos.update({"tablero_bt": tablero_bt,
                                        "exito":      exito,
                                        "t_bt":       t_bt,
                                        "log_f4":     log})
        st.session_state.paso = 5
        st.rerun()
    st.stop()

tablero_bt = st.session_state.datos["tablero_bt"]
st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.markdown("<div class='step-tag'>&gt;_ FASE 4 · BACKTRACKING</div>", unsafe_allow_html=True)
if st.session_state.datos.get("log_f4"):
    st.markdown(st.session_state.datos["log_f4"], unsafe_allow_html=True)

if not st.session_state.datos["exito"]:
    st.markdown("""
<div style='font-family:"Share Tech Mono",monospace; background:rgba(30,0,0,0.9);
            border:1px solid #ff4444; box-shadow:0 0 20px rgba(255,68,68,0.4);
            padding:1.5rem; margin:1rem 0; text-align:center; letter-spacing:2px;'>
    <div style='font-size:1.5rem; margin-bottom:0.5rem;'>⛔</div>
    <div style='color:#ff4444; font-size:1.1rem; text-shadow:0 0 8px #ff2222;'>
        &gt;&gt; ERROR: CIFRADO IRROMPIBLE
    </div>
    <div style='color:#aa2222; font-size:0.88rem; margin-top:0.5rem;'>
        La OCR leyó mal uno o más glifos. El puzzle no tiene solución válida.
    </div>
</div>
""", unsafe_allow_html=True)
    _, col_r, _ = st.columns([1, 2, 1])
    with col_r:
        if st.button("↺ REINTENTAR CON OTRA IMAGEN"):
            components.html("<script>window.parent.location.reload();</script>", height=0)
    st.stop()

st.markdown("""
<div class='win-banner'>
    &gt;&gt; ACCESO CONCEDIDO &lt;&lt;<br>
    <span style='font-size: 0.92rem; color:#00aa2e'>LA MATRIX HA SIDO DESCIFRADA</span>
</div>
""", unsafe_allow_html=True)
st.markdown(render_sudoku(tablero_bt, original=sudoku), unsafe_allow_html=True)
st.markdown("<p style='text-align:center; font-family:\"Share Tech Mono\",monospace; "
            "font-size: 1.15rem; letter-spacing:2px; color:#00ff41'>"
            "&gt; <span style='color:#00ff41'>VERDE = DATOS ORIGINALES</span>"
            " &nbsp;&nbsp; <span style='color:#ffd000'>ÁMBAR = REALIDAD RECONSTRUIDA</span></p>",
            unsafe_allow_html=True)

# ── PASO 5 → FASE 5: comparativa ─────────────────────────────
if st.session_state.paso == 5:
    if st.button("▶ EJECUTAR FASE 5 · ANÁLISIS COMPARATIVO"):
        ph  = st.empty()
        log = animar_hack("compare", ph)
        st.session_state.datos["log_f5"] = log
        st.session_state.paso = 6
        st.rerun()
    st.stop()

st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.markdown("<div class='step-tag-compare'>&gt;_ FASE 5 · ANÁLISIS COMPARATIVO</div>", unsafe_allow_html=True)
if st.session_state.datos.get("log_f5"):
    st.markdown(st.session_state.datos["log_f5"], unsafe_allow_html=True)

t_cnn = st.session_state.datos["t_cnn"]
t_bt  = st.session_state.datos["t_bt"]

html_tabla, aciertos, n_huecos, pct, perfecta = render_comparativa(
    sudoku, tablero_cnn, tablero_bt, t_cnn, t_bt)

st.markdown("<p style='color:#00cfff; letter-spacing:2px'>"
            "&gt;&gt; COMPARACIÓN VISUAL: RED NEURONAL vs BACKTRACKING</p>",
            unsafe_allow_html=True)
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("<p style='color:#ffd000; text-align:center'>🧠 RED NEURONAL</p>", unsafe_allow_html=True)
    st.markdown(render_sudoku(tablero_cnn, original=sudoku, comparar_con=tablero_bt), unsafe_allow_html=True)
with col_b:
    st.markdown("<p style='color:#00ff41; text-align:center'>⚙️ BACKTRACKING</p>", unsafe_allow_html=True)
    st.markdown(render_sudoku(tablero_bt, original=sudoku), unsafe_allow_html=True)

st.markdown("<p style='font-size:0.9rem; color:#00aa2e; text-align:center'>"
            "🔵 azul = acierto CNN &nbsp;|&nbsp; 🔴 rojo = fallo CNN &nbsp;|&nbsp; "
            "🟡 ámbar = backtracking &nbsp;|&nbsp; 🟢 verde brillante = pista original</p>",
            unsafe_allow_html=True)

st.markdown(html_tabla, unsafe_allow_html=True)

st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"<div class='stat-box'><span class='stat-num'>{nd}</span>"
                f"<span class='stat-lbl'>GLIFOS LEÍDOS</span></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='stat-box'><span class='stat-num'>{pct:.1f}%</span>"
                f"<span class='stat-lbl'>ACIERTO CNN</span></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='stat-box'><span class='stat-num'>{t_cnn:.1f}ms</span>"
                f"<span class='stat-lbl'>T. RED NEURONAL</span></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='stat-box'><span class='stat-num'>{t_bt:.1f}ms</span>"
                f"<span class='stat-lbl'>T. BACKTRACKING</span></div>", unsafe_allow_html=True)

st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
_, col_c, _ = st.columns([1, 2, 1])
with col_c:
    if st.button("↺ NUEVA INTRUSIÓN"):
        # recarga completa del navegador: limpia session_state y vuelve al estado inicial
        components.html("<script>window.parent.location.reload();</script>", height=0)
