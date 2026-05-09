# app.py
import streamlit as st
from epyt import epanet
import tempfile
import os
import pandas as pd
from itertools import combinations

# IMPORT DARI FILE BUATAN SENDIRI
from utils import warnai_status_tekanan, warnai_status_solver, tampilkan_network
from solver import clean_inp_file, run_wntr_simulation

st.set_page_config(page_title="EPANET Pro Toolkit", layout="wide")

# --- SIDEBAR & MENU ---
st.sidebar.title("EPANET Pro Toolkit 🛠️")
menu = st.sidebar.radio("Navigasi:", ["🚀 Auto-Solver (Engine: EPyT)", "🩺 Analisis Tekanan & Auto-PRV (Engine: WNTR)"])

# --- UPLOAD ---
uploaded_file = st.file_uploader("Upload file .inp EPANET", type=["inp"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        if menu == "🚀 Auto-Solver (Engine: EPyT)":
            # Panggil logika EPyT Anda di sini...
            # Gunakan fungsi dari utils untuk styling tabel
            pass

        elif menu == "🩺 Analisis Tekanan & Auto-PRV (Engine: WNTR)":
            clean_inp_file(tmp_path)
            wn, results = run_wntr_simulation(tmp_path)
            tekanan_awal = results.node["pressure"].iloc[0]
            
            # Tampilkan Visualisasi menggunakan utils
            tampilkan_network(wn, tekanan_awal, "Kondisi Awal Jaringan")
            
            # Logika pencarian Triple PRV Anda...
            pass

    except Exception as e:
        st.error(f"Terjadi Kesalahan: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
