import streamlit as st
import fitz  
from PIL import Image, ImageDraw
import io
import time
from deep_translator import GoogleTranslator

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="📚 Focus Reader (Mobile Friendly)", layout="wide")

# -------------------- RESPONSIVE CSS --------------------
st.markdown("""
<style>
/* GLOBAL PAGE */
.stApp {
    background: linear-gradient(180deg, #0f1114 0%, #121217 100%);
    color: #e6eef8;
    font-family: 'Inter', sans-serif;
    margin: 0;
    padding: 0;
}

/* HEADINGS */
h1 {
    font-size: 2rem;
    text-align: center;
    color: #FFD54F;
}
h2, h3, h4 {
    color: #a9b9d9;
}

/* CONTAINERS */
.book-card {
    background: #ffffff;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.3);
}
.panel-card {
    background: #0f1724;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.6);
    height: auto;
    overflow-y: auto;
    position: sticky;
    top: 10px;
}
.box {
    background: rgba(255,255,255,0.05);
    padding: 12px;
    border-radius: 10px;
    margin-bottom: 10px;
}

/* SLIDERS AND BUTTONS */
.stSlider, .stButton>button {
    font-size: 1rem !important;
    padding: 8px 14px !important;
}
.stButton>button {
    background-color: #1e293b;
    color: white;
    border: none;
    border-radius: 6px;
}
.stButton>button:hover {
    background-color: #334155;
}

/* 📱 MOBILE RESPONSIVE STYLES */
@media (max-width: 768px) {
    h1 {
        font-size: 1.5rem !important;
    }
    .book-card {
        padding: 10px !important;
    }
    .panel-card {
        margin-top: 20px !important;
        padding: 15px !important;
        height: auto !important;
        position: relative !important;
    }
    .stColumn {
        flex-direction: column-reverse !important;
    }
    .stSlider, .stButton>button {
        font-size: 0.9rem !important;
        padding: 6px 12px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# -------------------- HEADER --------------------
st.markdown("<h1>⚡ Bilingual Focus Reading Trainer</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#a9b9d9;'>Read easily across devices — highlighted English with live Hindi meaning.</p>", unsafe_allow_html=True)

# -------------------- FILE UPLOAD --------------------
uploaded_file = st.file_uploader("📂 Upload your PDF", type=["pdf"])
if not uploaded_file:
    st.info("Upload a readable PDF to start.")
    st.stop()

pdf_bytes = uploaded_file.getvalue()
try:
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
except Exception as e:
    st.error(f"Unable to open PDF: {e}")
    st.stop()

# -------------------- LAYOUT --------------------
col_left, col_right = st.columns([2.2, 1], gap="medium")

# -------------------- RIGHT PANEL (CONTROLS + TRANSLATION BOX) --------------------
with col_right:
    st.markdown("<div class='panel-card'>", unsafe_allow_html=True)
    st.subheader("⚙️ Reader Controls")

    words_per_highlight = st.slider("Words per highlight", 3, 10, 4)
    speed = st.slider("Speed (seconds per move)", 0.2, 2.0, 1.0)
    highlight_color = st.color_picker("🖍 Highlight Color", "#FFF176")
    transparency = st.slider("Transparency (lower = lighter)", 10, 160, 40)
    translate_enabled = st.checkbox("Enable Hindi translation", True)

    st.markdown("---")
    start = st.button("▶ Start")
    pause = st.button("⏸ Pause / Resume")
    reset = st.button("🔁 Reset")

    st.markdown("---")
    st.markdown("### 🔍 Current Highlight")
    english_box = st.empty()
    st.markdown("### 🈶 Hindi Meaning")
    hindi_box = st.empty()

    st.markdown("</div>", unsafe_allow_html=True)

# -------------------- LEFT PANEL --------------------
with col_left:
    st.markdown("<div class='book-card'>", unsafe_allow_html=True)
    st.subheader("📖 Book View")
    img_placeholder = st.empty()
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------- SESSION STATES --------------------
if "running" not in st.session_state:
    st.session_state.running = False
if "paused" not in st.session_state:
    st.session_state.paused = False
if "page_idx" not in st.session_state:
    st.session_state.page_idx = 0
if "word_idx" not in st.session_state:
    st.session_state.word_idx = 0

if pause:
    st.session_state.paused = not st.session_state.paused
if reset:
    st.session_state.running = False
    st.session_state.paused = False
    st.session_state.page_idx = 0
    st.session_state.word_idx = 0
    english_box.empty()
    hindi_box.empty()
    st.success("🔁 Reset complete.")
if start:
    st.session_state.running = True
    st.session_state.paused = False

# -------------------- TRANSLATION FUNCTION --------------------
@st.cache_data(show_spinner=False)
def translate_text(text):
    if not text.strip():
        return ""
    try:
        return GoogleTranslator(source='auto', target='hi').translate(text)
    except Exception:
        return "[Translation Error]"

# -------------------- HIGHLIGHT FUNCTION --------------------
def render_page_with_highlight(page, word_index, chunk_size, color_hex, alpha_value):
    words = page.get_text("words")
    if not words:
        return None, ""

    words_sorted = sorted(words, key=lambda x: (x[3], x[0]))
    start = word_index
    end = min(start + chunk_size, len(words_sorted))
    phrase = " ".join([w[4] for w in words_sorted[start:end]])

    zoom = 2
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img_pil = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")

    overlay = Image.new("RGBA", img_pil.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    r, g, b = tuple(int(color_hex[i:i+2], 16) for i in (1, 3, 5))

    for w in words_sorted[start:end]:
        x0, y0, x1, y1 = w[0]*zoom, w[1]*zoom, w[2]*zoom, w[3]*zoom
        draw.rectangle([x0, y0, x1, y1], fill=(r, g, b, alpha_value))

    highlighted = Image.alpha_composite(img_pil, overlay)
    return highlighted, phrase

# -------------------- MAIN READING LOOP --------------------
if st.session_state.running:
    total_pages = len(pdf_doc)

    while st.session_state.page_idx < total_pages:
        if st.session_state.paused:
            time.sleep(0.1)
            continue

        page = pdf_doc[st.session_state.page_idx]
        words = page.get_text("words")
        if not words:
            st.session_state.page_idx += 1
            st.session_state.word_idx = 0
            continue

        # Render current highlight
        img, phrase = render_page_with_highlight(
            page,
            st.session_state.word_idx,
            words_per_highlight,
            highlight_color,
            transparency
        )

        # Display image on left
        if img:
            img_placeholder.image(img, use_container_width=True)

        # Translate and show current phrase only
        if translate_enabled and phrase:
            hindi = translate_text(phrase)
        else:
            hindi = ""

        # Update both boxes live (overwrite old content)
        english_box.markdown(f"<div class='box'><b>English:</b> {phrase}</div>", unsafe_allow_html=True)
        hindi_box.markdown(f"<div class='box'><b>Hindi:</b> {hindi}</div>", unsafe_allow_html=True)

        # Move to next chunk
        st.session_state.word_idx += words_per_highlight
        if st.session_state.word_idx >= len(words):
            st.session_state.page_idx += 1
            st.session_state.word_idx = 0

        time.sleep(speed)

    st.session_state.running = False
    st.success("✅ Reading complete!")
else:
    english_box.markdown("<div class='box'>Waiting for reading to start...</div>", unsafe_allow_html=True)
    hindi_box.markdown("<div class='box'>---</div>", unsafe_allow_html=True)
