import streamlit as st
import tempfile
import os

from modules.auto_solver import run_auto_solver
from modules.pressure_analysis import run_pressure_analysis

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="EPANET Pro Toolkit",
    layout="wide"
)

st.sidebar.title("EPANET Pro Toolkit 🛠️")
st.sidebar.write("Pilih mode analisis:")

menu = st.sidebar.radio(
    "Navigasi:",
    [
        "🚀 Auto-Solver (Engine: EPyT)",
        "🩺 Analisis Tekanan & Auto-PRV (Engine: WNTR)"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("Multi-engine: EPyT + WNTR")

st.title(menu)

uploaded_file = st.file_uploader(
    "Upload file .inp EPANET",
    type=["inp"]
)

# =====================================================
# MAIN
# =====================================================

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        # =================================================
        # FEATURE 1 : AUTO SOLVER
        # =================================================
        if menu == "🚀 Auto-Solver (Engine: EPyT)":
            run_auto_solver(tmp_path)

        # =================================================
        # FEATURE 2 : ANALISIS TEKANAN + PRV
        # =================================================
        elif menu == "🩺 Analisis Tekanan & Auto-PRV (Engine: WNTR)":
            run_pressure_analysis(tmp_path)

    except Exception as e:
        st.error(f"❌ Gagal menjalankan analisis: {str(e)}")
        st.exception(e)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
