import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
import tempfile
import os
import copy
import time
import random
import streamlit.components.v1 as components

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="SUDOKU RELOADED", page_icon="🟢", layout="centered")

# ── Lluvia de código Matrix (se inyecta en el documento padre real) ──
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

# ── CSS Matrix ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

/* Fondo negro y la lluvia detrás de todo */
.stApp { background-color: #000000; }
.main .block-container { background: transparent; }
.main .block-container { position: relative; z-index: 1; }

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
.sudoku-wrap { display: flex; justify-content: center; margin: 1.5rem 0; }
table.sudoku {
    border-collapse: collapse; font-family: 'Share Tech Mono', monospace;
    font-size: 20.7px; border: 2px solid #00ff41;
    box-shadow: 0 0 20px rgba(0,255,65,0.4);
}
table.sudoku td {
    width: 44px; height: 44px; text-align: center; vertical-align: middle;
    background: #001a00; color: #00aa2e;
}
table.sudoku td.given { color: #00ff41; background: #002200; text-shadow: 0 0 8px #00ff41; font-weight: bold; }
table.sudoku td.solved { color: #ffd000; background: #1a1500; text-shadow: 0 0 10px #ffb000; font-weight: bold; }
table.sudoku td.empty { color: transparent; }
table.sudoku tr:nth-child(3n) td { border-bottom: 2px solid #00ff41; }
table.sudoku tr:nth-child(3n+1) td { border-top: 2px solid #00ff41; }
table.sudoku td:nth-child(3n) { border-right: 2px solid #00ff41; }
table.sudoku td:nth-child(3n+1) { border-left: 2px solid #00ff41; }
table.sudoku td { border: 1px solid #004d15; }
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
    97% { text-shadow: 2px 0 #ff0000, -2px 0 #0000ff; transform: skewX(-3deg); }
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

/* Botones estilo Matrix */
.stButton > button {
    font-family: 'Share Tech Mono', monospace !important;
    background: rgba(0,20,0,0.9) !important;
    color: #00ff41 !important;
    border: 2px solid #00ff41 !important;
    border-radius: 4px !important;
    letter-spacing: 2px !important;
    box-shadow: 0 0 12px rgba(0,255,65,0.4) !important;
    transition: all 0.2s !important;
    width: 100% !important;
    font-size: 1.21rem !important;
}
.stButton > button:hover {
    background: #00ff41 !important; color: #000 !important;
    box-shadow: 0 0 25px rgba(0,255,65,0.8) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Mensajes de hacker ───────────────────────────────────────
# Toda la gente del bootcamp (compañeros + Diego y Andreea). Una sola lista.
GENTE = ["Bárbara", "Ainara", "Nora", "David", "Leire", "Eduardo",
         "Raúl", "Ander", "Álex", "Juan", "Diego", "Andreea"]

# Plantillas de mensajes. {n} se rellena con un nombre distinto cada vez.
PLANTILLAS = {
    "intro": [
        "Accediendo al ordenador central de The Bridge",
        "Conectando con el portátil de {n}",
        "Rastreando la sesión de {n} en el bootcamp",
        "Clonando el disco duro de {n}",
    ],
    "deteccion": [
        "Abriendo los archivos ocultos de {n}",
        "Leyendo los apuntes secretos de {n}",
        "Entrando en la carpeta de proyectos de {n}",
    ],
    "ocr": [
        "Descifrando los WhatsApp de {n}",
        "Revisando el historial de búsqueda de {n}",
        "Copiando el código de {n} sin que se entere",
    ],
    "backtrack": [
        "Cambiando las notas de {n} en el expediente",
        "Borrando las faltas de asistencia del ordenador de {n}",
        "Reenviando los memes de {n} a toda la clase",
    ],
}

def iniciar_baraja():
    """Baraja con TODOS los nombres, se consume sin repetir durante la intrusión."""
    nombres = GENTE[:]
    random.shuffle(nombres)
    st.session_state.baraja = nombres

def siguiente_nombre():
    if not st.session_state.get("baraja"):
        iniciar_baraja()
    return st.session_state.baraja.pop()

def mensajes_hack(fase):
    salida = []
    for t in PLANTILLAS.get(fase, ["Procesando"]):
        salida.append(t.format(n=siguiente_nombre()) if "{n}" in t else t)
    return salida

def animar_hack(fase, contenedor, delay=2.2, pausa_final=2.0):
    """Muestra los mensajes uno a uno con puntos animados. Devuelve el HTML final
    (todos con [OK]) para poder dejarlo fijo en pantalla después."""
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
        time.sleep(delay)
        acumulado.append(m)
    # HTML final: todos con [OK]
    final = "<div style='font-family:Share Tech Mono,monospace; padding:12px 0; font-size: 1.21rem;'>"
    for m in acumulado:
        final += (f"<div style='color:#00aa2e; opacity:0.85; margin:7px 0;'>"
                  f"&gt; {m} <span style='color:#7fff00'>[OK]</span></div>")
    final += "</div>"
    contenedor.markdown(final, unsafe_allow_html=True)
    time.sleep(pausa_final)
    return final

# ── Header ───────────────────────────────────────────────────
st.title("SUDOKU RELOADED")
st.markdown("<p class='matrix-subtitle'>REALITY.EXE HA DEJADO DE FUNCIONAR | RESUELVE EL SUDOKU</p>", unsafe_allow_html=True)

# ── Cargar modelos ───────────────────────────────────────────
@st.cache_resource
def cargar_modelos():
    modelo_yolo = YOLO(os.path.join(BASE_DIR, "modelos", "yolo.pt"))
    reader = easyocr.Reader(['en'], gpu=False)
    return modelo_yolo, reader

modelo_yolo, reader = cargar_modelos()

# ── Funciones (lógica intacta) ───────────────────────────────
def corregir_perspectiva(img):
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gris, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contorno = max(contornos, key=cv2.contourArea)
    epsilon = 0.02 * cv2.arcLength(contorno, True)
    esquinas = cv2.approxPolyDP(contorno, epsilon, True)
    if len(esquinas) != 4:
        return img
    pts = esquinas.reshape(4, 2).astype('float32')
    rect = np.zeros((4, 2), dtype='float32')
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]; rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]; rect[3] = pts[np.argmax(diff)]
    lado = 450
    dst = np.array([[0,0],[lado,0],[lado,lado],[0,lado]], dtype='float32')
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(img, M, (lado, lado))

def dividir_celdas(img, margen=4):
    alto, ancho = img.shape[:2]
    ch, cw = alto // 9, ancho // 9
    celdas = []
    for fila in range(9):
        fc = []
        for col in range(9):
            y1 = fila*ch+margen; y2 = y1+ch-margen*2
            x1 = col*cw+margen; x2 = x1+cw-margen*2
            fc.append(img[y1:y2, x1:x2])
        celdas.append(fc)
    return celdas

def preprocesar_celda(gris, fondo_oscuro):
    gris = cv2.resize(gris, (96, 96), interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    gris = clahe.apply(gris)
    if fondo_oscuro:
        gris = cv2.bitwise_not(gris)
    gris = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return gris

def predecir_celda(celda, reader):
    gris = cv2.cvtColor(celda, cv2.COLOR_BGR2GRAY)
    fondo_oscuro = np.mean(gris) < 128
    for usar_oscuro in [fondo_oscuro, not fondo_oscuro]:
        img = preprocesar_celda(gris.copy(), usar_oscuro)
        r = reader.readtext(img, allowlist='123456789', detail=1, width_ths=0.2)
        if r:
            t, c = r[0][1], r[0][2]
            if t.isdigit() and 1 <= int(t) <= 9 and c >= 0.4:
                return int(t)
        r2 = reader.readtext(img, allowlist='123456789', detail=1, width_ths=0.1)
        if r2:
            t2, c2 = r2[0][1], r2[0][2]
            if t2.isdigit() and 1 <= int(t2) <= 9 and c2 >= 0.25:
                return int(t2)
    return 0

def detectar_sudoku(celdas, reader):
    return [[predecir_celda(celdas[f][c], reader) for c in range(9)] for f in range(9)]

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

def resolver(sudoku):
    tablero = copy.deepcopy(sudoku)
    return tablero, backtrack(tablero)

def render_sudoku(sudoku, original=None):
    html = "<div class='sudoku-wrap'><table class='sudoku'>"
    for i, fila in enumerate(sudoku):
        html += "<tr>"
        for j, num in enumerate(fila):
            valor = str(num) if num != 0 else "&nbsp;"
            if original is None:
                css = "given" if num != 0 else "empty"
            else:
                css = "given" if original[i][j] != 0 else ("solved" if num != 0 else "empty")
            html += f"<td class='{css}'>{valor}</td>"
        html += "</tr>"
    html += "</table></div>"
    return html

# ════════════════════════════════════════════════════════════
# FLUJO POR PASOS con session_state
# ════════════════════════════════════════════════════════════

if "paso" not in st.session_state:
    st.session_state.paso = 0
    st.session_state.datos = {}

st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.markdown("<div class='step-tag'>&gt;_ PROTOCOLO</div>", unsafe_allow_html=True)
st.markdown("**Carga el sudoku y ejecuta las fases del hackeo**")

imagen_subida = st.file_uploader("Sube tu sudoku", type=["jpg","jpeg","png"], label_visibility="collapsed")

# Si cambia la imagen, reiniciar el flujo
if imagen_subida is not None:
    if st.session_state.datos.get("nombre") != imagen_subida.name:
        st.session_state.paso = 0
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

# Leer imagen y guardarla en sesión
if "imagen" not in st.session_state.datos:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(imagen_subida.read()); tmp_path = tmp.name
    st.session_state.datos["imagen"] = cv2.imread(tmp_path)
    os.unlink(tmp_path)

imagen = st.session_state.datos["imagen"]

# ── PASO 0 → botón para revelar imagen ───────────────────────
if st.session_state.paso == 0:
    if st.button("🔴 TOMAR LA PÍLDORA ROJA"):
        iniciar_baraja()
        ph = st.empty()
        log = animar_hack("intro", ph)
        st.session_state.datos["log_intro"] = log
        st.session_state.paso = 1
        st.rerun()
    st.stop()

# Mostrar los mensajes de la intrusión inicial (se quedan fijos)
if st.session_state.datos.get("log_intro"):
    st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
    st.markdown(st.session_state.datos["log_intro"], unsafe_allow_html=True)

# Mostrar la imagen objetivo (a partir del paso 1)
st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.image(cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB), caption=">> MATRIX OBJETIVO", use_container_width=True)

# ── PASO 1 → FASE 1: YOLO + perspectiva ──────────────────────
if st.session_state.paso == 1:
    if st.button("▶ EJECUTAR FASE 1 · LOCALIZACIÓN SUDOKU"):
        ph = st.empty()
        log = animar_hack("deteccion", ph)
        results = modelo_yolo(imagen)
        if len(results[0].boxes) == 0:
            ph.empty()
            st.error(">> ERROR: No se detectó ninguna matriz. Reintenta con otra imagen.")
            st.stop()
        x1,y1,x2,y2 = map(int, results[0].boxes.xyxy[0])
        conf = float(results[0].boxes.conf[0])
        recorte = results[0].orig_img[y1:y2, x1:x2]
        corregida = corregir_perspectiva(recorte)
        st.session_state.datos.update({"recorte": recorte, "corregida": corregida, "conf": conf, "log_f1": log})
        st.session_state.paso = 2
        st.rerun()
    st.stop()

# Mostrar resultado fase 1
st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.markdown("<div class='step-tag'>&gt;_ FASE 1 · LOCALIZACIÓN SUDOKU</div>", unsafe_allow_html=True)
if st.session_state.datos.get("log_f1"):
    st.markdown(st.session_state.datos["log_f1"], unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.image(cv2.cvtColor(st.session_state.datos["recorte"], cv2.COLOR_BGR2RGB), caption=f">> OBJETIVO FIJADO ({st.session_state.datos['conf']:.0%})")
with c2:
    st.image(cv2.cvtColor(st.session_state.datos["corregida"], cv2.COLOR_BGR2RGB), caption=">> SEÑAL ESTABILIZADA")

# ── PASO 2 → FASE 2: OCR ─────────────────────────────────────
if st.session_state.paso == 2:
    if st.button("▶ EJECUTAR FASE 2 · DESENCRIPTANDO"):
        ph = st.empty()
        log = animar_hack("ocr", ph)
        t0 = time.time()
        celdas = dividir_celdas(st.session_state.datos["corregida"])
        sudoku = detectar_sudoku(celdas, reader)
        st.session_state.datos["sudoku"] = sudoku
        st.session_state.datos["t_ocr"] = time.time() - t0
        st.session_state.datos["log_f2"] = log
        st.session_state.paso = 3
        st.rerun()
    st.stop()

# Mostrar resultado fase 2
sudoku = st.session_state.datos["sudoku"]
nd = sum(1 for f in sudoku for n in f if n != 0)
st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.markdown("<div class='step-tag'>&gt;_ FASE 2 · DESENCRIPTANDO</div>", unsafe_allow_html=True)
if st.session_state.datos.get("log_f2"):
    st.markdown(st.session_state.datos["log_f2"], unsafe_allow_html=True)
st.markdown(f"<p style='color:#00ff41'>&gt;&gt; {nd} glifos descifrados · {81-nd} casillas cifradas</p>", unsafe_allow_html=True)
st.markdown(render_sudoku(sudoku), unsafe_allow_html=True)
with st.expander(">> Inspeccionar lectura en crudo (debug)"):
    for i, fila in enumerate(sudoku):
        st.text(f"Fila {i+1}: {fila}")

# ── PASO 3 → FASE 3: backtracking ────────────────────────────
if st.session_state.paso == 3:
    if st.button("▶ EJECUTAR FASE 3 · HACKEANDO MATRIX"):
        ph = st.empty()
        log = animar_hack("backtrack", ph)
        t0 = time.time()
        solucion, exito = resolver(sudoku)
        st.session_state.datos["solucion"] = solucion
        st.session_state.datos["exito"] = exito
        st.session_state.datos["t_solver"] = time.time() - t0
        st.session_state.datos["log_f3"] = log
        st.session_state.paso = 4
        st.rerun()
    st.stop()

# ── PASO 4 → resultado final ─────────────────────────────────
if not st.session_state.datos["exito"]:
    st.error(">> ERROR: Cifrado irrompible. Posibles glifos mal leídos. Reintenta con otra imagen.")
    st.stop()

st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.markdown("<div class='step-tag'>&gt;_ FASE 3 · HACKEANDO MATRIX</div>", unsafe_allow_html=True)
if st.session_state.datos.get("log_f3"):
    st.markdown(st.session_state.datos["log_f3"], unsafe_allow_html=True)
st.markdown("""
<div class='win-banner'>
    &gt;&gt; ACCESO CONCEDIDO &lt;&lt;<br>
    <span style='font-size: 0.92rem; color:#00aa2e'>LA MATRIX HA SIDO DESCIFRADA</span>
</div>
""", unsafe_allow_html=True)
st.markdown(render_sudoku(st.session_state.datos["solucion"], original=sudoku), unsafe_allow_html=True)
st.markdown("<p style='text-align:center; font-family:\"Share Tech Mono\",monospace; font-size: 1.15rem; letter-spacing:2px; color:#00ff41'>&gt; <span style='color:#00ff41'>VERDE = DATOS ORIGINALES</span> &nbsp;&nbsp; <span style='color:#ffd000'>ÁMBAR = REALIDAD RECONSTRUIDA</span></p>", unsafe_allow_html=True)

st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"<div class='stat-box'><span class='stat-num'>{nd}</span><span class='stat-lbl'>GLIFOS LEÍDOS</span></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='stat-box'><span class='stat-num'>{st.session_state.datos['t_ocr']:.1f}s</span><span class='stat-lbl'>T. DESENCRIPTADO</span></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='stat-box'><span class='stat-num'>{st.session_state.datos['t_solver']*1000:.0f}ms</span><span class='stat-lbl'>T. DESCIFRADO</span></div>", unsafe_allow_html=True)

st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
_, col_c, _ = st.columns([1, 2, 1])
with col_c:
    if st.button("↺ NUEVA INTRUSIÓN"):
        st.session_state.paso = 0
        st.session_state.datos = {}
        st.rerun()
