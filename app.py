import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
import tempfile
import os
import copy
import time
import base64

# ── Configuración ────────────────────────────────────────────
st.set_page_config(
    page_title="Sudoku Master 🐱‍🔮",
    page_icon="🔮",
    layout="centered"
)

# ── CSS pixel art ────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap');

html, body, [class*="css"] {
    font-family: 'VT323', monospace;
    font-size: 18px;
}

.stApp {
    background-color: #1a0a2e;
    background-image:
        radial-gradient(ellipse at 20% 50%, rgba(120, 40, 200, 0.15) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 20%, rgba(200, 100, 40, 0.1) 0%, transparent 40%);
}

/* Stars background */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background-image:
        radial-gradient(1px 1px at 10% 15%, #fff 0%, transparent 100%),
        radial-gradient(1px 1px at 30% 5%, #fff 0%, transparent 100%),
        radial-gradient(1px 1px at 50% 25%, #fff 0%, transparent 100%),
        radial-gradient(1px 1px at 70% 10%, #fff 0%, transparent 100%),
        radial-gradient(1px 1px at 90% 20%, #fff 0%, transparent 100%),
        radial-gradient(1px 1px at 20% 80%, #fff 0%, transparent 100%),
        radial-gradient(1px 1px at 80% 70%, #fff 0%, transparent 100%),
        radial-gradient(2px 2px at 60% 90%, rgba(255,200,100,0.8) 0%, transparent 100%),
        radial-gradient(2px 2px at 40% 60%, rgba(180,100,255,0.8) 0%, transparent 100%);
    pointer-events: none;
    z-index: 0;
}

h1 {
    font-family: 'Press Start 2P', monospace !important;
    font-size: 1.6rem !important;
    color: #f5a623 !important;
    text-align: center !important;
    text-shadow: 3px 3px 0 #7b2d8b, 6px 6px 0 rgba(123,45,139,0.4) !important;
    letter-spacing: 2px !important;
    line-height: 1.6 !important;
    margin-bottom: 0 !important;
}

.pixel-subtitle {
    font-family: 'VT323', monospace;
    font-size: 1.3rem;
    color: #c084fc;
    text-align: center;
    margin-bottom: 1.5rem;
    letter-spacing: 2px;
}

/* Pixel border mixin via box-shadow */
.pixel-box {
    background: #2d1b4e;
    border: 3px solid #7b2d8b;
    box-shadow: 3px 3px 0 #f5a623, inset 0 0 20px rgba(120,40,200,0.2);
    border-radius: 0;
    padding: 1.5rem;
    margin: 1rem 0;
    position: relative;
}

.pixel-box::before {
    content: '◆';
    position: absolute;
    top: -12px; left: 12px;
    color: #f5a623;
    font-size: 1rem;
}

.step-tag {
    font-family: 'Press Start 2P', monospace;
    font-size: 0.55rem;
    background: #7b2d8b;
    color: #f5a623;
    border: 2px solid #f5a623;
    padding: 4px 10px;
    display: inline-block;
    margin-bottom: 12px;
    box-shadow: 2px 2px 0 #f5a623;
    letter-spacing: 1px;
}

/* Sudoku grid */
.sudoku-wrap {
    display: flex;
    justify-content: center;
    margin: 1.5rem 0;
}

table.sudoku {
    border-collapse: collapse;
    font-family: 'Press Start 2P', monospace;
    font-size: 13px;
    border: 4px solid #f5a623;
    box-shadow: 4px 4px 0 #7b2d8b, 8px 8px 0 rgba(245,166,35,0.3);
}

table.sudoku td {
    width: 44px;
    height: 44px;
    text-align: center;
    vertical-align: middle;
    background: #1a0a2e;
    color: #94a3b8;
}

table.sudoku td.given {
    color: #7dd3fc;
    background: #0f172a;
}

table.sudoku td.solved {
    color: #86efac;
    background: #052e16;
}

table.sudoku td.empty {
    color: transparent;
}

/* thick borders every 3 */
table.sudoku tr:nth-child(3n) td { border-bottom: 3px solid #f5a623; }
table.sudoku tr:nth-child(3n+1) td { border-top: 3px solid #f5a623; }
table.sudoku td:nth-child(3n) { border-right: 3px solid #f5a623; }
table.sudoku td:nth-child(3n+1) { border-left: 3px solid #f5a623; }
table.sudoku td { border: 1px solid #3b1f6e; }

/* Cat animations */
.cat-idle {
    font-size: 5rem;
    text-align: center;
    animation: float 3s ease-in-out infinite;
    display: block;
    filter: drop-shadow(0 0 12px rgba(200,100,255,0.6));
}

.cat-working {
    font-size: 5rem;
    text-align: center;
    animation: spin 1s linear infinite;
    display: block;
}

.cat-celebrate {
    font-size: 6rem;
    text-align: center;
    animation: bounce 0.5s ease infinite alternate;
    display: block;
    filter: drop-shadow(0 0 20px rgba(245,166,35,0.8));
}

@keyframes float {
    0%, 100% { transform: translateY(0px) rotate(-3deg); }
    50% { transform: translateY(-12px) rotate(3deg); }
}

@keyframes spin {
    0% { transform: rotate(0deg) scale(1); }
    50% { transform: rotate(180deg) scale(1.2); }
    100% { transform: rotate(360deg) scale(1); }
}

@keyframes bounce {
    0% { transform: translateY(0) scale(1); }
    100% { transform: translateY(-15px) scale(1.1); }
}

/* Win banner */
.win-banner {
    font-family: 'Press Start 2P', monospace;
    font-size: 0.9rem;
    background: linear-gradient(135deg, #7b2d8b, #1a0a2e);
    border: 4px solid #f5a623;
    box-shadow: 6px 6px 0 #f5a623;
    color: #f5a623;
    text-align: center;
    padding: 1.5rem;
    margin: 1rem 0;
    line-height: 2.5;
    animation: glitch 2s infinite;
}

@keyframes glitch {
    0%, 95%, 100% { text-shadow: 2px 2px 0 #7b2d8b; }
    96% { text-shadow: -2px 2px 0 #00ffff, 2px -2px 0 #ff00ff; transform: skewX(2deg); }
    97% { text-shadow: 2px -2px 0 #00ffff, -2px 2px 0 #ff00ff; transform: skewX(-2deg); }
    98% { text-shadow: none; transform: skewX(0); }
}

/* Stats */
.stat-pixel {
    background: #0f0620;
    border: 2px solid #7b2d8b;
    box-shadow: 2px 2px 0 #f5a623;
    padding: 1rem;
    text-align: center;
}

.stat-num {
    font-family: 'Press Start 2P', monospace;
    font-size: 1.2rem;
    color: #f5a623;
    display: block;
}

.stat-lbl {
    font-family: 'VT323', monospace;
    font-size: 1rem;
    color: #c084fc;
    display: block;
    margin-top: 4px;
    letter-spacing: 1px;
}

/* Upload area */
.upload-area {
    border: 3px dashed #7b2d8b;
    background: rgba(45, 27, 78, 0.5);
    padding: 2rem;
    text-align: center;
    box-shadow: inset 0 0 30px rgba(120,40,200,0.1);
}

/* Pixel divider */
.px-divider {
    border: none;
    border-top: 3px solid #7b2d8b;
    margin: 1.5rem 0;
    box-shadow: 0 2px 0 rgba(245,166,35,0.3);
}

/* Streamlit widget overrides */
.stFileUploader {
    background: transparent !important;
}

[data-testid="stFileUploadDropzone"] {
    background: rgba(45,27,78,0.8) !important;
    border: 3px dashed #7b2d8b !important;
    border-radius: 0 !important;
}

.stSpinner > div {
    border-top-color: #f5a623 !important;
}

p, .stMarkdown p {
    color: #c4b5fd;
}

</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────
st.markdown("<span class='cat-idle'>🐱‍🔮</span>", unsafe_allow_html=True)
st.title("SUDOKU MASTER")
st.markdown("<p class='pixel-subtitle'>★ LA GATA MAGA RESUELVE TODO ★</p>", unsafe_allow_html=True)

# ── Cargar modelos ───────────────────────────────────────────
@st.cache_resource
def cargar_modelos():
    modelo_yolo = YOLO("../modelos/best.pt")
    reader = easyocr.Reader(['en'], gpu=False)
    return modelo_yolo, reader

with st.spinner("🔮 Invocando los modelos de IA..."):
    modelo_yolo, reader = cargar_modelos()

# ── Funciones ────────────────────────────────────────────────
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
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    lado = 450
    dst = np.array([[0,0],[lado,0],[lado,lado],[0,lado]], dtype='float32')
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(img, M, (lado, lado))

def dividir_celdas(img, margen=4):
    alto, ancho = img.shape[:2]
    celda_alto = alto // 9
    celda_ancho = ancho // 9
    celdas = []
    for fila in range(9):
        fila_celdas = []
        for col in range(9):
            y1 = fila * celda_alto + margen
            y2 = y1 + celda_alto - margen * 2
            x1 = col * celda_ancho + margen
            x2 = x1 + celda_ancho - margen * 2
            fila_celdas.append(img[y1:y2, x1:x2])
        celdas.append(fila_celdas)
    return celdas

def predecir_celda(celda, reader):
    gris = cv2.cvtColor(celda, cv2.COLOR_BGR2GRAY)
    gris = cv2.resize(gris, (gris.shape[1]*3, gris.shape[0]*3), interpolation=cv2.INTER_CUBIC)
    resultado = reader.readtext(gris, allowlist='123456789', detail=1)
    if not resultado:
        return 0
    texto = resultado[0][1]
    confianza = resultado[0][2]
    if texto.isdigit() and 1 <= int(texto) <= 9:
        return int(texto)
    return 0

def detectar_sudoku(celdas, reader):
    sudoku = []
    for fila in range(9):
        fila_nums = []
        for col in range(9):
            digito = predecir_celda(celdas[fila][col], reader)
            fila_nums.append(digito)
        sudoku.append(fila_nums)
    return sudoku

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
    exito = backtrack(tablero)
    return tablero, exito

def render_sudoku(sudoku, original=None):
    html = "<div class='sudoku-wrap'><table class='sudoku'>"
    for i, fila in enumerate(sudoku):
        html += "<tr>"
        for j, num in enumerate(fila):
            valor = str(num) if num != 0 else "&nbsp;"
            if original is None:
                css = "given" if num != 0 else "empty"
            else:
                if original[i][j] != 0:
                    css = "given"
                elif num != 0:
                    css = "solved"
                else:
                    css = "empty"
            html += f"<td class='{css}'>{valor}</td>"
        html += "</tr>"
    html += "</table></div>"
    return html

# ── Upload ───────────────────────────────────────────────────
st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
st.markdown("<div class='step-tag'>► MISIÓN</div>", unsafe_allow_html=True)
st.markdown("**Sube un sudoku y la gata maga lo resolverá al instante**")

imagen_subida = st.file_uploader(
    "Sube tu foto del sudoku",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed"
)

if not imagen_subida:
    st.markdown("""
    <div class='upload-area'>
        <div style='font-size:2.5rem'>📜</div>
        <div style='color:#c084fc; font-family:"VT323",monospace; font-size:1.4rem; letter-spacing:2px'>
            ARRASTRA TU SUDOKU AQUÍ<br>
            <span style='font-size:1rem; opacity:0.7'>JPG · PNG · Foto de periódico · Pantalla digital</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

if imagen_subida:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(imagen_subida.read())
        tmp_path = tmp.name

    imagen = cv2.imread(tmp_path)
    os.unlink(tmp_path)

    st.image(cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB), caption="📸 Tu misión", use_container_width=True)

    # ── PASO 1: YOLO ─────────────────────────────────────────
    st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
    st.markdown("<div class='step-tag'>► PASO 1 · YOLO VISION</div>", unsafe_allow_html=True)
    st.markdown("**La gata usa su visión mágica para encontrar el sudoku...**")

    with st.spinner("🔍 Escaneando con YOLO..."):
        results = modelo_yolo(imagen)

    if len(results[0].boxes) == 0:
        st.error("😿 ¡La gata no encontró ningún sudoku! Prueba con otra foto.")
        st.stop()

    x1, y1, x2, y2 = map(int, results[0].boxes.xyxy[0])
    confianza_yolo = float(results[0].boxes.conf[0])
    img_recortada = results[0].orig_img[y1:y2, x1:x2]

    with st.spinner("📐 Corrigiendo perspectiva con magia..."):
        img_corregida = corregir_perspectiva(img_recortada)

    col1, col2 = st.columns(2)
    with col1:
        st.image(cv2.cvtColor(img_recortada, cv2.COLOR_BGR2RGB), caption=f"🎯 YOLO ({confianza_yolo:.0%})")
    with col2:
        st.image(cv2.cvtColor(img_corregida, cv2.COLOR_BGR2RGB), caption="✨ Perspectiva corregida")

    # ── PASO 2: OCR ──────────────────────────────────────────
    st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
    st.markdown("<div class='step-tag'>► PASO 2 · LECTURA MÁGICA</div>", unsafe_allow_html=True)
    st.markdown("**EasyOCR lee cada celda del pergamino...**")

    t_ocr_start = time.time()
    with st.spinner("🔢 Descifrando los números arcanos..."):
        celdas = dividir_celdas(img_corregida)
        sudoku = detectar_sudoku(celdas, reader)
    t_ocr = time.time() - t_ocr_start

    numeros_detectados = sum(1 for fila in sudoku for n in fila if n != 0)
    huecos = 81 - numeros_detectados

    st.markdown(f"<p style='color:#c084fc'>✦ {numeros_detectados} dígitos detectados · {huecos} huecos por resolver</p>", unsafe_allow_html=True)
    st.markdown(render_sudoku(sudoku), unsafe_allow_html=True)

    # ── PASO 3: RESOLVER ─────────────────────────────────────
    st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
    st.markdown("<div class='step-tag'>► PASO 3 · CONJURO FINAL</div>", unsafe_allow_html=True)
    st.markdown("**La gata lanza el conjuro de backtracking...**")

    t_solver_start = time.time()
    with st.spinner("🧙‍♀️ Calculando la solución perfecta..."):
        solucion, exito = resolver(sudoku)
    t_solver = time.time() - t_solver_start

    if not exito:
        st.error("😿 ¡El conjuro falló! Puede que haya errores en la detección. Prueba con otra foto.")
        st.stop()

    # ── VICTORIA ─────────────────────────────────────────────
    st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
    st.markdown("<span class='cat-celebrate'>🐱‍🔮</span>", unsafe_allow_html=True)
    st.markdown("""
    <div class='win-banner'>
        ✨ ¡CONJURO COMPLETADO! ✨<br>
        <span style='font-size:0.7rem; color:#c084fc'>LA GATA MAGA HA RESUELTO EL SUDOKU</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(render_sudoku(solucion, original=sudoku), unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-family:\"VT323\",monospace; font-size:1.2rem; letter-spacing:2px'>◆ AZUL = NÚMEROS ORIGINALES &nbsp;&nbsp; VERDE = SOLUCIÓN MÁGICA ◆</p>", unsafe_allow_html=True)

    # ── STATS ─────────────────────────────────────────────────
    st.markdown("<hr class='px-divider'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class='stat-pixel'>
            <span class='stat-num'>{numeros_detectados}</span>
            <span class='stat-lbl'>DÍGITOS LEÍDOS</span>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class='stat-pixel'>
            <span class='stat-num'>{t_ocr:.1f}s</span>
            <span class='stat-lbl'>TIEMPO OCR</span>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class='stat-pixel'>
            <span class='stat-num'>{t_solver*1000:.0f}ms</span>
            <span class='stat-lbl'>TIEMPO SOLVER</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("<p style='text-align:center; color:#4a2070; font-size:0.85rem; margin-top:2rem; font-family:\"VT323\",monospace; letter-spacing:1px'>POWERED BY YOLO · EASYOCR · BACKTRACKING · STREAMLIT</p>", unsafe_allow_html=True)